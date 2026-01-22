#!/bin/bash

# Veille IA - Démarrer le serveur de publication
# Ce script démarre le serveur local pour l'extension Chrome

cd "$(dirname "$0")/publish-server"

echo "🚀 Démarrage du serveur de publication..."
echo ""

# Vérifier que node_modules existe
if [ ! -d "node_modules" ]; then
  echo "📦 Installation des dépendances..."
  npm install
fi

# Démarrer le serveur
npm start
