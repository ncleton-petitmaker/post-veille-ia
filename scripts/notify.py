#!/Users/nicolascleton/Documents/Projet veille pour Linkedin/post-veille-ia/venv/bin/python3
"""
Notifications Discord - Post Veille IA
Sprint 2 - US-1.4, US-2.9

Envoie des notifications via webhook Discord.

Usage:
    python notify.py "Message à envoyer"
    python notify.py --stats '{"articles": 85, "new": 10}'
    python notify.py --error "Erreur de collecte RSS"
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

# Charger .env
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_webhook_url() -> Optional[str]:
    """Récupère l'URL du webhook Discord"""
    return os.getenv('DISCORD_WEBHOOK_URL')


def send_notification(
    message: str,
    webhook_url: str = None,
    username: str = "Veille IA Bot",
    avatar_url: str = None
) -> bool:
    """
    Envoie une notification via webhook Discord.

    Args:
        message: Message à envoyer
        webhook_url: URL du webhook (ou depuis .env)
        username: Nom du bot
        avatar_url: URL de l'avatar

    Returns:
        True si succès, False sinon
    """
    if webhook_url is None:
        webhook_url = get_webhook_url()

    if not webhook_url:
        logger.warning("DISCORD_WEBHOOK_URL non configurée - notification ignorée")
        return False

    payload = {
        "content": message,
        "username": username,
    }

    if avatar_url:
        payload["avatar_url"] = avatar_url

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Notification Discord envoyée")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur envoi notification Discord: {e}")
        return False


def send_collection_stats(stats: dict, webhook_url: str = None) -> bool:
    """
    Envoie un résumé de collecte formaté.

    Args:
        stats: Statistiques de collecte
        webhook_url: URL du webhook
    """
    total_raw = stats.get('total_raw', 0)
    total_new = stats.get('total_new', 0)
    by_source = stats.get('by_source', {})
    sources = stats.get('sources_collected', [])

    # Construire le message
    now = datetime.now().strftime('%H:%M')

    if total_new > 0:
        emoji = "📬"
        status = f"**{total_new} nouveaux articles**"
    else:
        emoji = "📭"
        status = "Aucun nouvel article"

    message = f"{emoji} **Veille IA** - {now}\n\n{status}\n\n"

    # Détails par source
    if by_source:
        message += "**Par source:**\n"
        for source, count in by_source.items():
            message += f"• {source.upper()}: {count}\n"

    message += f"\n_Total brut: {total_raw} | Dédupliqués: {stats.get('total_deduped', 0)}_"

    return send_notification(message, webhook_url)


def send_error(error_message: str, webhook_url: str = None) -> bool:
    """
    Envoie une alerte d'erreur.

    Args:
        error_message: Description de l'erreur
        webhook_url: URL du webhook
    """
    now = datetime.now().strftime('%H:%M')
    message = f"⚠️ **Erreur Veille IA** - {now}\n\n```\n{error_message}\n```"
    return send_notification(message, webhook_url)


def send_priority_alert(article: dict, webhook_url: str = None) -> bool:
    """
    Envoie une alerte pour un article prioritaire (score >= 9).

    Args:
        article: Article avec score élevé
        webhook_url: URL du webhook
    """
    title = article.get('title', 'Sans titre')
    score = article.get('score', 0)
    url = article.get('url', '')
    source = article.get('source', '')

    message = f"""🚨 **Article Prioritaire!** (Score: {score}/10)

**{title}**

Source: {source}
{url}"""

    return send_notification(message, webhook_url)


def main():
    parser = argparse.ArgumentParser(
        description="Envoie des notifications Discord"
    )
    parser.add_argument(
        'message',
        nargs='?',
        default=None,
        help="Message à envoyer"
    )
    parser.add_argument(
        '--stats',
        type=str,
        default=None,
        help="JSON des statistiques de collecte"
    )
    parser.add_argument(
        '--error',
        type=str,
        default=None,
        help="Message d'erreur à envoyer"
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help="Envoie un message de test"
    )

    args = parser.parse_args()

    # Mode test
    if args.test:
        success = send_notification("🧪 Test de notification Veille IA - Tout fonctionne!")
        return 0 if success else 1

    # Erreur
    if args.error:
        success = send_error(args.error)
        return 0 if success else 1

    # Stats de collecte
    if args.stats:
        try:
            stats = json.loads(args.stats)
            success = send_collection_stats(stats)
            return 0 if success else 1
        except json.JSONDecodeError:
            logger.error("JSON invalide pour --stats")
            return 1

    # Message simple
    if args.message:
        success = send_notification(args.message)
        return 0 if success else 1

    # Aucun argument
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
