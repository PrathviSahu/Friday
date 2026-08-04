"""goals.py — Goal Manager (v3.3).

Set goals like "Get an 8 LPA job" and track:
  tasks → progress → deadlines → skill gaps → resources

Goals can optionally link to the career profile: category 'career' goals
suggest missing skills from your job match data.
"""

import json
import sqlite3
import threading
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "friday_brain.db"
_lock = threading.RLock()

GOAL_CATEGORIES = ("career", "learning", "skill", "project", "health", "personal")


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_goals_db():
    with _lock, _connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT NOT NULL,
            category     TEXT NOT NULL DEFAULT 'personal',
            target_value REAL DEFAULT 100,
            current_value REAL DEFAULT 0,
            unit         TEXT DEFAULT '%',
            deadline     TEXT DEFAULT '',
            status       TEXT DEFAULT 'active',   -- active | done | paused
            skill_gaps   TEXT DEFAULT '[]',
            resources    TEXT DEFAULT '[]',
            notes        TEXT DEFAULT '',
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()


init_goals_db()


def _pct(current, target) -> int:
    try:
        return int(round(min(100.0, max(0.0, current / max(1, target)) * 100)))
    except Exception:
        return 0


def create_goal(title: str, category: str = "personal", target_value: float = 100,
                unit: str = "%", deadline: str = "", skill_gaps: list = None,
                resources: list = None) -> int:
    title = (title or "").strip()
    if not title:
        raise ValueError("title is required")
    if category not in GOAL_CATEGORIES:
        category = "personal"
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO goals (title, category, target_value, unit, deadline, "
            "skill_gaps, resources) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, category, float(target_value or 0), unit or "%", deadline or "",
             json.dumps(skill_gaps or []), json.dumps(resources or [])))
        conn.commit()
        return cur.lastrowid


def list_goals(status: str = None) -> list:
    q = "SELECT * FROM goals"
    params = []
    if status:
        q += " WHERE status = ?"
        params.append(status)
    q += " ORDER BY id DESC"
    with _lock, _connect() as conn:
        rows = conn.execute(q, params).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        for k in ("skill_gaps", "resources"):
            try:
                d[k] = json.loads(d.get(k) or "[]")
            except Exception:
                d[k] = []
        d["progress_pct"] = _pct(d["current_value"], d["target_value"])
        result.append(d)
    return result


def update_goal(goal_id: int, **fields) -> bool:
    allowed = {"title", "category", "target_value", "current_value", "unit",
               "deadline", "status", "skill_gaps", "resources", "notes"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    for k in ("skill_gaps", "resources"):
        if k in updates and isinstance(updates[k], list):
            updates[k] = json.dumps(updates[k])
    with _lock, _connect() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        cur = conn.execute(
            f"UPDATE goals SET {set_clause} WHERE id = ?",
            list(updates.values()) + [goal_id])
        conn.commit()
        return cur.rowcount > 0


def increment_goal(goal_id: int, amount: float = 1) -> dict | None:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if not row:
            return None
        new_val = float(row["current_value"]) + float(amount)
        status = "done" if new_val >= float(row["target_value"]) and row["status"] == "active" else row["status"]
        conn.execute(
            "UPDATE goals SET current_value = ?, status = ? WHERE id = ?",
            (new_val, status, goal_id))
        conn.commit()
        d = dict(row)
        d["current_value"] = new_val
        d["status"] = status
        return d


def delete_goal(goal_id: int) -> bool:
    with _lock, _connect() as conn:
        cur = conn.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
        conn.commit()
        return cur.rowcount > 0


def suggest_skill_gaps(category: str = None) -> list:
    """Suggest missing skills from job-match data for career goals."""
    if category and category != "career":
        return []
    try:
        from services.career_db import get_jobs
        jobs = get_jobs(min_score=60) or []
        from collections import Counter
        counter = Counter()
        for job in jobs:
            try:
                match = json.loads(job.get("match_json") or "{}")
            except Exception:
                match = {}
            for skill in match.get("missing_skills", [])[:5]:
                counter[skill] += 1
        return [s for s, _ in counter.most_common(5)]
    except Exception:
        return []
