"""
Collecteurs de veille IA
Post Veille IA - Sprint 1 & 2
"""

from .schema import Article, AnalyzedArticle, LinkedInDraft, CATEGORIES, POST_TYPES
from .rss_collector import collect_rss
from .jina_collector import collect_jina
from .reddit_collector import collect_reddit
from .dedup import deduplicate_articles, DeduplicationDB

# YouTube collector (optionnel, peut échouer si youtube-transcript-api non installé)
try:
    from .youtube_collector import collect_youtube, get_transcript
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False
    collect_youtube = None
    get_transcript = None

__all__ = [
    'Article',
    'AnalyzedArticle',
    'LinkedInDraft',
    'CATEGORIES',
    'POST_TYPES',
    'collect_rss',
    'collect_jina',
    'collect_reddit',
    'collect_youtube',
    'get_transcript',
    'deduplicate_articles',
    'DeduplicationDB',
    'YOUTUBE_AVAILABLE',
]
