#!/Users/nicolascleton/Documents/Projet veille pour Linkedin/post-veille-ia/venv/bin/python3
"""
Analyseur d'articles - Post Veille IA
Sprint 1 - US-3.1

Script standalone pour analyser et scorer les articles collectés.
Utilise la configuration scoring.yaml pour les critères.

Usage:
    python analyze_articles.py                    # Analyse le fichier du jour
    python analyze_articles.py --date 2026-01-05  # Analyse une date spécifique
    python analyze_articles.py --input file.jsonl # Analyse un fichier spécifique
"""

import argparse
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import yaml

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Chemins
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "scoring.yaml"
RAW_DIR = PROJECT_ROOT / "_bmad-output" / "raw-articles"
OUTPUT_DIR = PROJECT_ROOT / "_bmad-output" / "analyzed-articles"


def load_scoring_config() -> dict:
    """Charge la configuration de scoring"""
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_articles(input_path: Path) -> List[dict]:
    """Charge les articles depuis un fichier JSONL"""
    articles = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                articles.append(json.loads(line))
    return articles


def calculate_keyword_score(text: str, keywords: List[str]) -> float:
    """Calcule un score basé sur la présence de mots-clés"""
    if not text or not keywords:
        return 0.0

    text_lower = text.lower()
    matches = sum(1 for kw in keywords if kw.lower() in text_lower)
    return min(matches / len(keywords), 1.0)  # Normaliser à [0, 1]


def detect_categories(article: dict, config: dict) -> List[str]:
    """Détecte les catégories d'un article"""
    categories = []
    text = f"{article.get('title', '')} {article.get('content', '')} {article.get('summary', '')}".lower()

    for cat in config.get('categories', []):
        keywords = cat.get('keywords', [])
        if any(kw.lower() in text for kw in keywords):
            categories.append(cat['name'])

    return categories[:3] if categories else ['General']


def score_article(article: dict, config: dict) -> Dict:
    """
    Score un article selon les critères configurés.

    Retourne un dict avec le score et les détails.
    """
    criteria = config.get('scoring_criteria', {})
    thresholds = config.get('thresholds', {})
    exclusions = config.get('exclusions', {})

    title = article.get('title', '')
    content = article.get('content', '')
    summary = article.get('summary', '')
    source = article.get('source_name', '')
    full_text = f"{title} {content} {summary}"

    scores = {}
    total_weight = 0
    weighted_sum = 0

    # 1. Pertinence audience
    audience = criteria.get('audience_relevance', {})
    if audience:
        weight = audience.get('weight', 0)
        keywords = audience.get('keywords_boost', [])
        score = calculate_keyword_score(full_text, keywords)
        # Bonus si titre contient des mots clés
        if calculate_keyword_score(title, keywords) > 0:
            score = min(score + 0.3, 1.0)
        scores['audience_relevance'] = score * 10
        weighted_sum += score * weight
        total_weight += weight

    # 2. Potentiel d'engagement
    engagement = criteria.get('engagement_potential', {})
    if engagement:
        weight = engagement.get('weight', 0)
        keywords = engagement.get('keywords_boost', [])
        score = calculate_keyword_score(title, keywords)  # Surtout dans le titre
        scores['engagement_potential'] = score * 10
        weighted_sum += score * weight
        total_weight += weight

    # 3. Qualité de la source
    source_quality = criteria.get('source_quality', {})
    if source_quality:
        weight = source_quality.get('weight', 0)
        tier1 = source_quality.get('tier_1_sources', [])
        tier2 = source_quality.get('tier_2_sources', [])

        if any(t1.lower() in source.lower() for t1 in tier1):
            score = 1.0
        elif any(t2.lower() in source.lower() for t2 in tier2):
            score = 0.7
        else:
            score = 0.4  # Source inconnue

        scores['source_quality'] = score * 10
        weighted_sum += score * weight
        total_weight += weight

    # 4. Fraîcheur (basé sur published_at si dispo)
    timeliness = criteria.get('timeliness', {})
    if timeliness:
        weight = timeliness.get('weight', 0)
        # Pour l'instant, on assume que les articles sont récents
        score = 0.7  # Score par défaut
        scores['timeliness'] = score * 10
        weighted_sum += score * weight
        total_weight += weight

    # 5. Originalité (basique - longueur du titre)
    uniqueness = criteria.get('uniqueness', {})
    if uniqueness:
        weight = uniqueness.get('weight', 0)
        # Heuristique simple: titres plus longs = plus spécifiques
        title_length_score = min(len(title) / 80, 1.0)
        scores['uniqueness'] = title_length_score * 10
        weighted_sum += title_length_score * weight
        total_weight += weight

    # Calculer le score final (1-10)
    if total_weight > 0:
        final_score = (weighted_sum / total_weight) * 10
    else:
        final_score = 5.0

    # Appliquer les pénalités
    negative_kw = exclusions.get('negative_keywords', [])
    if any(nkw.lower() in full_text.lower() for nkw in negative_kw):
        final_score *= 0.7

    clickbait = exclusions.get('clickbait_patterns', [])
    if any(cb.lower() in title.lower() for cb in clickbait):
        final_score *= 0.8

    # Arrondir et limiter
    final_score = round(min(max(final_score, 1), 10), 1)

    return {
        'score': final_score,
        'breakdown': scores,
        'categories': detect_categories(article, config)
    }


def generate_linkedin_angles(article: dict, categories: List[str]) -> List[str]:
    """Génère des suggestions d'angles LinkedIn"""
    title = article.get('title', '')
    source = article.get('source_name', '')

    angles = []

    # Angle 1: Décryptage
    angles.append(f"Ce que {title[:50]}... signifie pour les entreprises")

    # Angle 2: Question
    if 'Enterprise' in categories or 'Tools' in categories:
        angles.append("Comment intégrer cette innovation dans vos process ?")
    elif 'Research' in categories:
        angles.append("Pourquoi cette recherche va impacter votre secteur")
    else:
        angles.append("Les 3 leçons à retenir de cette actualité")

    # Angle 3: Prospective
    angles.append("Ce que ça prédit pour 2026")

    return angles


def suggest_hashtags(categories: List[str], config: dict) -> List[str]:
    """Suggère des hashtags basés sur les catégories"""
    hashtags_config = config.get('hashtags', {})
    base = hashtags_config.get('base', ['#IA', '#IntelligenceArtificielle'])
    by_category = hashtags_config.get('by_category', {})
    max_tags = hashtags_config.get('max_hashtags', 4)

    # Mapping par défaut si pas dans config
    default_by_category = {
        'LLMs': ['#LLM', '#ChatGPT', '#Claude'],
        'Enterprise': ['#TransformationDigitale', '#EntrepriseIA'],
        'Tools': ['#DevTools', '#Productivite'],
        'Safety': ['#IAResponsable', '#EthiqueIA'],
        'Research': ['#RechercheIA', '#DeepLearning'],
        'Hardware': ['#GPU', '#Infrastructure'],
        'Agents': ['#IAAgents', '#Automation'],
        'Autonomous': ['#Autonomous', '#SelfDriving'],
        'Startup': ['#Startup', '#FrenchTech'],
    }

    tags = list(base)
    for cat in categories:
        # Chercher dans config d'abord, puis défaut
        cat_tags = by_category.get(cat, default_by_category.get(cat, []))
        tags.extend(cat_tags[:2])

    # Dédupliquer et limiter
    seen = set()
    unique_tags = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            unique_tags.append(tag)

    return unique_tags[:max_tags]


def analyze_articles(
    input_path: Path,
    config: dict,
    max_articles: int = None
) -> Dict:
    """
    Analyse tous les articles d'un fichier.

    Returns:
        Dict avec les résultats d'analyse
    """
    articles = load_articles(input_path)
    thresholds = config.get('thresholds', {})

    if max_articles is None:
        max_articles = thresholds.get('max_articles_to_analyze', 30)

    logger.info(f"Analyse de {min(len(articles), max_articles)} articles...")

    analyzed = []
    for article in articles[:max_articles]:
        result = score_article(article, config)

        analyzed.append({
            'title': article.get('title'),
            'url': article.get('url'),
            'source': article.get('source_name'),
            'score': result['score'],
            'categories': result['categories'],
            'score_breakdown': result['breakdown'],
            'linkedin_angles': generate_linkedin_angles(article, result['categories']),
            'suggested_hashtags': suggest_hashtags(result['categories'], config)
        })

    # Trier par score décroissant
    analyzed.sort(key=lambda x: x['score'], reverse=True)

    # Statistiques
    min_score = thresholds.get('min_score_for_post', 7)
    top_articles = [a for a in analyzed if a['score'] >= min_score]

    return {
        'date': datetime.utcnow().strftime('%Y-%m-%d'),
        'input_file': str(input_path),
        'total_articles': len(articles),
        'analyzed': len(analyzed),
        'above_threshold': len(top_articles),
        'threshold_used': min_score,
        'top_articles': top_articles[:10],
        'all_analyzed': analyzed
    }


def save_results(results: Dict, output_dir: Path):
    """Sauvegarde les résultats d'analyse"""
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str = results.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
    output_file = output_dir / f"analyzed_{date_str}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"Résultats sauvegardés dans {output_file}")
    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Analyse et score les articles collectés"
    )
    parser.add_argument(
        '--date',
        type=str,
        default=None,
        help="Date des articles à analyser (YYYY-MM-DD)"
    )
    parser.add_argument(
        '--input',
        type=str,
        default=None,
        help="Chemin vers le fichier JSONL à analyser"
    )
    parser.add_argument(
        '--max',
        type=int,
        default=None,
        help="Nombre max d'articles à analyser"
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help="Sortie JSON des résultats"
    )

    args = parser.parse_args()

    # Charger la config
    config = load_scoring_config()

    # Déterminer le fichier d'entrée
    if args.input:
        input_path = Path(args.input)
    else:
        date_str = args.date or datetime.utcnow().strftime('%Y-%m-%d')
        input_path = RAW_DIR / f"articles_{date_str}.jsonl"

    if not input_path.exists():
        logger.error(f"Fichier non trouvé: {input_path}")
        return 1

    # Analyser
    results = analyze_articles(input_path, config, args.max)

    # Sauvegarder
    save_results(results, OUTPUT_DIR)

    # Afficher le résumé
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'='*50}")
        print("RÉSUMÉ DE L'ANALYSE")
        print(f"{'='*50}")
        print(f"Articles analysés: {results['analyzed']}")
        print(f"Score >= {results['threshold_used']}: {results['above_threshold']}")
        print(f"\nTop 5 articles:")
        for i, article in enumerate(results['top_articles'][:5], 1):
            print(f"  {i}. [{article['score']}/10] {article['title'][:60]}...")

    return 0


if __name__ == "__main__":
    exit(main())
