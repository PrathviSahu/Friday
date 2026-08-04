"""notifications.py — in-app notification center (v3.1).

Automations, the daily briefing, job scans, and market alerts all land here
instead of interrupting the user. The HUD Notification Center panel reads
this table; Telegram can push it later.
"""

import sqlite3
import threading
import time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "friday_brain.db"
_lock = threading.RLock()


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_notifications_db():
    with _lock, _connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            title      TEXT NOT NULL,
            body       TEXT NOT NULL,
            category   TEXT DEFAULT 'general',
            is_read    INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()


init_notifications_db()


def push_notification(title: str, body: str, category: str = "general") -> int:
    """Insert a notification and return its id."""
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO notifications (title, body, category) VALUES (?, ?, ?)",
            (title[:200], body[:2000], category),
        )
        conn.commit()
        return cur.lastrowid


def get_notifications(limit: int = 50, unread_only: bool = False) -> list:
    with _lock, _connect() as conn:
        q = "SELECT * FROM notifications"
        if unread_only:
            q += " WHERE is_read = 0"
        q += " ORDER BY id DESC LIMIT ?"
        rows = conn.execute(q, (limit,)).fetchall()
    return [dict(r) for r in rows]


def mark_read(notification_id: int) -> bool:
    with _lock, _connect() as conn:
        cur = conn.execute(
            "UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,)
        )
        conn.commit()
        return cur.rowcount > 0


def unread_count() -> int:
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM notifications WHERE is_read = 0"
        ).fetchone()
    return row["c"] if row else 0
