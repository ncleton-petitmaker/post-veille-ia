#!/usr/bin/env python3
"""
Discord Channel Collector - Post Veille IA
Sprint 2 - US-2.9

Bot Discord pour collecter les annonces des serveurs AI.
Déployé sur Fly.io pour fonctionnement 24/7.

Usage:
    python discord_collector.py              # Lance le bot
    python discord_collector.py --export     # Exporte les messages récents
    python discord_collector.py --test       # Test de connexion
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional

import aiosqlite
import discord
from discord.ext import tasks
import yaml
from dotenv import load_dotenv

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Chemins
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "discord_channels.yaml"
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "_bmad-output" / "raw-articles"

# Charger les variables d'environnement
load_dotenv(PROJECT_ROOT / ".env")

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def load_config() -> dict:
    """Charge la configuration des canaux Discord"""
    if not CONFIG_PATH.exists():
        logger.error(f"Config non trouvée: {CONFIG_PATH}")
        return {}

    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class DiscordCollector(discord.Client):
    """Bot Discord pour collecter les messages des canaux AI"""

    def __init__(self, config: dict):
        # Intents nécessaires
        intents = discord.Intents.default()
        intents.message_content = True  # Privileged intent
        intents.guilds = True
        intents.guild_messages = True

        super().__init__(intents=intents)

        self.config = config
        self.db_path = DATA_DIR / config.get('storage', {}).get('database', 'discord_messages.db')
        self.monitored_channels: Dict[int, dict] = {}
        self.priority_patterns = []
        self.ignore_patterns = []

        # Compiler les patterns regex
        filters = config.get('collection', {}).get('filters', {})
        for pattern in filters.get('priority_keywords', []):
            try:
                self.priority_patterns.append(re.compile(pattern))
            except re.error:
                logger.warning(f"Pattern invalide ignoré: {pattern}")

        for pattern in filters.get('ignore_patterns', []):
            try:
                self.ignore_patterns.append(re.compile(pattern))
            except re.error:
                logger.warning(f"Pattern ignoré invalide: {pattern}")

    async def setup_hook(self):
        """Initialisation après connexion"""
        # Créer le dossier data si nécessaire
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Initialiser la base de données
        await self.init_database()

        # Démarrer la tâche périodique
        self.periodic_check.start()

    async def init_database(self):
        """Initialise la base de données SQLite"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY,
                    message_id TEXT UNIQUE,
                    channel_id TEXT,
                    channel_name TEXT,
                    server_id TEXT,
                    server_name TEXT,
                    author_id TEXT,
                    author_name TEXT,
                    content TEXT,
                    created_at TEXT,
                    collected_at TEXT,
                    priority TEXT,
                    exported INTEGER DEFAULT 0,
                    url TEXT
                )
            ''')
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_created_at ON messages(created_at)
            ''')
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_exported ON messages(exported)
            ''')
            await db.commit()
        logger.info(f"Base de données initialisée: {self.db_path}")

    async def on_ready(self):
        """Appelé quand le bot est connecté"""
        logger.info(f"Bot connecté en tant que {self.user}")
        logger.info(f"Connecté à {len(self.guilds)} serveurs")

        # Lister les serveurs et canaux accessibles
        for guild in self.guilds:
            logger.info(f"  → {guild.name} (ID: {guild.id})")

        # Configurer les canaux à monitorer
        await self.setup_monitored_channels()

    async def setup_monitored_channels(self):
        """Configure les canaux à monitorer"""
        servers_config = self.config.get('servers', {})

        for server_key, server_info in servers_config.items():
            if not server_info.get('enabled', True):
                continue

            server_id = server_info.get('server_id')
            if not server_id:
                continue

            guild = self.get_guild(int(server_id))
            if not guild:
                logger.warning(f"Serveur non trouvé: {server_key} (ID: {server_id})")
                continue

            for channel_config in server_info.get('channels', []):
                channel_id = channel_config.get('channel_id')
                channel_name = channel_config.get('name')

                # Chercher le canal par ID ou par nom
                channel = None
                if channel_id:
                    channel = guild.get_channel(int(channel_id))

                if not channel and channel_name:
                    # Chercher par nom
                    channel = discord.utils.get(guild.text_channels, name=channel_name)

                if channel:
                    self.monitored_channels[channel.id] = {
                        'server_key': server_key,
                        'server_name': guild.name,
                        'channel_name': channel.name,
                        'priority': channel_config.get('priority', 'medium')
                    }
                    logger.info(f"Monitoring: {guild.name} / #{channel.name}")
                else:
                    logger.warning(f"Canal non trouvé: {server_key} / {channel_name or channel_id}")

    async def on_message(self, message: discord.Message):
        """Appelé pour chaque nouveau message"""
        # Ignorer les bots
        if message.author.bot:
            return

        # Vérifier si le canal est monitoré
        if message.channel.id not in self.monitored_channels:
            return

        # Vérifier les patterns à ignorer
        for pattern in self.ignore_patterns:
            if pattern.search(message.content):
                return

        # Déterminer la priorité
        priority = self.monitored_channels[message.channel.id].get('priority', 'medium')
        for pattern in self.priority_patterns:
            if pattern.search(message.content):
                priority = 'high'
                break

        # Sauvegarder le message
        await self.save_message(message, priority)

        # Notifier si haute priorité
        if priority == 'high' and self.config.get('notifications', {}).get('notify_on_priority'):
            await self.notify_important_message(message)

    async def save_message(self, message: discord.Message, priority: str = 'medium'):
        """Sauvegarde un message dans la base de données"""
        channel_info = self.monitored_channels.get(message.channel.id, {})

        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute('''
                    INSERT OR IGNORE INTO messages
                    (message_id, channel_id, channel_name, server_id, server_name,
                     author_id, author_name, content, created_at, collected_at, priority, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(message.id),
                    str(message.channel.id),
                    channel_info.get('channel_name', message.channel.name),
                    str(message.guild.id) if message.guild else None,
                    channel_info.get('server_name', message.guild.name if message.guild else None),
                    str(message.author.id),
                    str(message.author),
                    message.content,
                    message.created_at.isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                    priority,
                    message.jump_url
                ))
                await db.commit()
                logger.info(f"Message sauvegardé: {message.guild.name}/#{message.channel.name} [{priority}]")
            except Exception as e:
                logger.error(f"Erreur sauvegarde: {e}")

    async def notify_important_message(self, message: discord.Message):
        """Envoie une notification pour un message important"""
        if not DISCORD_WEBHOOK_URL:
            return

        import aiohttp

        channel_info = self.monitored_channels.get(message.channel.id, {})

        embed = {
            "title": f"Nouvelle annonce: {channel_info.get('server_name', 'Unknown')}",
            "description": message.content[:500] + ("..." if len(message.content) > 500 else ""),
            "color": 0x5865F2,  # Discord blurple
            "fields": [
                {"name": "Serveur", "value": message.guild.name if message.guild else "DM", "inline": True},
                {"name": "Canal", "value": f"#{message.channel.name}", "inline": True},
                {"name": "Auteur", "value": str(message.author), "inline": True}
            ],
            "timestamp": message.created_at.isoformat(),
            "footer": {"text": "Discord Collector - Post Veille IA"}
        }

        payload = {
            "embeds": [embed],
            "components": [{
                "type": 1,
                "components": [{
                    "type": 2,
                    "style": 5,
                    "label": "Voir le message",
                    "url": message.jump_url
                }]
            }]
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(DISCORD_WEBHOOK_URL, json=payload) as resp:
                    if resp.status != 204:
                        logger.warning(f"Webhook notification failed: {resp.status}")
        except Exception as e:
            logger.error(f"Erreur notification: {e}")

    @tasks.loop(minutes=5)
    async def periodic_check(self):
        """Vérifie périodiquement l'historique des canaux"""
        collection_config = self.config.get('collection', {})
        max_messages = collection_config.get('max_messages_per_channel', 50)
        max_age_hours = collection_config.get('max_message_age_hours', 24)
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        for channel_id, channel_info in self.monitored_channels.items():
            channel = self.get_channel(channel_id)
            if not channel:
                continue

            try:
                async for message in channel.history(limit=max_messages, after=cutoff_time):
                    if message.author.bot:
                        continue

                    # Vérifier si déjà collecté
                    async with aiosqlite.connect(self.db_path) as db:
                        cursor = await db.execute(
                            'SELECT 1 FROM messages WHERE message_id = ?',
                            (str(message.id),)
                        )
                        if await cursor.fetchone():
                            continue

                    # Déterminer la priorité et sauvegarder
                    priority = channel_info.get('priority', 'medium')
                    for pattern in self.priority_patterns:
                        if pattern.search(message.content):
                            priority = 'high'
                            break

                    # Vérifier les patterns à ignorer
                    should_ignore = False
                    for pattern in self.ignore_patterns:
                        if pattern.search(message.content):
                            should_ignore = True
                            break

                    if not should_ignore:
                        await self.save_message(message, priority)

            except discord.Forbidden:
                logger.warning(f"Accès refusé: {channel_info.get('server_name')}/#{channel_info.get('channel_name')}")
            except Exception as e:
                logger.error(f"Erreur check périodique: {e}")

        logger.info("Check périodique terminé")

    @periodic_check.before_loop
    async def before_periodic_check(self):
        """Attend que le bot soit prêt avant de démarrer la tâche"""
        await self.wait_until_ready()


async def export_messages(config: dict, since_hours: int = 24) -> List[Dict]:
    """Exporte les messages récents en JSON"""
    db_path = DATA_DIR / config.get('storage', {}).get('database', 'discord_messages.db')

    if not db_path.exists():
        logger.error(f"Base de données non trouvée: {db_path}")
        return []

    cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()

    messages = []
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM messages
            WHERE created_at > ? AND exported = 0
            ORDER BY created_at DESC
        ''', (cutoff_time,))

        rows = await cursor.fetchall()
        for row in rows:
            messages.append({
                'source': 'discord',
                'source_detail': f"{row['server_name']}/#{row['channel_name']}",
                'title': f"Discord: {row['server_name']} - {row['channel_name']}",
                'content': row['content'],
                'url': row['url'],
                'author': row['author_name'],
                'published_at': row['created_at'],
                'collected_at': row['collected_at'],
                'priority': row['priority'],
                'message_id': row['message_id']
            })

        # Marquer comme exportés
        if messages:
            await db.execute('''
                UPDATE messages SET exported = 1
                WHERE created_at > ? AND exported = 0
            ''', (cutoff_time,))
            await db.commit()

    # Sauvegarder le fichier JSON
    if messages:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime('%Y-%m-%d')
        output_file = OUTPUT_DIR / f"discord_{date_str}.json"

        # Charger les messages existants si le fichier existe
        existing = []
        if output_file.exists():
            with open(output_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)

        # Fusionner et dédupliquer
        all_messages = existing + messages
        seen_ids = set()
        unique_messages = []
        for msg in all_messages:
            if msg['message_id'] not in seen_ids:
                seen_ids.add(msg['message_id'])
                unique_messages.append(msg)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(unique_messages, f, ensure_ascii=False, indent=2)

        logger.info(f"Exporté {len(messages)} nouveaux messages vers {output_file}")

    return messages


async def test_connection():
    """Teste la connexion au bot"""
    if not DISCORD_BOT_TOKEN:
        logger.error("DISCORD_BOT_TOKEN non défini dans .env")
        return False

    config = load_config()

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        logger.info(f"Test réussi! Connecté en tant que {client.user}")
        logger.info(f"Serveurs accessibles: {len(client.guilds)}")
        for guild in client.guilds:
            logger.info(f"  → {guild.name} (ID: {guild.id})")
            # Lister les canaux texte
            for channel in guild.text_channels[:5]:
                logger.info(f"      #{channel.name} (ID: {channel.id})")
        await client.close()

    try:
        await client.start(DISCORD_BOT_TOKEN)
        return True
    except discord.LoginFailure:
        logger.error("Token invalide!")
        return False
    except Exception as e:
        logger.error(f"Erreur de connexion: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Discord Channel Collector pour la veille IA"
    )
    parser.add_argument(
        '--export',
        action='store_true',
        help="Exporter les messages récents en JSON"
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help="Tester la connexion au bot"
    )
    parser.add_argument(
        '--since',
        type=int,
        default=24,
        help="Heures d'historique à exporter (défaut: 24)"
    )

    args = parser.parse_args()

    if args.test:
        asyncio.run(test_connection())
        return

    if args.export:
        config = load_config()
        messages = asyncio.run(export_messages(config, args.since))
        print(f"Exporté {len(messages)} messages")
        return

    # Lancer le bot
    if not DISCORD_BOT_TOKEN:
        logger.error("DISCORD_BOT_TOKEN non défini!")
        logger.info("Ajoutez DISCORD_BOT_TOKEN=votre_token dans .env")
        sys.exit(1)

    config = load_config()
    client = DiscordCollector(config)

    try:
        client.run(DISCORD_BOT_TOKEN)
    except discord.LoginFailure:
        logger.error("Token Discord invalide!")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Bot arrêté")


if __name__ == "__main__":
    main()
