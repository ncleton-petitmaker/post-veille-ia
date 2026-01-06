# ============================================================
# Dockerfile - Discord Bot Collector
# Post Veille IA
# ============================================================
# Build: docker build -t veille-ia-discord-bot -f flyio/Dockerfile .
# ============================================================

FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Installer les dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copier les requirements
COPY requirements-discord.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements-discord.txt

# Copier le code
COPY scripts/collectors/discord_collector.py scripts/collectors/
COPY config/discord_channels.yaml config/

# Créer les dossiers nécessaires
RUN mkdir -p data _bmad-output/raw-articles

# Le .env sera fourni via les secrets Fly.io
# Ne pas copier le .env dans l'image!

# Port pour health check (optionnel)
EXPOSE 8080

# Commande de démarrage
CMD ["python", "scripts/collectors/discord_collector.py"]
