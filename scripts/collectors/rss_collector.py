"""
Collecteur RSS - Post Veille IA
US-2.1 : Collecteur RSS

Collecte les flux RSS des blogs officiels et sites tech.
"""

import feedparser
import logging
import ssl
import certifi
from datetime import datetime, timedelta
from typing import List, Optional
from time import mktime
import yaml
from pathlib import Path

from .schema import Article

# Fix SSL certificates pour macOS
ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_rss_sources(config_path: str = None) -> List[dict]:
    """Charge les sources RSS depuis le fichier de config"""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "sources.yaml"

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    return [s for s in config.get('rss', []) if s.get('enabled', True)]


def parse_date(entry) -> Optional[str]:
    """Extrait et normalise la date d'un entry RSS"""
    date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']

    for field in date_fields:
        if hasattr(entry, field) and getattr(entry, field):
            try:
                dt = datetime.fromtimestamp(mktime(getattr(entry, field)))
                return dt.isoformat() + "Z"
            except:
                continue

    return None


def extract_content(entry) -> str:
    """Extrait le contenu d'un entry RSS"""
    # Essayer différents champs de contenu
    if hasattr(entry, 'content') and entry.content:
        return entry.content[0].value if isinstance(entry.content, list) else entry.content

    if hasattr(entry, 'summary') and entry.summary:
        return entry.summary

    if hasattr(entry, 'description') and entry.description:
        return entry.description

    return ""


def is_recent(entry, max_age_hours: int = 72) -> bool:
    """Vérifie si l'article est assez récent"""
    published = parse_date(entry)
    if not published:
        return True  # Si pas de date, on garde par défaut

    try:
        pub_dt = datetime.fromisoformat(published.replace('Z', '+00:00'))
        cutoff = datetime.now(pub_dt.tzinfo) - timedelta(hours=max_age_hours)
        return pub_dt > cutoff
    except:
        return True


def collect_single_feed(source: dict, max_articles: int = 15, max_age_hours: int = 72) -> List[Article]:
    """Collecte un seul flux RSS"""
    articles = []

    try:
        logger.info(f"Collecte RSS: {source['name']}")
        feed = feedparser.parse(source['url'])

        if feed.bozo and not feed.entries:
            logger.warning(f"Erreur parsing {source['name']}: {feed.bozo_exception}")
            return []

        for entry in feed.entries[:max_articles]:
            # Vérifier la date
            if not is_recent(entry, max_age_hours):
                continue

            # Créer l'article
            article = Article(
                id="",  # Sera généré automatiquement
                url=entry.get('link', ''),
                title=entry.get('title', 'Sans titre'),
                content=extract_content(entry),
                summary=entry.get('summary', '')[:500] if entry.get('summary') else None,
                source_name=source['name'],
                source_type="rss",
                source_category=source.get('category', 'news'),
                published_at=parse_date(entry),
                author=entry.get('author'),
                tags=[tag.term for tag in entry.get('tags', [])] if hasattr(entry, 'tags') else []
            )

            # Générer l'ID après avoir l'URL
            article.id = article.generate_id()
            articles.append(article)

        logger.info(f"  → {len(articles)} articles collectés depuis {source['name']}")

    except Exception as e:
        logger.error(f"Erreur collecte {source['name']}: {e}")

    return articles


def collect_rss(
    config_path: str = None,
    max_articles_per_source: int = 15,
    max_age_hours: int = 72
) -> List[Article]:
    """
    Collecte tous les flux RSS configurés.

    Args:
        config_path: Chemin vers sources.yaml
        max_articles_per_source: Nombre max d'articles par source
        max_age_hours: Ne pas collecter les articles plus vieux que X heures

    Returns:
        Liste d'Articles normalisés
    """
    sources = load_rss_sources(config_path)
    all_articles = []

    logger.info(f"Démarrage collecte RSS - {len(sources)} sources")

    for source in sources:
        articles = collect_single_feed(
            source,
            max_articles=max_articles_per_source,
            max_age_hours=max_age_hours
        )
        all_articles.extend(articles)

    logger.info(f"Collecte RSS terminée - {len(all_articles)} articles total")
    return all_articles


if __name__ == "__main__":
    # Test direct
    articles = collect_rss()
    for article in articles[:3]:
        print(f"- {article.title} ({article.source_name})")
