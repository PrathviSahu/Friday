"""knowledge.py — Second Brain (Knowledge OS, v3.3).

A searchable knowledge base that automatically stores meeting notes, ideas,
research, code snippets, interview experiences, project decisions, book
notes and YouTube summaries — everything searchable later.

"Friday, where did I save that Kafka architecture idea?" → search finds it.

Idea Capture: when you interrupt with an idea and no type, `auto_categorize`
picks the note type from the text so FRIDAY "categorizes it automatically".
Project Intelligence: every note can be tied to a project, and each project
gets its own structured memory (architecture/tasks/bugs/roadmap/decisions).
"""

import json
import re
import sqlite3
import threading
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "friday_brain.db"
_lock = threading.RLock()

NOTE_TYPES = [
    "meeting", "idea", "research", "code_snippet", "interview",
    "decision", "book", "youtube", "general",
]

PROJECT_SECTIONS = [
    "architecture", "tasks", "bugs", "roadmap", "ideas",
    "completed", "documentation", "github", "dependencies",
]

# keyword -> type for auto-categorization
_AUTO_CATEGORY_RULES = [
    (["meeting", "sync", "standup", "call with"], "meeting"),
    (["idea", "think", "maybe we", "what if", "concept"], "idea"),
    (["research", "compare", "benchmark", "docs", "documentation"], "research"),
    (["code", "snippet", "function", "bug", "error", "regex", "kafka"], "code_snippet"),
    (["interview", "round", "question they asked"], "interview"),
    (["decided", "decision", "we chose", "we picked", "why we"], "decision"),
    (["book", "chapter", "read"], "book"),
    (["youtube", "video", "course"], "youtube"),
]


def auto_categorize(text: str) -> str:
    t = (text or "").lower()
    for keywords, ntype in _AUTO_CATEGORY_RULES:
        if any(k in t for k in keywords):
            return ntype
    return "general"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_knowledge_db():
    with _lock, _connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS kb_notes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            type       TEXT NOT NULL DEFAULT 'general',
            title      TEXT NOT NULL,
            content    TEXT NOT NULL,
            tags       TEXT DEFAULT '[]',
            project    TEXT,
            source_url TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        # project_memory: composite key (project, section) so a project can
        # hold MULTIPLE sections. The first version of this table wrongly used
        # `project TEXT PRIMARY KEY`, which capped each project at one section
        # and raised IntegrityError on the second write. Recreate if needed —
        # detected via PRAGMA table_info (robust to SQL formatting/quoting).
        cols = conn.execute(
            "PRAGMA table_info(project_memory)").fetchall()
        pk_cols = [r["name"] for r in cols if r["pk"] > 0]
        if cols and pk_cols != ["project", "section"]:
            conn.execute("DROP TABLE project_memory")
            cols = []
        if not cols:
            conn.execute("""
            CREATE TABLE project_memory (
                project  TEXT NOT NULL,
                section  TEXT NOT NULL,
                content  TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (project, section)
            )""")
        conn.commit()


init_knowledge_db()


# ═══════════════════════════════════════════════════════════════════════════════
# Notes (Second Brain)
# ═══════════════════════════════════════════════════════════════════════════════

def add_note(title: str, content: str, note_type: str = None, tags: list = None,
             project: str = None, source_url: str = "") -> int:
    """Add a note. `note_type` auto-detected when omitted (idea capture)."""
    title = (title or "").strip() or "Untitled note"
    content = (content or "").strip()
    ntype = note_type or auto_categorize(f"{title} {content}")
    if ntype not in NOTE_TYPES:
        ntype = "general"
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO kb_notes (type, title, content, tags, project, source_url) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ntype, title[:300], content[:10000], json.dumps(tags or []),
             (project or "").strip() or None, source_url))
        conn.commit()
        return cur.lastrowid


def list_notes(note_type: str = None, project: str = None, limit: int = 100) -> list:
    q = "SELECT * FROM kb_notes"
    conds, params = [], []
    if note_type:
        conds.append("type = ?")
        params.append(note_type)
    if project:
        conds.append("project = ?")
        params.append(project)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with _lock, _connect() as conn:
        rows = conn.execute(q, params).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["tags"] = json.loads(d.get("tags") or "[]")
        except Exception:
            d["tags"] = []
        result.append(d)
    return result


def delete_note(note_id: int) -> bool:
    with _lock, _connect() as conn:
        cur = conn.execute("DELETE FROM kb_notes WHERE id = ?", (note_id,))
        conn.commit()
        return cur.rowcount > 0


def _tokens(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def search_notes(query: str, limit: int = 8) -> list:
    """Token + prefix search over title/content/tags/project."""
    qt = _tokens(query or "")
    if not qt:
        return []
    with _lock, _connect() as conn:
        rows = conn.execute("SELECT * FROM kb_notes ORDER BY id DESC LIMIT 800").fetchall()
    scored = []
    for r in rows:
        try:
            tags = " ".join(json.loads(r["tags"] or "[]"))
        except Exception:
            tags = ""
        text = f"{r['title']} {r['content']} {tags} {r['project'] or ''}"
        stok = _tokens(text)
        full = len(qt & stok)
        partial = sum(1 for q in qt if any(s.startswith(q) or q.startswith(s) for s in stok))
        score = (full + 0.5 * partial) / len(qt)
        if score > 0:
            d = dict(r)
            try:
                d["tags"] = json.loads(d.get("tags") or "[]")
            except Exception:
                d["tags"] = []
            scored.append((score, d))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:limit]]


def answer_notes_query(query: str) -> str:
    """Natural-language recall: 'where did I save that Kafka idea?'"""
    results = search_notes(query, limit=3)
    if not results:
        return f"I couldn't find anything about '{query}' in your notes. Say 'Friday, remember this…' to save it."
    parts = []
    for n in results:
        loc = n["project"] or f"in {n['type'].replace('_', ' ')}"
        parts.append(f"'{n['title']}' — {loc}")
    return "Found: " + "; ".join(parts) + "."


# ═══════════════════════════════════════════════════════════════════════════════
# Project Intelligence
# ═══════════════════════════════════════════════════════════════════════════════

def set_project_section(project: str, section: str, content: str) -> bool:
    project = (project or "").strip()
    section = (section or "").strip().lower()
    if not project or section not in PROJECT_SECTIONS:
        return False
    with _lock, _connect() as conn:
        conn.execute("""
        INSERT INTO project_memory (project, section, content, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(project, section) DO UPDATE SET
            content = excluded.content, updated_at = CURRENT_TIMESTAMP
        """, (project, section, content))
        conn.commit()
        return True


def get_project_memory(project: str) -> dict:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT section, content FROM project_memory WHERE project = ?",
            (project,)).fetchall()
    return {r["section"]: r["content"] for r in rows}


def list_projects() -> list:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT project, COUNT(*) AS sections FROM project_memory GROUP BY project"
        ).fetchall()
    return [dict(r) for r in rows]
