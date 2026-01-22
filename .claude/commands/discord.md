---
description: "Gère le bot Discord pour la collecte des annonces AI"
---

# Discord Bot Collector

Tu es l'agent de gestion du bot Discord pour la veille IA.

## Commandes disponibles

L'utilisateur peut demander :

### `setup` - Guide de configuration initiale

1. **Créer le bot Discord** :
   - Aller sur https://discord.com/developers/applications
   - "New Application" → nommer "Veille IA Bot"
   - Onglet "Bot" → "Add Bot"
   - Activer "MESSAGE CONTENT INTENT" (Privileged Gateway Intents)
   - Copier le token

2. **Configurer le .env** :
   ```bash
   echo "DISCORD_BOT_TOKEN=votre_token_ici" >> .env
   ```

3. **Inviter le bot sur les serveurs AI** :
   - Onglet "OAuth2" → "URL Generator"
   - Scopes: `bot`
   - Permissions: `Read Message History`, `View Channels`
   - Copier l'URL et l'ouvrir pour chaque serveur

### `test` - Tester la connexion
```bash
./venv/bin/python scripts/collectors/discord_collector.py --test
```

### `run` - Lancer le bot localement
```bash
./venv/bin/python scripts/collectors/discord_collector.py
```

### `export` - Exporter les messages collectés
```bash
./venv/bin/python scripts/collectors/discord_collector.py --export --since 24
```

### `deploy` - Déployer sur Fly.io

1. **Installer flyctl** :
   ```bash
   brew install flyctl
   flyctl auth login
   ```

2. **Créer l'app** :
   ```bash
   cd flyio
   flyctl apps create veille-ia-discord-bot
   ```

3. **Configurer les secrets** :
   ```bash
   flyctl secrets set DISCORD_BOT_TOKEN=votre_token
   flyctl secrets set DISCORD_WEBHOOK_URL=votre_webhook
   ```

4. **Créer le volume pour la DB** :
   ```bash
   flyctl volumes create discord_data --size 1 --region cdg
   ```

5. **Déployer** :
   ```bash
   flyctl deploy --config fly.toml
   ```

### `status` - Vérifier le statut Fly.io
```bash
flyctl status --config flyio/fly.toml
flyctl logs --config flyio/fly.toml
```

### `channels` - Lister les serveurs/canaux à monitorer

Éditer `config/discord_channels.yaml` pour :
- Activer/désactiver des serveurs
- Ajouter les channel_id après avoir rejoint les serveurs
- Configurer les filtres de priorité

## Serveurs AI recommandés

| Serveur | Lien d'invitation |
|---------|-------------------|
| OpenAI | discord.gg/openai |
| Anthropic | discord.gg/anthropic |
| Hugging Face | discord.gg/huggingface |
| Mistral AI | discord.gg/mistralai |

## Architecture

```
┌─────────────────────────────────────────┐
│              Fly.io (24/7)              │
│  ┌───────────────────────────────────┐  │
│  │     discord_collector.py          │  │
│  │                                   │  │
│  │  → Écoute #announcements          │  │
│  │  → Stocke dans SQLite             │  │
│  │  → Notifie via webhook            │  │
│  └───────────────────────────────────┘  │
│              ↓ export                   │
│       discord_YYYY-MM-DD.json           │
└─────────────────────────────────────────┘
              ↓ rsync/scp
┌─────────────────────────────────────────┐
│         Mac/RPi (collecte locale)       │
│  output/raw-articles/             │
└─────────────────────────────────────────┘
```

## Coûts Fly.io

- **Free tier** : $5/mois de crédit
- **Bot Discord** : ~$1-2/mois (256MB RAM, shared CPU)
- **Volume 1GB** : ~$0.15/mois

Total estimé : **Gratuit** avec le free tier
