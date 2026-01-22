---
description: "Contrôle le Raspberry Pi pour la veille IA (sync, status, logs)"
---

# Raspberry Pi Control

Tu es l'agent de contrôle du Raspberry Pi pour la veille IA.

## Commandes disponibles

L'utilisateur peut demander :

### `status` - État du système
```bash
ssh pi@$RPI_HOST "cd /home/pi/veille-ia && crontab -l && echo '---' && ls -la output/raw-articles/ 2>/dev/null | tail -5"
```

### `sync` - Synchroniser les fichiers
```bash
bash /Users/nicolascleton/Documents/Projet\ veille\ pour\ Linkedin/post-veille-ia/raspberry/sync-to-rpi.sh
```

### `logs` - Voir les logs récents
```bash
ssh pi@$RPI_HOST "tail -50 /var/log/veille-ia/collect-rss.log"
```

### `collect` - Lancer une collecte manuelle
```bash
ssh pi@$RPI_HOST "cd /home/pi/veille-ia && ./venv/bin/python scripts/collect_all.py --notify"
```

### `setup` - Installer/mettre à jour le RPi
```bash
ssh pi@$RPI_HOST "cd /home/pi/veille-ia && bash raspberry/setup.sh"
```

## Variables d'environnement requises

Dans le fichier `.env` du projet :
```
RPI_HOST=192.168.1.XXX
RPI_USER=pi
RPI_SSH_KEY_PATH=~/.ssh/id_rsa
RPI_PROJECT_PATH=/home/pi/veille-ia
```

## Workflow typique

1. **Première installation** :
   - `/rpi sync` pour copier les fichiers
   - `/rpi setup` pour configurer le RPi

2. **Usage quotidien** :
   - `/rpi status` pour vérifier l'état
   - `/rpi logs` pour voir les collectes

3. **Mise à jour** :
   - Modifier les scripts localement
   - `/rpi sync` pour déployer

## Planification des collectes

| Source | Fréquence | Heures |
|--------|-----------|--------|
| RSS + Jina | 4x/jour | 0h, 6h, 12h, 18h |
| Reddit | 6x/jour | 2h, 6h, 10h, 14h, 18h, 22h |

## En cas de problème

1. Vérifier la connexion : `ssh pi@$RPI_HOST`
2. Vérifier les logs : `/rpi logs`
3. Relancer manuellement : `/rpi collect`
