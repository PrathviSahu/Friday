"""
song_memory_repo.py — Song Alias & Contextual Memory Repository.
Stores custom song aliases ("gym song", "coding music", "breakup song") to bypass search fuzzy matching.
"""

import uuid
import time
from typing import Optional, Dict, Any, List
from ..connection import get_db_connection

def init_song_memory_db():
    """Initializes the song_memory table and performance indexes."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS song_memory (
                id TEXT PRIMARY KEY,
                alias TEXT NOT NULL UNIQUE,
                song_name TEXT NOT NULL,
                artist TEXT,
                spotify_uri TEXT,
                created_at REAL NOT NULL,
                last_used REAL,
                use_count INTEGER DEFAULT 1
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_song_memory_alias ON song_memory(alias);")
        
        # Seed initial default song aliases if database is empty
        cursor = conn.execute("SELECT COUNT(*) FROM song_memory")
        if cursor.fetchone()[0] == 0:
            now = time.time()
            defaults = [
                (uuid.uuid4().hex, "gym song", "Believer", "Imagine Dragons", "spotify:track:08m1DywosR42BDT0kYOFyB", now, now, 1),
                (uuid.uuid4().hex, "my gym song", "Believer", "Imagine Dragons", "spotify:track:08m1DywosR42BDT0kYOFyB", now, now, 1),
                (uuid.uuid4().hex, "coding music", "Interstellar Main Theme", "Hans Zimmer", "spotify:track:6ybVivXRLIyC3XjWyAM2ft", now, now, 1),
                (uuid.uuid4().hex, "breakup song", "Bekhayali (Arijit Singh Version)", "Arijit Singh", "spotify:track:18D6852nLcvJ7L80rU7uH1", now, now, 1),
                (uuid.uuid4().hex, "relaxing song", "Kesariya", "Arijit Singh", "spotify:track:6VhuP93xyzc5eT0v55Ww84", now, now, 1),
            ]
            conn.executemany(
                "INSERT INTO song_memory (id, alias, song_name, artist, spotify_uri, created_at, last_used, use_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                defaults
            )
        conn.commit()

class SongMemoryRepository:
    def __init__(self):
        init_song_memory_db()

    def save_alias(self, alias: str, song_name: str, artist: str = "", spotify_uri: str = "") -> Dict[str, Any]:
        """Saves or updates a custom song alias."""
        clean_alias = alias.strip().lower()
        now = time.time()
        mem_id = uuid.uuid4().hex

        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO song_memory (id, alias, song_name, artist, spotify_uri, created_at, last_used, use_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(alias) DO UPDATE SET
                    song_name = excluded.song_name,
                    artist = excluded.artist,
                    spotify_uri = excluded.spotify_uri,
                    last_used = excluded.last_used,
                    use_count = song_memory.use_count + 1
                """,
                (mem_id, clean_alias, song_name.strip(), artist.strip(), spotify_uri.strip(), now, now)
            )
            conn.commit()

        return {
            "alias": clean_alias,
            "song_name": song_name,
            "artist": artist,
            "spotify_uri": spotify_uri
        }

    def lookup_alias(self, alias_query: str) -> Optional[Dict[str, Any]]:
        """Looks up a song by custom alias or natural phrase."""
        clean = alias_query.strip().lower()
        with get_db_connection() as conn:
            # 1. Exact match lookup
            cursor = conn.execute("SELECT * FROM song_memory WHERE alias = ?", (clean,))
            row = cursor.fetchone()
            
            # 2. Substring containment lookup (e.g. user says "play my gym song please")
            if not row:
                cursor = conn.execute("SELECT * FROM song_memory WHERE ? LIKE '%' || alias || '%'", (clean,))
                row = cursor.fetchone()

            if row:
                data = dict(row)
                # Update last_used and use_count in background
                conn.execute(
                    "UPDATE song_memory SET last_used = ?, use_count = use_count + 1 WHERE id = ?",
                    (time.time(), data["id"])
                )
                conn.commit()
                return data

        return None

    def list_all_aliases(self) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM song_memory ORDER BY use_count DESC, last_used DESC")
            return [dict(row) for row in cursor.fetchall()]
