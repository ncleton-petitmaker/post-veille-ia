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
PREFS_PATH = PROJECT_ROOT / "config" / "content_preferences.json"
RAW_DIR = PROJECT_ROOT / "output" / "raw-articles"
OUTPUT_DIR = PROJECT_ROOT / "output" / "analyzed-articles"


def load_scoring_config() -> dict:
    """Charge la configuration de scoring"""
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_content_preferences() -> dict:
    """Charge les préférences de contenu utilisateur"""
    try:
        with open(PREFS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("content_preferences.json non trouvé, utilisation des défauts")
        return {}




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


def extract_keywords_from_text(text: str) -> list:
    """
    Extrait les mots significatifs d'un texte (news_focus de l'utilisateur).
    Ignore les mots vides (stop words).
    """
    # Mots vides à ignorer
    stop_words = {
        'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'au', 'aux',
        'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles',
        'mon', 'ma', 'mes', 'ton', 'ta', 'tes', 'son', 'sa', 'ses',
        'ce', 'cette', 'ces', 'qui', 'que', 'quoi', 'dont', 'où',
        'et', 'ou', 'mais', 'donc', 'car', 'ni', 'si', 'pour', 'par',
        'sur', 'sous', 'dans', 'avec', 'sans', 'entre', 'vers', 'chez',
        'être', 'avoir', 'faire', 'pouvoir', 'vouloir', 'devoir', 'aller',
        'est', 'sont', 'était', 'peut', 'va', 'fait', 'bien', 'plus',
        'se', 'ne', 'pas', 'quels', 'quel', 'quelle', 'quelles',
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
        'to', 'of', 'in', 'on', 'at', 'for', 'with', 'by', 'from',
        'cherche', 'uniquement', 'news', 'peuvent', 'intéresser', 'publique',
        'demande', 'comment', 'pourquoi', 'important', 'autant', 'faire',
        'sujets', 'inclure', 'exclure', 'éviter', 'trop', 'techniques'
    }

    # Nettoyer et extraire les mots
    words = re.findall(r'[a-zA-ZÀ-ÿ]{3,}', text.lower())
    keywords = [w for w in words if w not in stop_words]

    # Retourner les mots uniques
    return list(set(keywords))


def quick_score_title(article: dict, config: dict, preferences: dict) -> float:
    """
    Score rapide basé sur le titre ET le texte news_focus de l'utilisateur.
    Extrait les mots-clés DIRECTEMENT depuis le texte saisi par l'utilisateur.
    """
    title = article.get('title', '')
    source = article.get('source_name', '')
    title_lower = title.lower()

    score = 0.0

    # Extraire les mots-clés depuis le texte news_focus de l'utilisateur
    news_focus = preferences.get('news_focus', '')
    user_keywords = extract_keywords_from_text(news_focus)

    # Score basé sur les mots-clés extraits du news_focus
    matches = sum(1 for kw in user_keywords if kw in title_lower)
    score += min(matches * 2.0, 10.0)

    # Bonus source tier 1/2
    criteria = config.get('scoring_criteria', {})
    source_quality = criteria.get('source_quality', {})
    if source_quality:
        tier1 = source_quality.get('tier_1_sources', [])
        tier2 = source_quality.get('tier_2_sources', [])
        if any(t1.lower() in source.lower() for t1 in tier1):
            score += 2.0
        elif any(t2.lower() in source.lower() for t2 in tier2):
            score += 1.0

    return score


def analyze_articles(
    input_path: Path,
    config: dict,
    max_articles: int = None
) -> Dict:
    """
    Analyse les articles en 2 passes:
    1. Score rapide sur TOUS les titres (basé sur préférences utilisateur)
    2. Analyse complète des meilleurs articles

    Returns:
        Dict avec les résultats d'analyse
    """
    articles = load_articles(input_path)
    thresholds = config.get('thresholds', {})
    preferences = load_content_preferences()

    if max_articles is None:
        max_articles = thresholds.get('max_articles_to_analyze', 30)

    logger.info(f"Phase 1: Score rapide de {len(articles)} titres selon preferences utilisateur...")

    # Phase 1: Score rapide sur tous les titres (basé sur news_focus)
    articles_with_quick_score = []
    for article in articles:
        quick_score = quick_score_title(article, config, preferences)
        articles_with_quick_score.append({
            'article': article,
            'quick_score': quick_score
        })

    # Trier par score rapide et prendre les meilleurs
    articles_with_quick_score.sort(key=lambda x: x['quick_score'], reverse=True)
    top_candidates = [item['article'] for item in articles_with_quick_score[:max_articles]]

    logger.info(f"Phase 2: Analyse complete de {len(top_candidates)} articles selectionnes...")

    # Phase 2: Analyse complète des meilleurs candidats
    analyzed = []
    for article in top_candidates:
        result = score_article(article, config)

        analyzed.append({
            'title': article.get('title'),
            'url': article.get('url'),
            'source': article.get('source_name'),
            'date': article.get('published_at', ''),
            'score': result['score'],
            'categories': result['categories'],
            'score_breakdown': result['breakdown'],
            'linkedin_angles': generate_linkedin_angles(article, result['categories']),
            'suggested_hashtags': suggest_hashtags(result['categories'], config)
        })

    # Trier par score final décroissant
    analyzed.sort(key=lambda x: x['score'], reverse=True)

    # Statistiques
    min_score = thresholds.get('min_score_for_post', 7)
    max_posts = thresholds.get('max_posts_per_day', 15)
    top_articles = [a for a in analyzed if a['score'] >= min_score]

    return {
        'date': datetime.utcnow().strftime('%Y-%m-%d'),
        'input_file': str(input_path),
        'total_articles': len(articles),
        'analyzed': len(analyzed),
        'above_threshold': len(top_articles),
        'threshold_used': min_score,
        'max_posts_per_day': max_posts,
        'top_articles': top_articles[:max_posts],
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
