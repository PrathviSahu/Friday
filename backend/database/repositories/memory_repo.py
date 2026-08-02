"""
memory_repo.py — Dedicated repository for domain-categorized AI memory storage and retrieval.
Supports category filtering, importance ranking, and tag-based searches.
"""

import uuid
import time
from typing import List, Dict, Any, Optional
from ..connection import get_db_connection

def init_memory_db():
    """Initializes the structured ai_memory table and performance indexes."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_memory (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                importance INTEGER DEFAULT 1,
                source TEXT DEFAULT 'user',
                content TEXT NOT NULL,
                tags TEXT,
                created_at REAL NOT NULL,
                last_used REAL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_category ON ai_memory(category);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_importance ON ai_memory(importance);")
        conn.commit()

class MemoryRepository:
    def __init__(self):
        init_memory_db()

    def save_memory(self, content: str, category: str = "general", importance: int = 1, source: str = "user", tags: str = "") -> Dict[str, Any]:
        """Saves a new memory entry."""
        mem_id = uuid.uuid4().hex
        now = time.time()
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO ai_memory (id, category, importance, source, content, tags, created_at, last_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (mem_id, category.lower(), importance, source, content, tags, now, now)
            )
            conn.commit()
        return {
            "id": mem_id,
            "category": category,
            "importance": importance,
            "content": content,
            "tags": tags,
            "created_at": now
        }

    def get_memories_by_category(self, category: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves memories for a specific domain category ordered by importance and freshness."""
        with get_db_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM ai_memory 
                WHERE category = ? 
                ORDER BY importance DESC, created_at DESC 
                LIMIT ?
                """,
                (category.lower(), limit)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def search_memories(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Searches memories by keyword content or tags."""
        pattern = f"%{query.lower()}%"
        with get_db_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM ai_memory 
                WHERE LOWER(content) LIKE ? OR LOWER(tags) LIKE ?
                ORDER BY importance DESC, created_at DESC 
                LIMIT ?
                """,
                (pattern, pattern, limit)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
