"""life_memory.py — searchable life memory (knowledge-graph-lite, v3.2).

Stores memories as (subject → relation → target) triples, e.g.

    Boss  --loves-->            cold brew
    Boss  --won't apply below--> 7 LPA
    Mom   --birthday-->          15 September

instead of isolated key/value facts, so FRIDAY can answer questions from
*connected* information ("what do I like? cold brew", "which salary do I
avoid?"). Token-overlap search over subject/relation/target/note makes every
memory findable later.
"""

import re
import sqlite3
import threading
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "friday_brain.db"
_lock = threading.RLock()


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_life_memory_db():
    with _lock, _connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS life_memories (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            subject    TEXT NOT NULL,
            relation   TEXT NOT NULL,
            target     TEXT NOT NULL,
            note       TEXT DEFAULT '',
            category   TEXT DEFAULT 'personal',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_life_mem_subject ON life_memories(subject)")
        conn.commit()


init_life_memory_db()


def save_memory(subject: str, relation: str, target: str,
                category: str = "personal", note: str = "") -> int:
    """Persist a (subject, relation, target) memory triple."""
    subject = (subject or "Boss").strip()
    relation = (relation or "remembers").strip()
    target = (target or "").strip()
    if not target:
        raise ValueError("target is required")
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO life_memories (subject, relation, target, note, category) "
            "VALUES (?, ?, ?, ?, ?)",
            (subject, relation, target, note.strip(), category))
        conn.commit()
        return cur.lastrowid


def list_memories(category: str = None, limit: int = 100) -> list:
    with _lock, _connect() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM life_memories WHERE category = ? ORDER BY id DESC LIMIT ?",
                (category, limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM life_memories ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def delete_memory(memory_id: int) -> bool:
    with _lock, _connect() as conn:
        cur = conn.execute("DELETE FROM life_memories WHERE id = ?", (memory_id,))
        conn.commit()
        return cur.rowcount > 0


def _tokens(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def search_memories(query: str, limit: int = 8) -> list:
    """Token-overlap search across subject/relation/target/note.

    Uses full-token matches plus prefix matches so "love" still finds
    "loves" and "salary" finds "minimum_salary" style phrasing.
    """
    qt = _tokens(query or "")
    if not qt:
        return []
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM life_memories ORDER BY id DESC LIMIT 500").fetchall()

    def _score(qtok: set, stok: set) -> float:
        full = len(qtok & stok)
        partial = 0
        for q in qtok:
            if any(s.startswith(q) or q.startswith(s) for s in stok):
                partial += 1
        return (full + 0.5 * partial) / len(qt)

    scored = []
    for r in rows:
        text = f"{r['subject']} {r['relation']} {r['target']} {r['note']}"
        stok = _tokens(text)
        score = _score(qt, stok)
        if score > 0:
            scored.append((score, dict(r)))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:limit]]


def answer_memory_query(query: str) -> str:
    """Human-readable answer from life memory ("I remember: ...")."""
    results = search_memories(query, limit=3)
    if not results:
        return f"I don't remember anything about '{query}' yet. Tell me and I'll store it."
    parts = [f"{r['subject']} {r['relation']} {r['target']}" for r in results]
    return "I remember: " + "; ".join(parts) + "."
