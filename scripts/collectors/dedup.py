"""
Déduplication - Post Veille IA
US-2.7 : Déduplication

Gère la déduplication des articles via SQLite.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Set
import json

from .schema import Article

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Chemin par défaut de la base
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "veille.db"


class DeduplicationDB:
    """Gestionnaire de déduplication SQLite"""

    def __init__(self, db_path: str = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialise la base de données"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS seen_articles (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    title TEXT,
                    source_name TEXT,
                    source_type TEXT,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_seen_at
                ON seen_articles(first_seen_at)
            """)
            conn.commit()

    def is_seen(self, article_id: str) -> bool:
        """Vérifie si un article a déjà été vu"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM seen_articles WHERE id = ?",
                (article_id,)
            )
            return cursor.fetchone() is not None

    def mark_seen(self, article: Article):
        """Marque un article comme vu"""
        now = datetime.utcnow().isoformat() + "Z"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO seen_articles (id, url, title, source_name, source_type, first_seen_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET last_seen_at = ?
            """, (
                article.id,
                article.url,
                article.title[:200],
                article.source_name,
                article.source_type,
                now, now, now
            ))
            conn.commit()

    def get_seen_ids(self) -> Set[str]:
        """Récupère tous les IDs déjà vus"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id FROM seen_articles")
            return {row[0] for row in cursor.fetchall()}

    def cleanup_old(self, retention_days: int = 7):
        """Supprime les entrées plus vieilles que retention_days"""
        cutoff = (datetime.utcnow() - timedelta(days=retention_days)).isoformat() + "Z"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM seen_articles WHERE first_seen_at < ?",
                (cutoff,)
            )
            deleted = cursor.rowcount
            conn.commit()

        if deleted > 0:
            logger.info(f"Nettoyage: {deleted} anciennes entrées supprimées")

        return deleted

    def get_stats(self) -> dict:
        """Retourne des statistiques sur la base"""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM seen_articles").fetchone()[0]

            by_source = {}
            cursor = conn.execute(
                "SELECT source_type, COUNT(*) FROM seen_articles GROUP BY source_type"
            )
            for row in cursor.fetchall():
                by_source[row[0]] = row[1]

            return {
                "total_articles": total,
                "by_source_type": by_source
            }


def deduplicate_articles(articles: List[Article], db_path: str = None) -> List[Article]:
    """
    Filtre les articles déjà vus et marque les nouveaux comme vus.

    Args:
        articles: Liste d'articles à filtrer
        db_path: Chemin vers la base SQLite

    Returns:
        Liste d'articles non vus
    """
    db = DeduplicationDB(db_path)

    # Nettoyer les vieilles entrées
    db.cleanup_old(retention_days=7)

    # Récupérer les IDs déjà vus
    seen_ids = db.get_seen_ids()

    # Filtrer et marquer
    new_articles = []
    for article in articles:
        if article.id not in seen_ids:
            new_articles.append(article)
            db.mark_seen(article)
        else:
            logger.debug(f"Article déjà vu: {article.title[:50]}")

    logger.info(f"Déduplication: {len(new_articles)} nouveaux / {len(articles)} total")

    return new_articles


if __name__ == "__main__":
    # Test
    db = DeduplicationDB()
    stats = db.get_stats()
    print(f"Stats DB: {stats}")
