#!/Users/nicolascleton/Documents/Projet veille pour Linkedin/post-veille-ia/venv/bin/python3
"""
Script principal de collecte - Post Veille IA
Sprint 1

Exécute tous les collecteurs et sauvegarde les résultats.
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
import sys

# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).parent))

# Chemins par défaut
PROJECT_ROOT = Path(__file__).parent.parent

# Charger les variables d'environnement depuis .env
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from collectors import (
    collect_rss,
    collect_jina,
    collect_reddit,
    deduplicate_articles,
    Article
)

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
OUTPUT_DIR = PROJECT_ROOT / "output" / "raw-articles"
CONFIG_PATH = PROJECT_ROOT / "config" / "sources.yaml"


def save_articles(articles: list, output_dir: Path, prefix: str = "articles"):
    """
    Sauvegarde les articles en JSONL.

    Args:
        articles: Liste d'Articles
        output_dir: Dossier de sortie
        prefix: Préfixe du fichier
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Nom de fichier avec date
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    output_file = output_dir / f"{prefix}_{date_str}.jsonl"

    # Mode append pour ajouter aux articles existants du jour
    with open(output_file, 'a', encoding='utf-8') as f:
        for article in articles:
            f.write(article.to_json() + '\n')

    logger.info(f"Sauvegardé {len(articles)} articles dans {output_file}")
    return output_file


def collect_all(
    sources: list = None,
    config_path: str = None,
    output_dir: str = None,
    skip_dedup: bool = False
) -> dict:
    """
    Exécute la collecte complète.

    Args:
        sources: Liste des sources à collecter ['rss', 'jina', 'reddit']
                 Si None, collecte tout
        config_path: Chemin vers sources.yaml
        output_dir: Dossier de sortie
        skip_dedup: Si True, ne pas dédupliquer

    Returns:
        Statistiques de collecte
    """
    if sources is None:
        sources = ['rss', 'jina', 'reddit']

    config_path = Path(config_path) if config_path else CONFIG_PATH
    output_dir = Path(output_dir) if output_dir else OUTPUT_DIR

    all_articles = []
    stats = {
        'start_time': datetime.utcnow().isoformat() + "Z",
        'sources_collected': [],
        'by_source': {},
        'total_raw': 0,
        'total_new': 0,
        'total_deduped': 0,
    }

    # Collecte RSS
    if 'rss' in sources:
        logger.info("=" * 50)
        logger.info("COLLECTE RSS")
        logger.info("=" * 50)
        try:
            rss_articles = collect_rss(str(config_path))
            all_articles.extend(rss_articles)
            stats['by_source']['rss'] = len(rss_articles)
            stats['sources_collected'].append('rss')
        except Exception as e:
            logger.error(f"Erreur collecte RSS: {e}")
            stats['by_source']['rss'] = 0

    # Collecte Jina
    if 'jina' in sources:
        logger.info("=" * 50)
        logger.info("COLLECTE JINA AI")
        logger.info("=" * 50)
        try:
            jina_articles = collect_jina(str(config_path))
            all_articles.extend(jina_articles)
            stats['by_source']['jina'] = len(jina_articles)
            stats['sources_collected'].append('jina')
        except Exception as e:
            logger.error(f"Erreur collecte Jina: {e}")
            stats['by_source']['jina'] = 0

    # Collecte Reddit
    if 'reddit' in sources:
        logger.info("=" * 50)
        logger.info("COLLECTE REDDIT")
        logger.info("=" * 50)
        try:
            reddit_articles = collect_reddit(str(config_path))
            all_articles.extend(reddit_articles)
            stats['by_source']['reddit'] = len(reddit_articles)
            stats['sources_collected'].append('reddit')
        except Exception as e:
            logger.error(f"Erreur collecte Reddit: {e}")
            stats['by_source']['reddit'] = 0

    stats['total_raw'] = len(all_articles)

    # Déduplication
    if not skip_dedup and all_articles:
        logger.info("=" * 50)
        logger.info("DÉDUPLICATION")
        logger.info("=" * 50)
        new_articles = deduplicate_articles(all_articles)
        stats['total_deduped'] = len(all_articles) - len(new_articles)
        all_articles = new_articles

    stats['total_new'] = len(all_articles)

    # Sauvegarde
    if all_articles:
        logger.info("=" * 50)
        logger.info("SAUVEGARDE")
        logger.info("=" * 50)
        save_articles(all_articles, output_dir)

    stats['end_time'] = datetime.utcnow().isoformat() + "Z"

    # Résumé
    logger.info("=" * 50)
    logger.info("RÉSUMÉ")
    logger.info("=" * 50)
    logger.info(f"Sources collectées: {', '.join(stats['sources_collected'])}")
    logger.info(f"Articles bruts: {stats['total_raw']}")
    logger.info(f"Articles dédupliqués: {stats['total_deduped']}")
    logger.info(f"Nouveaux articles: {stats['total_new']}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Collecte des news IA depuis toutes les sources configurées"
    )
    parser.add_argument(
        '--sources',
        nargs='+',
        choices=['rss', 'jina', 'reddit', 'all'],
        default=['all'],
        help="Sources à collecter (défaut: all)"
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help="Chemin vers sources.yaml"
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help="Dossier de sortie"
    )
    parser.add_argument(
        '--skip-dedup',
        action='store_true',
        help="Ne pas dédupliquer les articles"
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help="Sortie JSON des stats"
    )
    parser.add_argument(
        '--notify',
        action='store_true',
        help="Envoyer notification Discord après collecte"
    )

    args = parser.parse_args()

    # Convertir 'all' en liste complète
    sources = None if 'all' in args.sources else args.sources

    # Exécuter la collecte
    stats = collect_all(
        sources=sources,
        config_path=args.config,
        output_dir=args.output,
        skip_dedup=args.skip_dedup
    )

    # Sortie JSON si demandé
    if args.json:
        print(json.dumps(stats, indent=2))

    # Notification Discord si demandé
    if args.notify:
        try:
            from notify import send_collection_stats
            send_collection_stats(stats)
        except ImportError:
            logger.warning("Module notify non disponible")
        except Exception as e:
            logger.error(f"Erreur notification: {e}")

    return 0 if stats['total_new'] >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
