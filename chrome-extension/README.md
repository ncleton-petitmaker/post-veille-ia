# Veille IA - LinkedIn Publisher Extension

Extension Chrome pour la publication automatique des posts LinkedIn depuis Claude Veille.

## Installation

### 1. Charger l'extension dans Chrome

1. Ouvrir Chrome et aller dans `chrome://extensions/`
2. Activer le "Mode développeur" (en haut à droite)
3. Cliquer sur "Charger l'extension non empaquetée"
4. Sélectionner le dossier `chrome-extension`

### 2. Démarrer le serveur local

```bash
cd publish-server
npm install
npm start
```

Le serveur démarre sur `http://localhost:3847`

## Architecture

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   Claude Veille     │     │   Publish Server    │     │  Chrome Extension   │
│   (Tauri App)       │────▶│   (Node.js)         │◀────│  (Background)       │
│                     │     │                     │     │                     │
│ scheduled_posts.json│     │ API REST + Cron     │     │ Polling toutes      │
└─────────────────────┘     └─────────────────────┘     │ les minutes         │
                                                        └──────────┬──────────┘
                                                                   │
                                                                   ▼
                                                        ┌─────────────────────┐
                                                        │   Content Script    │
                                                        │   (LinkedIn DOM)    │
                                                        │                     │
                                                        │ - Ouvre compositeur │
                                                        │ - Insert texte      │
                                                        │ - Upload image      │
                                                        │ - Clique Publier    │
                                                        └─────────────────────┘
```

## Fonctionnement

1. **Claude Veille** programme des posts dans `scheduled_posts.json`
2. **Publish Server** expose ces posts via une API REST
3. **Chrome Extension** vérifie toutes les minutes s'il y a des posts à publier
4. Quand c'est l'heure, l'extension :
   - Ouvre LinkedIn (si pas déjà ouvert)
   - Utilise le content script pour :
     - Cliquer sur "Commencer un post"
     - Insérer le texte
     - Uploader l'image
     - Cliquer sur "Publier"
   - Met à jour le statut via l'API

## API Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/scheduled-posts` | Liste tous les posts |
| GET | `/api/scheduled-posts/pending` | Posts à publier maintenant |
| PATCH | `/api/scheduled-posts/:id` | Met à jour le statut |
| DELETE | `/api/scheduled-posts/:id` | Supprime un post |
| GET | `/api/image?path=...` | Sert une image |
| GET | `/api/health` | Vérifie que le serveur fonctionne |

## Configuration

Le serveur écoute sur le port `3847` par défaut.

Pour changer le port, modifiez `PORT` dans `publish-server/server.js`.

## Sécurité

- L'extension ne fonctionne que sur `linkedin.com`
- Le serveur n'est accessible qu'en local (`localhost`)
- Aucune donnée n'est envoyée à des serveurs externes

## Dépannage

### L'extension ne se connecte pas

1. Vérifier que le serveur est démarré (`npm start`)
2. Vérifier que le port 3847 n'est pas utilisé
3. Actualiser l'extension depuis la popup

### La publication échoue

1. S'assurer d'être connecté à LinkedIn
2. Vérifier que le compositeur peut s'ouvrir
3. Les sélecteurs LinkedIn peuvent avoir changé (mise à jour nécessaire)

### Les images ne s'uploadent pas

1. Vérifier que le chemin de l'image est correct
2. L'image doit être accessible via le serveur local
