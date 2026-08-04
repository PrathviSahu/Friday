"""services/embeddings.py — Semantic memory (RAG) for the AI brain.

Indexes FRIDAY's long-term knowledge (saved facts, knowledge notes, meeting
summaries) as vectors using Google Gemini `text-embedding-004` (free tier),
then retrieves the most relevant snippets for any user query — so Friday can
answer "any big meetings coming up?" even if you never said those exact words.

Design:
  * Own SQLite store (data/embeddings.db), one row per source item.
  * Pure-Python cosine similarity via numpy (personal scale — fine).
  * Fully graceful: no GEMINI_API_KEY → available()=False and callers fall
    back to keyword search. Indexing is lazy + TTL-refreshed; a broken
    embedder never breaks a chat turn.
"""

import json
import os
import sqlite3
import threading
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "embeddings.db"
_lock = threading.Lock()
INDEX_TTL_SECONDS = 300  # re-index at most every 5 minutes
_last_indexed = [0.0]

EMBED_MODEL = os.getenv("FRIDAY_EMBED_MODEL", "text-embedding-004")

_embedder = None


def init_embeddings_db():
    with _lock, _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                source_type TEXT NOT NULL,
                source_id   TEXT NOT NULL,
                text        TEXT NOT NULL,
                vector      TEXT NOT NULL,
                updated_at  REAL NOT NULL,
                PRIMARY KEY (source_type, source_id)
            )
        """)
        conn.commit()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


# ── Embedding client (lazy, guarded) ─────────────────────────────────────

def _get_embedder():
    """Return a callable embed(texts: list[str]) -> list[list[float]], or None."""
    global _embedder
    if _embedder is not None:
        return _embedder
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or key == "your_key_here":
        return None
    try:
        from google import genai
        client = genai.Client(api_key=key)

        def embed(texts):
            resp = client.models.embed_content(model=EMBED_MODEL, contents=list(texts))
            return [e.values for e in resp.embeddings]

        _embedder = embed
        return _embedder
    except Exception as exc:
        print(f"[Embeddings] Gemini embedder unavailable: {exc}")
        return None


def available() -> bool:
    return _get_embedder() is not None


# ── Vector math ──────────────────────────────────────────────────────────

def _cosine(a: list, b: list) -> float:
    import numpy as np
    va, vb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    denom = (np.linalg.norm(va) * np.linalg.norm(vb)) or 1e-9
    return float(np.dot(va, vb) / denom)


# ── Indexing ─────────────────────────────────────────────────────────────

def _embed_and_store(source_type: str, source_id: str, text: str) -> bool:
    embed = _get_embedder()
    if embed is None or not text.strip():
        return False
    try:
        vectors = embed([text.strip()[:2000]])
        if not vectors:
            return False
        with _lock, _connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO embeddings (source_type, source_id, text, vector, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (source_type, source_id, text.strip()[:2000], json.dumps(vectors[0]), time.time()),
            )
            conn.commit()
        return True
    except Exception:
        return False


def index_text(source_type: str, source_id: str, text: str) -> bool:
    """Public hook for services to index a new item (guarded, non-blocking)."""
    try:
        return _embed_and_store(source_type, source_id, text)
    except Exception:
        return False


def _collect_sources() -> list:
    """(source_type, source_id, text) for everything worth remembering."""
    sources = []
    try:
        from services.learning_engine import get_all_memories
        for m in get_all_memories() or []:
            sources.append(("memory", f"{m.get('category')}:{m.get('key')}",
                            f"{m.get('key')}: {m.get('value')}"))
    except Exception:
        pass
    try:
        from services.knowledge import list_notes
        for n in list_notes(limit=300) or []:
            sources.append(("note", str(n.get("id")),
                            f"{n.get('title')} — {n.get('content')}"))
    except Exception:
        pass
    try:
        from services.meeting_agent import list_meetings
        for m in list_meetings(limit=100) or []:
            sources.append(("meeting", m.get("id"),
                            f"Meeting {m.get('title')}: {m.get('summary')}"))
    except Exception:
        pass
    return sources


def ensure_indexed(force: bool = False) -> bool:
    """Index all sources if the index is empty or stale. Returns True if fresh."""
    if _get_embedder() is None:
        return False
    now = time.time()
    if not force and now - _last_indexed[0] < INDEX_TTL_SECONDS:
        return True
    try:
        with _lock, _connect() as conn:
            count = conn.execute("SELECT COUNT(*) AS c FROM embeddings").fetchone()["c"]
        if count > 0 and not force:
            _last_indexed[0] = now
            return True
        sources = _collect_sources()
        for stype, sid, text in sources:
            _embed_and_store(stype, sid, text)
        _last_indexed[0] = time.time()
        return True
    except Exception:
        return False


# ── Retrieval ────────────────────────────────────────────────────────────

def retrieve(query: str, k: int = 4) -> list:
    """Top-k semantically similar stored items for `query`.

    Returns [{"text": str, "source": str, "score": float}, ...] — empty when
    embeddings are unavailable or nothing is indexed.
    """
    embed = _get_embedder()
    if embed is None or not (query or "").strip():
        return []
    try:
        ensure_indexed()
        vectors = embed([query.strip()[:2000]])
        if not vectors:
            return []
        qv = vectors[0]
        with _lock, _connect() as conn:
            rows = conn.execute("SELECT source_type, text, vector FROM embeddings").fetchall()
        scored = []
        for r in rows:
            try:
                score = _cosine(qv, json.loads(r["vector"]))
            except Exception:
                continue
            if score > 0.25:  # ignore unrelated items
                scored.append({"text": r["text"], "source": r["source_type"], "score": score})
        scored.sort(key=lambda x: -x["score"])
        return scored[:k]
    except Exception:
        return []


def semantic_context(query: str, k: int = 4) -> str:
    """Formatted 'RELEVANT MEMORIES' block for the brain prompt (or '')."""
    items = retrieve(query, k=k)
    if not items:
        return ""
    lines = ["Relevant memories for this request:"]
    for it in items:
        lines.append(f"- [{it['source']}] {it['text'][:300]}")
    return "\n".join(lines)


# ── Convenience hooks for services (guarded) ─────────────────────────────

def on_fact_saved(key: str, value: str) -> None:
    try:
        index_text("memory", f"fact:{key}", f"{key}: {value}")
    except Exception:
        pass


def on_note_added(title: str, content: str, note_id=None) -> None:
    try:
        index_text("note", str(note_id or title), f"{title} — {content}")
    except Exception:
        pass


def on_meeting_saved(title: str, summary: str, meeting_id=None) -> None:
    try:
        index_text("meeting", str(meeting_id or title), f"Meeting {title}: {summary}")
    except Exception:
        pass


init_embeddings_db()
