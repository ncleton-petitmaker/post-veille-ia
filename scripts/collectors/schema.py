"""
Schema de données pour Post Veille IA
US-2.6 : Normalisation des données
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional
import hashlib
import json


@dataclass
class Article:
    """Structure normalisée d'un article collecté"""

    # Identifiants
    id: str                          # Hash SHA256 de l'URL
    url: str                         # URL source

    # Contenu
    title: str                       # Titre de l'article
    content: str                     # Contenu complet (texte ou markdown)
    summary: Optional[str] = None    # Résumé si disponible

    # Métadonnées source
    source_name: str = ""            # Nom de la source (OpenAI Blog, Reddit, etc.)
    source_type: str = ""            # Type: rss, jina, reddit, discord, youtube
    source_category: str = ""        # Catégorie: official, news, community, research

    # Dates
    published_at: Optional[str] = None   # Date de publication (ISO 8601)
    collected_at: str = ""               # Date de collecte (ISO 8601)

    # Métadonnées additionnelles
    language: str = "en"             # Langue détectée
    author: Optional[str] = None     # Auteur si disponible
    tags: List[str] = None           # Tags/catégories d'origine

    # Spécifique Reddit
    score: Optional[int] = None      # Upvotes (Reddit)
    num_comments: Optional[int] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if not self.collected_at:
            self.collected_at = datetime.utcnow().isoformat() + "Z"
        if not self.id:
            self.id = self.generate_id()

    def generate_id(self) -> str:
        """Génère un ID unique basé sur l'URL"""
        return hashlib.sha256(self.url.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        """Convertit en dictionnaire"""
        return asdict(self)

    def to_json(self) -> str:
        """Convertit en JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> 'Article':
        """Crée un Article depuis un dictionnaire"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class AnalyzedArticle:
    """Article avec analyse Claude"""

    # Article original
    article: Article

    # Analyse
    relevance_score: float           # Score 1-10
    score_justification: str         # Pourquoi ce score
    categories: List[str]            # LLMs, Safety, Enterprise, etc.

    # Pour LinkedIn
    linkedin_angles: List[str]       # 2-3 angles suggérés
    hashtags: List[str]              # Hashtags recommandés
    suggested_post_type: str         # astuce, decryptage, prospective, etc.

    # Métadonnées
    analyzed_at: str = ""

    def __post_init__(self):
        if not self.analyzed_at:
            self.analyzed_at = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> dict:
        data = asdict(self)
        data['article'] = self.article.to_dict()
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class LinkedInDraft:
    """Draft de post LinkedIn"""

    # Référence
    id: str                          # UUID du draft
    article_id: str                  # ID de l'article source

    # Contenu
    post_type: str                   # astuce, decryptage, prospective, etc.
    length_type: str                 # short, standard, long
    content: str                     # Le post complet

    # Métadonnées
    char_count: int = 0
    word_count: int = 0
    hashtags: List[str] = None

    # Statut
    status: str = "draft"            # draft, ready, published, rejected
    notes: str = ""                  # Notes personnelles

    # Dates
    created_at: str = ""
    suggested_publish_time: Optional[str] = None

    def __post_init__(self):
        if self.hashtags is None:
            self.hashtags = []
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat() + "Z"
        self.char_count = len(self.content)
        self.word_count = len(self.content.split())

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# Catégories disponibles
CATEGORIES = [
    "LLMs",           # Modèles de langage (GPT, Claude, Llama...)
    "Safety",         # Sécurité, alignement, éthique IA
    "Vision",         # IA vision, images, vidéo
    "Enterprise",     # IA en entreprise, déploiement, ROI
    "Research",       # Recherche académique, papers
    "Tools",          # Outils, applications, produits
    "Startup",        # Startups, levées de fonds, acquisitions
    "Regulation",     # Régulation, lois, politique
    "Open Source",    # Projets open source
    "Hardware",       # GPU, TPU, infrastructure
]

# Types de posts LinkedIn
POST_TYPES = [
    "astuce",         # Conseil pratique
    "decryptage",     # Analyse d'actualité
    "prospective",    # Vision long terme
    "cas_usage",      # Exemple en entreprise
    "alerte",         # Point de vigilance
    "reflexion",      # Partage personnel
]
