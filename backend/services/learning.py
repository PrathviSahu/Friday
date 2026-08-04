"""learning.py — Personal Learning Coach (v3.2).

Tracks practice sessions across learning tracks (DSA, Java roadmap, System
Design, AWS, interview prep), computes daily/weekly streaks, and pushes
gentle notifications when the streak is at risk ("Boss, you haven't solved a
DSA problem in 3 days").

Backed by the `learning_goals` and `learning_log` tables in friday_brain.db.
"""

import sqlite3
import threading
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "friday_brain.db"
_lock = threading.RLock()

# Seed tracks so the coach is useful out of the box
DEFAULT_GOALS = [
    {"title": "DSA Practice",       "category": "dsa",           "target_per_week": 5},
    {"title": "Java Roadmap",       "category": "java",          "target_per_week": 3},
    {"title": "System Design",      "category": "system_design", "target_per_week": 2},
    {"title": "AWS Learning",       "category": "aws",           "target_per_week": 2},
    {"title": "Interview Prep",     "category": "interview_prep","target_per_week": 2},
]

CATEGORY_LABELS = {
    "dsa": "DSA", "java": "Java", "system_design": "System Design",
    "aws": "AWS", "interview_prep": "Interview Prep", "general": "General",
}


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_learning_db():
    with _lock, _connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_goals (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT NOT NULL,
            category        TEXT NOT NULL,
            target_per_week INTEGER DEFAULT 3
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            title      TEXT NOT NULL,
            category   TEXT DEFAULT 'general',
            minutes    INTEGER DEFAULT 30,
            solved     INTEGER DEFAULT 0,
            log_date   TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        # Seed defaults ONLY when the table is empty (no UNIQUE constraint on
        # title, so INSERT OR IGNORE would duplicate on every process start).
        count = conn.execute("SELECT COUNT(*) AS c FROM learning_goals").fetchone()["c"]
        if count == 0:
            for g in DEFAULT_GOALS:
                conn.execute(
                    "INSERT INTO learning_goals (title, category, target_per_week) "
                    "VALUES (?, ?, ?)", (g["title"], g["category"], g["target_per_week"]))
        conn.commit()


init_learning_db()


# ═══════════════════════════════════════════════════════════════════════════════
# Logging sessions
# ═══════════════════════════════════════════════════════════════════════════════

def log_session(title: str, category: str = "general", minutes: int = 30,
                solved: int = 0, log_date: str = None) -> int:
    """Record a learning session. `log_date` defaults to today (ISO format)."""
    title = (title or "Practice session").strip()
    if category not in CATEGORY_LABELS:
        category = "general"
    d = log_date or date.today().isoformat()
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO learning_log (title, category, minutes, solved, log_date) "
            "VALUES (?, ?, ?, ?, ?)", (title, category, int(minutes), int(solved), d))
        conn.commit()
        return cur.lastrowid


def _streak_data():
    """Return (current_streak, best_streak, last_log_date_str_or_None)."""
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT log_date FROM learning_log ORDER BY log_date"
        ).fetchall()
    dset = set()
    for r in rows:
        try:
            dset.add(date.fromisoformat(r["log_date"]))
        except ValueError:
            continue
    if not dset:
        return 0, 0, None

    today = date.today()
    cursor = today if today in dset else today - timedelta(days=1)
    current = 0
    while cursor in dset:
        current += 1
        cursor -= timedelta(days=1)

    best, run, prev = 0, 0, None
    for d in sorted(dset):
        if prev is None or (d - prev).days == 1:
            run += 1
        else:
            run = 1
        best = max(best, run)
        prev = d

    return current, best, max(dset).isoformat()


def get_dashboard() -> dict:
    """Full coach dashboard: streak, today, weekly goals, recent sessions."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    today_iso, monday_iso = today.isoformat(), monday.isoformat()

    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT title, category, minutes, solved, log_date FROM learning_log "
            "ORDER BY log_date DESC, id DESC LIMIT 200").fetchall()
        goals = conn.execute("SELECT * FROM learning_goals").fetchall()

    sessions = [dict(r) for r in rows]
    today_sessions = [s for s in sessions if s["log_date"] == today_iso]
    week_sessions = [s for s in sessions if s["log_date"] >= monday_iso]
    current, best, last = _streak_data()

    # Weekly goal progress per track
    weekly = []
    for g in goals:
        gd = dict(g)
        done = sum(1 for s in week_sessions if s["category"] == gd["category"])
        weekly.append({
            "title": gd["title"],
            "category": gd["category"],
            "label": CATEGORY_LABELS.get(gd["category"], gd["category"]),
            "target": gd["target_per_week"],
            "done": done,
            "pct": min(100, round(done / max(1, gd["target_per_week"]) * 100)),
        })

    # Last 7 days activity (for the mini bar chart)
    last7 = []
    for i in range(6, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        last7.append({
            "date": d,
            "count": sum(1 for s in sessions if s["log_date"] == d),
            "minutes": sum(s["minutes"] for s in sessions if s["log_date"] == d),
        })

    return {
        "streak": current,
        "best_streak": best,
        "last_activity_date": last,
        "today_sessions": len(today_sessions),
        "today_minutes": sum(s["minutes"] for s in today_sessions),
        "today_solved": sum(s["solved"] for s in today_sessions),
        "week_minutes": sum(s["minutes"] for s in week_sessions),
        "weekly_goals": weekly,
        "last7": last7,
        "recent": sessions[:5],
    }


def check_streak() -> str:
    """Coach check used by the automation runner. Notifies when idle ≥ 3 days."""
    from services.notifications import push_notification

    current, best, last = _streak_data()
    if last is None:
        return "No learning sessions logged yet — start one today, Boss!"
    days_since = (date.today() - date.fromisoformat(last)).days
    if days_since >= 3:
        msg = (f"Boss, you haven't practiced in {days_since} days. "
               f"Your streak was {current} day(s) — one session today keeps it alive.")
        push_notification("Learning Coach", msg, "learning")
        return msg
    if days_since == 1:
        return (f"You practiced yesterday — streak at {current} day(s). "
                "One session today keeps it going.")
    return f"Streak alive at {current} day(s) (best {best}). Last session: {last}."
