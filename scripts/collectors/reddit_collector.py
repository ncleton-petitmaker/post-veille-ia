"""
Collecteur Reddit - Post Veille IA
US-2.3 : Collecteur Reddit

Collecte les posts populaires des subreddits IA via l'endpoint JSON gratuit.
"""

import requests
import logging
import time
from datetime import datetime
from typing import List, Optional
import yaml
from pathlib import Path

from .schema import Article

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration Reddit
REDDIT_BASE_URL = "https://www.reddit.com"
USER_AGENT = "VeilleIA/2.0 (by /u/veille_ia_bot)"
RATE_LIMIT_DELAY = 2  # Secondes entre chaque requête


def load_reddit_sources(config_path: str = None) -> List[dict]:
    """Charge les subreddits depuis le fichier de config"""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "sources.yaml"

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    reddit_config = config.get('reddit', {})
    return [s for s in reddit_config.get('subreddits', []) if s.get('enabled', True)]


def fetch_subreddit(
    subreddit: str,
    filter_type: str = "hot",
    period: str = None,
    limit: int = 25
) -> Optional[dict]:
    """
    Récupère les posts d'un subreddit via l'endpoint JSON.

    Args:
        subreddit: Nom du subreddit (sans r/)
        filter_type: hot, new, top, rising
        period: Pour top: hour, day, week, month, year, all
        limit: Nombre de posts à récupérer

    Returns:
        Données JSON ou None si erreur
    """
    url = f"{REDDIT_BASE_URL}/r/{subreddit}/{filter_type}.json"

    params = {"limit": limit}
    if period and filter_type == "top":
        params["t"] = period

    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur Reddit r/{subreddit}: {e}")
        return None


def extract_post_content(post_data: dict) -> str:
    """Extrait le contenu textuel d'un post Reddit"""
    data = post_data.get('data', {})

    # Self-post avec texte
    if data.get('selftext'):
        return data['selftext'][:3000]

    # Lien externe - utiliser le titre comme contenu
    if data.get('url') and not data.get('is_self'):
        return f"[Lien externe] {data.get('url', '')}"

    return ""


def collect_single_subreddit(source: dict) -> List[Article]:
    """Collecte les posts d'un seul subreddit"""
    articles = []
    subreddit = source['name']
    filter_type = source.get('filter', 'hot')
    period = source.get('period')
    min_upvotes = source.get('min_upvotes', 0)

    try:
        logger.info(f"Collecte Reddit: r/{subreddit} ({filter_type})")

        data = fetch_subreddit(subreddit, filter_type, period, limit=50)
        if not data or 'data' not in data:
            return []

        posts = data['data'].get('children', [])

        for post in posts:
            post_data = post.get('data', {})

            # Filtrer par upvotes
            score = post_data.get('ups', 0)
            if score < min_upvotes:
                continue

            # Ignorer les posts épinglés (souvent des règles)
            if post_data.get('stickied'):
                continue

            # Créer l'article
            article = Article(
                id="",
                url=f"https://reddit.com{post_data.get('permalink', '')}",
                title=post_data.get('title', 'Sans titre'),
                content=extract_post_content(post),
                summary=post_data.get('title', ''),
                source_name=f"r/{subreddit}",
                source_type="reddit",
                source_category="community",
                published_at=datetime.fromtimestamp(
                    post_data.get('created_utc', 0)
                ).isoformat() + "Z" if post_data.get('created_utc') else None,
                author=post_data.get('author'),
                score=score,
                num_comments=post_data.get('num_comments', 0),
                tags=[post_data.get('link_flair_text')] if post_data.get('link_flair_text') else []
            )

            article.id = article.generate_id()
            articles.append(article)

        logger.info(f"  → {len(articles)} posts collectés depuis r/{subreddit}")

    except Exception as e:
        logger.error(f"Erreur collecte r/{subreddit}: {e}")

    return articles


def collect_reddit(
    config_path: str = None,
    max_articles_per_source: int = 15
) -> List[Article]:
    """
    Collecte tous les subreddits configurés.

    Args:
        config_path: Chemin vers sources.yaml
        max_articles_per_source: Nombre max d'articles par subreddit

    Returns:
        Liste d'Articles normalisés
    """
    sources = load_reddit_sources(config_path)
    all_articles = []

    logger.info(f"Démarrage collecte Reddit - {len(sources)} subreddits")

    for i, source in enumerate(sources):
        articles = collect_single_subreddit(source)
        all_articles.extend(articles[:max_articles_per_source])

        # Rate limiting entre les subreddits
        if i < len(sources) - 1:
            time.sleep(RATE_LIMIT_DELAY)

    # Trier par score décroissant
    all_articles.sort(key=lambda a: a.score or 0, reverse=True)

    logger.info(f"Collecte Reddit terminée - {len(all_articles)} posts total")
    return all_articles


if __name__ == "__main__":
    # Test direct
    articles = collect_reddit()
    for article in articles[:5]:
        print(f"- [{article.score}↑] {article.title[:50]}... ({article.source_name})")
