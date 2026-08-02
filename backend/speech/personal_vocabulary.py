"""
personal_vocabulary.py — Personal Vocabulary & User Speech Correction Engine.
Learns from owner corrections ("No, I meant Arijit Singh version") and applies personal dictionary rules.
"""

import time
import re
from typing import Dict, Any, Optional
from database.connection import get_db_connection

def init_speech_corrections_db():
    """Initializes speech_corrections table."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS speech_corrections (
                id TEXT PRIMARY KEY,
                original_text TEXT NOT NULL UNIQUE,
                corrected_text TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                created_at REAL NOT NULL,
                use_count INTEGER DEFAULT 1
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_speech_orig ON speech_corrections(original_text);")
        conn.commit()

class PersonalVocabularyEngine:
    def __init__(self):
        init_speech_corrections_db()

    def apply_corrections(self, transcript: str) -> str:
        """Applies saved personal vocabulary corrections to transcript."""
        if not transcript:
            return ""

        clean = transcript.strip()
        clean_lower = clean.lower()

        with get_db_connection() as conn:
            # 1. Exact phrase lookup
            cursor = conn.execute("SELECT corrected_text, id FROM speech_corrections WHERE original_text = ?", (clean_lower,))
            row = cursor.fetchone()
            if row:
                conn.execute("UPDATE speech_corrections SET use_count = use_count + 1 WHERE id = ?", (row["id"],))
                conn.commit()
                return row["corrected_text"]

            # 2. Substring replacements for saved custom vocabulary terms
            cursor = conn.execute("SELECT original_text, corrected_text FROM speech_corrections ORDER BY LENGTH(original_text) DESC")
            all_corrections = cursor.fetchall()
            for orig, corr in all_corrections:
                pattern = re.compile(re.escape(orig), re.IGNORECASE)
                if pattern.search(clean):
                    clean = pattern.sub(corr, clean)

        return clean

    def record_correction(self, original_text: str, corrected_text: str) -> bool:
        """Permanently records a user speech correction so FRIDAY learns immediately."""
        import uuid
        orig_clean = original_text.strip().lower()
        corr_clean = corrected_text.strip()
        if not orig_clean or not corr_clean:
            return False

        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO speech_corrections (id, original_text, corrected_text, created_at, use_count)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(original_text) DO UPDATE SET
                    corrected_text = excluded.corrected_text,
                    use_count = speech_corrections.use_count + 1
                """,
                (uuid.uuid4().hex, orig_clean, corr_clean, time.time())
            )
            conn.commit()
            return True
