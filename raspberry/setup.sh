#!/bin/bash
# ============================================================
# Setup Raspberry Pi - Post Veille IA
# Sprint 2 - US-1.1, US-2.8
#
# Execute ce script sur le Raspberry Pi pour configurer
# l'environnement et les cron jobs.
#
# Usage: bash setup.sh
# ============================================================

set -e

PROJECT_DIR="/home/pi/veille-ia"
LOG_DIR="/var/log/veille-ia"
VENV_DIR="$PROJECT_DIR/venv"

echo "========================================"
echo "Setup Post Veille IA - Raspberry Pi"
echo "========================================"

# --- Création des dossiers ---
echo "[1/6] Création des dossiers..."
sudo mkdir -p $LOG_DIR
sudo chown pi:pi $LOG_DIR
mkdir -p $PROJECT_DIR

# --- Installation des dépendances système ---
echo "[2/6] Installation des dépendances système..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv

# --- Création du virtualenv ---
echo "[3/6] Création du virtualenv..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR
fi

# --- Installation des dépendances Python ---
echo "[4/6] Installation des dépendances Python..."
$VENV_DIR/bin/pip install --upgrade pip -q
$VENV_DIR/bin/pip install feedparser requests pyyaml python-dotenv python-dateutil certifi -q

# --- Copie des fichiers (si pas déjà fait) ---
echo "[5/6] Vérification des fichiers..."
if [ ! -f "$PROJECT_DIR/scripts/collect_all.py" ]; then
    echo "  ⚠️  Les scripts ne sont pas encore copiés."
    echo "  Utilisez rsync ou scp pour copier le projet."
fi

# --- Configuration des cron jobs ---
echo "[6/6] Configuration des cron jobs..."

# Créer le fichier cron
CRON_FILE="/tmp/veille-ia-cron"
cat > $CRON_FILE << 'EOF'
# Post Veille IA - Cron Jobs
# Généré automatiquement par setup.sh

# Variables d'environnement
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
PROJECT_DIR=/home/pi/veille-ia
LOG_DIR=/var/log/veille-ia

# === COLLECTE RSS + JINA ===
# Toutes les 6 heures : 6h, 12h, 18h, 00h
0 0,6,12,18 * * * $PROJECT_DIR/venv/bin/python $PROJECT_DIR/scripts/collect_all.py --sources rss jina --notify >> $LOG_DIR/collect-rss.log 2>&1

# === COLLECTE REDDIT ===
# Toutes les 4 heures
0 2,6,10,14,18,22 * * * $PROJECT_DIR/venv/bin/python $PROJECT_DIR/scripts/collect_all.py --sources reddit --notify >> $LOG_DIR/collect-reddit.log 2>&1

# === NETTOYAGE LOGS ===
# Tous les jours à 3h00 - garde 7 jours de logs
0 3 * * * find $LOG_DIR -name "*.log" -mtime +7 -delete

# === ROTATION LOGS ===
# Tous les dimanches à 4h00
0 4 * * 0 for f in $LOG_DIR/*.log; do mv "$f" "$f.$(date +\%Y\%m\%d)"; done 2>/dev/null
EOF

# Installer le cron pour l'utilisateur pi
crontab $CRON_FILE
rm $CRON_FILE

echo ""
echo "========================================"
echo "✓ Setup terminé!"
echo "========================================"
echo ""
echo "Prochaines étapes:"
echo "1. Copier les scripts: rsync -av scripts/ pi@<IP>:$PROJECT_DIR/scripts/"
echo "2. Copier la config: rsync -av config/ pi@<IP>:$PROJECT_DIR/config/"
echo "3. Créer le fichier .env sur le RPi"
echo "4. Tester: $VENV_DIR/bin/python $PROJECT_DIR/scripts/collect_all.py --sources rss"
echo ""
echo "Logs disponibles dans: $LOG_DIR"
echo "Cron jobs installés - vérifier avec: crontab -l"
