"""
Collecteur YouTube Transcripts - Post Veille IA
Sprint 2 - US-2.5

Extrait les transcripts de vidéos YouTube pour créer du contenu.

Modes de fonctionnement :
1. Local avec proxy Webshare (si configuré)
2. Local sans proxy (fallback)
3. Via service Fly.io existant (connaissance.pro)

Usage:
    from collectors.youtube_collector import get_transcript, collect_youtube
"""

import logging
import os
import re
import requests
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        TranscriptsDisabled,
        NoTranscriptFound,
        VideoUnavailable
    )
    # Essayer d'importer le proxy Webshare
    try:
        from youtube_transcript_api.proxies import WebshareProxyConfig
        WEBSHARE_AVAILABLE = True
    except ImportError:
        WEBSHARE_AVAILABLE = False
        WebshareProxyConfig = None

    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False
    WEBSHARE_AVAILABLE = False
    WebshareProxyConfig = None

from .schema import Article

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service Fly.io existant (connaissance.pro)
FLYIO_SERVICE_URL = "https://youtube-transcript-service-winter-sea-1469.fly.dev"


def extract_video_id(url: str) -> Optional[str]:
    """
    Extrait l'ID vidéo depuis une URL YouTube.

    Supporte:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    """
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com/watch\?.*v=)([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def get_webshare_proxy_config():
    """Configure le proxy Webshare si les credentials sont disponibles"""
    if not WEBSHARE_AVAILABLE:
        return None

    username = os.getenv('WEBSHARE_USERNAME')
    password = os.getenv('WEBSHARE_PASSWORD')

    if username and password:
        logger.info("✅ Proxy Webshare configuré")
        return WebshareProxyConfig(
            proxy_username=username,
            proxy_password=password
        )
    return None


def get_transcript_via_flyio(
    video_url: str,
    languages: List[str] = ['fr', 'en']
) -> Optional[Dict]:
    """
    Récupère le transcript via le service Fly.io existant (connaissance.pro).

    Args:
        video_url: URL de la vidéo YouTube
        languages: Liste des langues préférées

    Returns:
        Dict avec le transcript ou None si erreur
    """
    try:
        response = requests.post(
            f"{FLYIO_SERVICE_URL}/transcript",
            json={
                "url": video_url,
                "languages": languages,
                "format": "json"
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if not data.get('success'):
            logger.warning(f"Fly.io: {data.get('error', 'Erreur inconnue')}")
            return None

        # Convertir au format attendu
        transcript = data.get('transcript', [])
        metadata = data.get('metadata', {})

        full_text = ' '.join([s.get('text', '') for s in transcript])

        return {
            'video_id': metadata.get('video_id'),
            'video_url': video_url,
            'language': metadata.get('language_code', 'auto'),
            'is_generated': metadata.get('is_generated', False),
            'duration_minutes': int(metadata.get('duration_seconds', 0) / 60),
            'transcript_raw': transcript,
            'transcript_text': full_text,
            'word_count': len(full_text.split())
        }

    except requests.exceptions.RequestException as e:
        logger.warning(f"Fly.io service non disponible: {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur Fly.io: {e}")
        return None


def get_transcript_local(
    video_id: str,
    languages: List[str] = ['fr', 'en'],
    use_proxy: bool = True
) -> Optional[Dict]:
    """
    Récupère le transcript localement via youtube-transcript-api.

    Args:
        video_id: ID de la vidéo
        languages: Langues préférées
        use_proxy: Utiliser le proxy Webshare si disponible
    """
    if not YOUTUBE_API_AVAILABLE:
        return None

    try:
        # Configurer le proxy si demandé
        proxy_config = get_webshare_proxy_config() if use_proxy else None

        if proxy_config:
            api = YouTubeTranscriptApi(proxy_config=proxy_config)
        else:
            api = YouTubeTranscriptApi()

        # Essayer de récupérer le transcript
        transcript_data = None
        language_used = None

        for lang in languages:
            try:
                transcript_data = api.fetch(video_id, languages=[lang])
                language_used = lang
                break
            except (NoTranscriptFound, Exception):
                continue

        if transcript_data is None:
            try:
                transcript_data = api.fetch(video_id)
                language_used = 'auto'
            except Exception:
                return None

        if not transcript_data:
            return None

        # Assembler le résultat
        full_text = ' '.join([
            entry.text if hasattr(entry, 'text') else str(entry.get('text', ''))
            for entry in transcript_data
        ])

        duration_seconds = sum([
            entry.duration if hasattr(entry, 'duration') else entry.get('duration', 0)
            for entry in transcript_data
        ])

        return {
            'video_id': video_id,
            'language': language_used,
            'is_generated': False,
            'duration_minutes': int(duration_seconds / 60),
            'transcript_raw': [
                {'text': e.text if hasattr(e, 'text') else e.get('text', ''),
                 'start': e.start if hasattr(e, 'start') else e.get('start', 0),
                 'duration': e.duration if hasattr(e, 'duration') else e.get('duration', 0)}
                for e in transcript_data
            ],
            'transcript_text': full_text,
            'word_count': len(full_text.split())
        }

    except TranscriptsDisabled:
        logger.warning(f"Transcripts désactivés pour {video_id}")
        return None
    except VideoUnavailable:
        logger.warning(f"Vidéo non disponible: {video_id}")
        return None
    except Exception as e:
        logger.error(f"Erreur locale: {e}")
        return None


def get_transcript(
    video_url: str,
    languages: List[str] = ['fr', 'en'],
    method: str = 'auto'
) -> Optional[Dict]:
    """
    Récupère le transcript d'une vidéo YouTube.

    Essaie plusieurs méthodes dans l'ordre :
    1. Service Fly.io (connaissance.pro) - plus fiable avec proxy
    2. Local avec proxy Webshare
    3. Local sans proxy

    Args:
        video_url: URL de la vidéo YouTube
        languages: Liste des langues à chercher (par ordre de préférence)
        method: 'auto', 'flyio', 'local', ou 'local_no_proxy'

    Returns:
        Dict avec le transcript ou None si non disponible
    """
    video_id = extract_video_id(video_url)
    if not video_id:
        logger.error(f"URL YouTube invalide: {video_url}")
        return None

    result = None

    # Méthode explicite
    if method == 'flyio':
        return get_transcript_via_flyio(video_url, languages)
    elif method == 'local':
        result = get_transcript_local(video_id, languages, use_proxy=True)
        if result:
            result['video_url'] = video_url
        return result
    elif method == 'local_no_proxy':
        result = get_transcript_local(video_id, languages, use_proxy=False)
        if result:
            result['video_url'] = video_url
        return result

    # Mode auto : essayer dans l'ordre
    logger.info(f"📺 Transcript pour {video_id}...")

    # 1. Essayer Fly.io d'abord (plus fiable)
    logger.debug("  Tentative via Fly.io...")
    result = get_transcript_via_flyio(video_url, languages)
    if result:
        logger.info(f"  ✓ Via Fly.io ({result['word_count']} mots)")
        return result

    # 2. Essayer local avec proxy
    if WEBSHARE_AVAILABLE and os.getenv('WEBSHARE_USERNAME'):
        logger.debug("  Tentative locale avec proxy...")
        result = get_transcript_local(video_id, languages, use_proxy=True)
        if result:
            result['video_url'] = video_url
            logger.info(f"  ✓ Via local+proxy ({result['word_count']} mots)")
            return result

    # 3. Essayer local sans proxy
    if YOUTUBE_API_AVAILABLE:
        logger.debug("  Tentative locale sans proxy...")
        result = get_transcript_local(video_id, languages, use_proxy=False)
        if result:
            result['video_url'] = video_url
            logger.info(f"  ✓ Via local ({result['word_count']} mots)")
            return result

    logger.warning(f"  ✗ Aucun transcript disponible pour {video_id}")
    return None


def transcript_to_article(
    transcript_data: Dict,
    title: str = None,
    channel_name: str = None
) -> Article:
    """
    Convertit un transcript en Article pour le pipeline de veille.

    Args:
        transcript_data: Données du transcript
        title: Titre de la vidéo (optionnel)
        channel_name: Nom de la chaîne (optionnel)
    """
    video_url = transcript_data.get('video_url', '')
    video_id = transcript_data.get('video_id', '')

    # Générer un résumé (premiers 500 caractères)
    full_text = transcript_data.get('transcript_text', '')
    summary = full_text[:500] + '...' if len(full_text) > 500 else full_text

    article = Article(
        id="",
        url=video_url,
        title=title or f"YouTube Video {video_id}",
        content=full_text,
        summary=summary,
        source_name=channel_name or "YouTube",
        source_type="youtube",
        source_category="video",
        published_at=datetime.utcnow().isoformat() + "Z",
        metadata={
            'video_id': video_id,
            'language': transcript_data.get('language'),
            'duration_minutes': transcript_data.get('duration_minutes'),
            'word_count': transcript_data.get('word_count'),
            'is_generated': transcript_data.get('is_generated')
        }
    )

    article.id = article.generate_id()
    return article


def collect_youtube(
    video_urls: List[str],
    languages: List[str] = ['fr', 'en']
) -> List[Article]:
    """
    Collecte les transcripts de plusieurs vidéos YouTube.

    Args:
        video_urls: Liste d'URLs de vidéos
        languages: Langues préférées pour les transcripts

    Returns:
        Liste d'Articles avec les transcripts
    """
    articles = []

    logger.info(f"Collecte YouTube - {len(video_urls)} vidéos")

    for url in video_urls:
        logger.info(f"  Traitement: {url[:50]}...")

        transcript_data = get_transcript(url, languages)

        if transcript_data:
            article = transcript_to_article(transcript_data)
            articles.append(article)
            logger.info(f"    ✓ {transcript_data['word_count']} mots extraits")
        else:
            logger.warning(f"    ✗ Transcript non disponible")

    logger.info(f"Collecte YouTube terminée - {len(articles)} transcripts")
    return articles


# === CLI ===

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Extrait les transcripts de vidéos YouTube"
    )
    parser.add_argument(
        'url',
        help="URL de la vidéo YouTube"
    )
    parser.add_argument(
        '--lang',
        nargs='+',
        default=['fr', 'en'],
        help="Langues préférées (défaut: fr en)"
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help="Sortie JSON"
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help="Afficher seulement le résumé"
    )

    args = parser.parse_args()

    transcript = get_transcript(args.url, args.lang)

    if transcript:
        if args.json:
            # Ne pas inclure le raw dans le JSON (trop gros)
            output = {k: v for k, v in transcript.items() if k != 'transcript_raw'}
            print(json.dumps(output, ensure_ascii=False, indent=2))
        elif args.summary:
            print(f"Video ID: {transcript['video_id']}")
            print(f"Langue: {transcript['language']}")
            print(f"Durée: {transcript['duration_minutes']} min")
            print(f"Mots: {transcript['word_count']}")
            print(f"\nExtrait (500 premiers caractères):")
            print(transcript['transcript_text'][:500])
        else:
            print(transcript['transcript_text'])
    else:
        print("Transcript non disponible")
        exit(1)
