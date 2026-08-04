"""timeline.py — AI Memory Timeline (v3.3).

Maintains a chronological timeline of meaningful events (milestones,
certifications, applications, projects started/finished, skills learned)
instead of isolated memories. Queryable:

    "Friday, what changed last month?"   → summarize_period(last 30 days)
    "Show me my progress this year."     → summarize_period(year start → now)

`snapshot_from_existing()` derives a free timeline from data FRIDAY already
tracks (job applications, learning sessions, remembered facts), so the
timeline is useful immediately even before you log milestones manually.
"""

import sqlite3
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "friday_brain.db"
_lock = threading.RLock()

CATEGORIES = ("career", "learning", "project", "skill", "milestone", "personal")


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_timeline_db():
    with _lock, _connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS timeline_events (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            event    TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'milestone',
            event_date TEXT NOT NULL,          -- ISO date
            detail   TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_timeline_date ON timeline_events(event_date)")
        conn.commit()


init_timeline_db()


def add_event(event: str, category: str = "milestone", event_date: str = None,
              detail: str = "") -> int:
    event = (event or "").strip()
    if not event:
        raise ValueError("event is required")
    if category not in CATEGORIES:
        category = "milestone"
    d = event_date or date.today().isoformat()
    # normalize any parseable date
    try:
        d = date.fromisoformat(d).isoformat()
    except ValueError:
        d = date.today().isoformat()
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO timeline_events (event, category, event_date, detail) "
            "VALUES (?, ?, ?, ?)", (event, category, d, detail.strip()))
        conn.commit()
        return cur.lastrowid


def list_events(category: str = None, since: str = None, until: str = None,
                limit: int = 200) -> list:
    q = "SELECT * FROM timeline_events"
    conds, params = [], []
    if category:
        conds.append("category = ?")
        params.append(category)
    if since:
        conds.append("event_date >= ?")
        params.append(since)
    if until:
        conds.append("event_date <= ?")
        params.append(until)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY event_date DESC, id DESC LIMIT ?"
    params.append(limit)
    with _lock, _connect() as conn:
        rows = conn.execute(q, params).fetchall()
    return [dict(r) for r in rows]


def delete_event(event_id: int) -> bool:
    with _lock, _connect() as conn:
        cur = conn.execute("DELETE FROM timeline_events WHERE id = ?", (event_id,))
        conn.commit()
        return cur.rowcount > 0


def snapshot_from_existing() -> list:
    """Free 'auto timeline' derived from data FRIDAY already tracks."""
    events = []
    # Job applications (applied_at exists)
    try:
        from services.career_db import get_applications
        for app in get_applications() or []:
            applied = app.get("applied_at")
            if applied:
                events.append({
                    "event": f"Applied to {app.get('company_name') or app.get('job_title') or 'a job'}",
                    "category": "career",
                    "event_date": applied[:10],
                    "detail": app.get("job_title", ""),
                })
    except Exception:
        pass
    # First learning session per track = milestone
    try:
        from services.learning import _connect as learn_conn
        with learn_conn() as conn:
            rows = conn.execute(
                "SELECT category, MIN(log_date) AS first_date FROM learning_log "
                "GROUP BY category").fetchall()
        labels = {"dsa": "Started DSA practice", "java": "Started Java roadmap",
                  "system_design": "Started System Design", "aws": "Started AWS",
                  "interview_prep": "Started interview prep"}
        for r in rows:
            if r["first_date"]:
                events.append({
                    "event": labels.get(r["category"], f"Started {r['category']}"),
                    "category": "learning",
                    "event_date": r["first_date"],
                    "detail": "",
                })
    except Exception:
        pass
    # Sort newest first
    events.sort(key=lambda e: e["event_date"], reverse=True)
    return events


def summarize_period(since: str, until: str = None) -> dict:
    """Group timeline events in [since, until] by category + build a summary."""
    until = until or date.today().isoformat()
    events = list_events(since=since, until=until, limit=500)
    auto = [e for e in snapshot_from_existing()
            if since <= e["event_date"] <= until]
    # Merge: manual events take precedence, dedupe by (event, event_date)
    merged = {}
    for e in auto:
        merged[(e["event"], e["event_date"])] = e
    for e in events:
        merged[(e["event"], e["event_date"])] = e
    all_events = sorted(merged.values(), key=lambda e: e["event_date"], reverse=True)

    by_category = {}
    for e in all_events:
        by_category.setdefault(e["category"], []).append(e)

    lines = []
    for cat in ("career", "learning", "project", "skill", "milestone", "personal"):
        if by_category.get(cat):
            lines.append(f"{cat.capitalize()}: " + "; ".join(
                f"{e['event']} ({e['event_date']})" for e in by_category[cat][:5]))

    if not all_events:
        return {"since": since, "until": until, "events": [],
                "summary": f"Nothing notable in this period ({since} → {until}).",
                "by_category": {}}

    total = len(all_events)
    summary = (f"In this period ({since} → {until}) there were {total} events. "
               + " ".join(lines[:4]))
    return {"since": since, "until": until, "events": all_events,
            "summary": summary, "by_category": by_category}


def period_for_query(query: str) -> tuple:
    """Map a natural query to (since, until) ISO dates.

    Supports: 'last month', 'this year', 'last week', 'this month',
    'last 30 days', 'this year' (default: last 30 days).
    """
    q = (query or "").lower()
    today = date.today()
    if "year" in q:
        return today.replace(month=1, day=1).isoformat(), today.isoformat()
    if "last month" in q:
        first = today.replace(day=1) - timedelta(days=1)
        return first.replace(day=1).isoformat(), today.isoformat()
    if "this month" in q:
        return today.replace(day=1).isoformat(), today.isoformat()
    if "last week" in q:
        return (today - timedelta(days=7)).isoformat(), today.isoformat()
    if "week" in q:
        monday = today - timedelta(days=today.weekday())
        return monday.isoformat(), today.isoformat()
    # default: last 30 days
    return (today - timedelta(days=30)).isoformat(), today.isoformat()
