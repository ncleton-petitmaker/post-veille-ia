#!/bin/bash
# ============================================================
# Sync to Raspberry Pi - Post Veille IA
# Sprint 2 - US-1.3
#
# Synchronise les fichiers du projet vers le Raspberry Pi.
# Utilise les variables d'environnement de .env
#
# Usage: bash sync-to-rpi.sh
# ============================================================

set -e

# Charger les variables d'environnement
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

# Configuration par défaut
RPI_HOST="${RPI_HOST:-192.168.1.100}"
RPI_USER="${RPI_USER:-pi}"
RPI_PROJECT_PATH="${RPI_PROJECT_PATH:-/home/pi/veille-ia}"
RPI_SSH_KEY="${RPI_SSH_KEY_PATH:-~/.ssh/id_rsa}"

echo "========================================"
echo "Sync vers Raspberry Pi"
echo "========================================"
echo "Host: $RPI_USER@$RPI_HOST"
echo "Destination: $RPI_PROJECT_PATH"
echo ""

# Vérifier la connexion SSH
echo "[1/4] Test de connexion SSH..."
if ! ssh -i "$RPI_SSH_KEY" -o ConnectTimeout=5 "$RPI_USER@$RPI_HOST" "echo ok" > /dev/null 2>&1; then
    echo "❌ Impossible de se connecter à $RPI_HOST"
    echo "Vérifiez:"
    echo "  - RPI_HOST dans .env"
    echo "  - Clé SSH: $RPI_SSH_KEY"
    exit 1
fi
echo "✓ Connexion OK"

# Créer le dossier distant si nécessaire
echo "[2/4] Création du dossier distant..."
ssh -i "$RPI_SSH_KEY" "$RPI_USER@$RPI_HOST" "mkdir -p $RPI_PROJECT_PATH"

# Sync des fichiers
echo "[3/4] Synchronisation des fichiers..."
rsync -avz --progress \
    --exclude 'venv/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.git/' \
    --exclude '_bmad-output/' \
    --exclude '_bmad/' \
    --exclude '.claude/' \
    --exclude 'data/*.db' \
    --exclude '.env' \
    --exclude '*.log' \
    -e "ssh -i $RPI_SSH_KEY" \
    "$PROJECT_DIR/scripts/" \
    "$PROJECT_DIR/config/" \
    "$PROJECT_DIR/requirements.txt" \
    "$RPI_USER@$RPI_HOST:$RPI_PROJECT_PATH/"

# Sync du setup Raspberry
rsync -avz --progress \
    -e "ssh -i $RPI_SSH_KEY" \
    "$PROJECT_DIR/raspberry/" \
    "$RPI_USER@$RPI_HOST:$RPI_PROJECT_PATH/raspberry/"

# Vérifier/créer le .env sur le RPi
echo "[4/4] Vérification du .env distant..."
if ! ssh -i "$RPI_SSH_KEY" "$RPI_USER@$RPI_HOST" "test -f $RPI_PROJECT_PATH/.env"; then
    echo "⚠️  Fichier .env non trouvé sur le RPi"
    echo "Création d'un template..."
    ssh -i "$RPI_SSH_KEY" "$RPI_USER@$RPI_HOST" "cat > $RPI_PROJECT_PATH/.env" << 'EOF'
# Post Veille IA - Raspberry Pi
# Remplir les valeurs ci-dessous

JINA_API_KEY=
DISCORD_WEBHOOK_URL=
EOF
    echo "   Éditez le fichier .env sur le RPi: nano $RPI_PROJECT_PATH/.env"
fi

echo ""
echo "========================================"
echo "✓ Synchronisation terminée!"
echo "========================================"
echo ""
echo "Pour finaliser l'installation sur le RPi:"
echo "  ssh $RPI_USER@$RPI_HOST"
echo "  cd $RPI_PROJECT_PATH"
echo "  bash raspberry/setup.sh"
