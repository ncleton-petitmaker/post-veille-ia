# Post Veille IA - Configuration Claude Code

## Project: Post Veille IA

Système de veille IA automatisé pour générer des posts LinkedIn.

## Commandes Principales

### Veille
- `/veille` - Workflow complet : collecte → analyse → génération de posts
- `/veille-analyze` - Analyser les articles collectés
- `/veille-generate` - Générer les posts LinkedIn

### Gestion
- `/discord` - Gérer le bot Discord pour la collecte
- `/rpi` - Contrôler le Raspberry Pi (sync, status, logs)
- `/youtube` - Extraire les transcripts YouTube

## Structure des Dossiers

```
config/                    # Configuration
  sources.yaml            # Sources RSS, Reddit, Jina, etc.
  scoring.yaml            # Règles de scoring des articles
  content_preferences.json # Préférences de contenu et style

output/                    # Données générées
  raw-articles/           # Articles bruts collectés
  analyzed-articles/      # Articles analysés et scorés
  linkedin-posts/         # Posts LinkedIn générés

scripts/                   # Scripts Python
  collect_all.py          # Collecte des articles
  analyze_articles.py     # Analyse et scoring
  collectors/             # Collecteurs par source
```

## Configuration du Contenu

Édite `config/content_preferences.json` pour personnaliser :
- `news_focus` : Types de news à privilégier
- `post_style` : Format et style de rédaction des posts

## Workflow Typique

1. Lance `/veille` pour exécuter le pipeline complet
2. Consulte les posts générés dans `output/linkedin-posts/`
3. Programme ou publie sur LinkedIn

## Publication Automatique LinkedIn

### Extension Chrome

Une extension Chrome permet la publication automatique des posts programmés.

#### Installation

1. Charger l'extension dans Chrome (`chrome://extensions/` > Mode développeur > Charger l'extension non empaquetée > sélectionner `chrome-extension/`)
2. Démarrer le serveur local : `./start-publish-server.sh`

#### Fonctionnement

```
Claude Veille (GUI) → scheduled_posts.json → Publish Server → Extension Chrome → LinkedIn
```

- Le serveur expose les posts via API REST (port 3847)
- L'extension vérifie toutes les minutes s'il y a des posts à publier
- Quand c'est l'heure, elle publie automatiquement sur LinkedIn

#### Structure

```
chrome-extension/        # Extension Chrome
  manifest.json         # Configuration Manifest V3
  src/
    background.js       # Service worker (polling + coordination)
    content-linkedin.js # Manipulation DOM LinkedIn
    popup.html/js       # Interface popup

publish-server/         # Serveur local Node.js
  server.js            # API REST + Cron
```
