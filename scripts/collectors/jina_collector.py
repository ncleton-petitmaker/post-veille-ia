"""
Collecteur Jina AI - Post Veille IA
US-2.2 : Collecteur Jina AI (sites JavaScript)

Utilise Jina Reader API pour collecter les sites nécessitant JavaScript.
https://jina.ai/reader/
"""

import requests
import logging
import os
import re
import time
from datetime import datetime
from typing import List, Optional
import yaml
from pathlib import Path

from .schema import Article

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration Jina
JINA_READER_URL = "https://r.jina.ai"
RATE_LIMIT_DELAY = 3  # Secondes entre chaque requête (conservateur)


def load_jina_sources(config_path: str = None) -> List[dict]:
    """Charge les sources Jina depuis le fichier de config"""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "sources.yaml"

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    return [s for s in config.get('jina', {}).get('sites', []) if s.get('enabled', True)]


def get_jina_api_key() -> Optional[str]:
    """Récupère la clé API Jina depuis l'environnement"""
    return os.getenv('JINA_API_KEY')


def extract_articles_from_markdown(markdown: str, source: dict) -> List[dict]:
    """
    Extrait les articles individuels depuis le markdown Jina.
    Supporte plusieurs formats de newsletters.
    """
    articles = []
    seen_urls = set()

    # Pattern générique pour trouver tous les liens markdown
    link_pattern = r'\[([^\]]+)\]\((https?://[^)]+)\)'

    # Patterns d'URL d'articles selon la source
    article_url_patterns = [
        r'/p/',           # Beehiiv newsletters (therundown, bensbites)
        r'/posts/',       # Substack
        r'/archive/',     # Archives newsletters
        r'/article/',     # Sites news
        r'/news/',        # Sites news
        r'/\d{4}/\d{2}/', # Date-based URLs (blogs)
    ]

    for match in re.finditer(link_pattern, markdown):
        title = match.group(1)
        url = match.group(2)

        # Ignorer les images et liens courts
        if title.startswith('!') or title.startswith('Image'):
            continue
        if len(title) < 20:
            continue
        if url in seen_urls:
            continue

        # Vérifier si c'est un lien d'article
        is_article = any(pattern in url for pattern in article_url_patterns)

        # Ou si l'URL contient le domaine source et n'est pas la page principale
        source_domain = source['url'].replace('https://', '').replace('http://', '').split('/')[0]
        if source_domain in url and url != source['url'] and len(url) > len(source['url']) + 5:
            is_article = True

        if is_article:
            # Nettoyer le titre (enlever les tirets décoratifs)
            clean_title = re.sub(r'\s*-+\s*$', '', title).strip()
            clean_title = re.sub(r'^-+\s*', '', clean_title).strip()

            if len(clean_title) > 15:
                seen_urls.add(url)
                articles.append({
                    'title': clean_title,
                    'url': url,
                    'content': ''  # Le contenu sera dans le résumé si dispo
                })

    return articles[:15]  # Max 15 articles par source


def fetch_with_jina(url: str, api_key: Optional[str] = None) -> Optional[str]:
    """
    Récupère le contenu d'une URL via Jina Reader API.

    Returns:
        Contenu en Markdown ou None si erreur
    """
    headers = {
        "Accept": "text/markdown",
    }

    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    jina_url = f"{JINA_READER_URL}/{url}"

    try:
        logger.debug(f"Fetching via Jina: {url}")
        response = requests.get(jina_url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur Jina pour {url}: {e}")
        return None


def collect_single_jina_source(source: dict, api_key: Optional[str] = None) -> List[Article]:
    """Collecte une seule source via Jina"""
    articles = []

    try:
        logger.info(f"Collecte Jina: {source['name']}")

        # Récupérer le contenu via Jina
        markdown = fetch_with_jina(source['url'], api_key)
        if not markdown:
            return []

        # Extraire les articles du markdown
        raw_articles = extract_articles_from_markdown(markdown, source)

        for raw in raw_articles:
            article = Article(
                id="",
                url=raw.get('url', source['url']),
                title=raw.get('title', 'Sans titre'),
                content=raw.get('content', ''),
                summary=raw.get('content', '')[:300] if raw.get('content') else None,
                source_name=source['name'],
                source_type="jina",
                source_category=source.get('category', 'newsletter'),
                published_at=datetime.utcnow().isoformat() + "Z",  # Pas de date exacte dispo
            )
            article.id = article.generate_id()
            articles.append(article)

        logger.info(f"  → {len(articles)} articles extraits depuis {source['name']}")

    except Exception as e:
        logger.error(f"Erreur collecte Jina {source['name']}: {e}")

    return articles


def collect_jina(
    config_path: str = None,
    max_articles_per_source: int = 15
) -> List[Article]:
    """
    Collecte tous les sites configurés via Jina Reader API.

    Args:
        config_path: Chemin vers sources.yaml
        max_articles_per_source: Nombre max d'articles par source

    Returns:
        Liste d'Articles normalisés
    """
    sources = load_jina_sources(config_path)
    api_key = get_jina_api_key()
    all_articles = []

    if not api_key:
        logger.warning("JINA_API_KEY non définie - utilisation du free tier (20 RPM)")

    logger.info(f"Démarrage collecte Jina - {len(sources)} sources")

    for i, source in enumerate(sources):
        articles = collect_single_jina_source(source, api_key)
        all_articles.extend(articles[:max_articles_per_source])

        # Rate limiting entre les sources
        if i < len(sources) - 1:
            time.sleep(RATE_LIMIT_DELAY)

    logger.info(f"Collecte Jina terminée - {len(all_articles)} articles total")
    return all_articles


if __name__ == "__main__":
    # Test direct
    articles = collect_jina()
    for article in articles[:5]:
        print(f"- {article.title[:60]}... ({article.source_name})")
