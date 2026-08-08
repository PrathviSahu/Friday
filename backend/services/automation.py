"""automation.py — Automation Engine (v3.1).

Persisted scheduled workflows ("every morning: briefing", "check jobs every
12 hours") with a lifespan-managed background runner. Actions push results
into the Notification Center instead of interrupting.

Actions implemented now:
  briefing        — generate the smart daily briefing → notification
  job_scan        — scan tracked jobs; notify when high-match / high-salary
  market_summary  — summarize watchlist prices → notification
"""

import json
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "friday_brain.db"
_lock = threading.RLock()
_stop_event = threading.Event()
_runner_thread: list = []


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_automations_db():
    with _lock, _connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS automations (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT NOT NULL,
            trigger_type     TEXT NOT NULL,     -- 'interval' | 'daily'
            interval_seconds INTEGER DEFAULT 0, -- for trigger_type=interval
            daily_time       TEXT DEFAULT '',   -- 'HH:MM' for trigger_type=daily
            action           TEXT NOT NULL,     -- briefing | job_scan | market_summary
            params           TEXT DEFAULT '{}',
            enabled          INTEGER DEFAULT 1,
            last_run         REAL DEFAULT 0,
            next_run         REAL DEFAULT 0,
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()


init_automations_db()


# ═══════════════════════════════════════════════════════════════════════════════
# CRUD
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_next_run(a: dict) -> float:
    now = time.time()
    if a["trigger_type"] == "interval":
        interval = max(60, int(a.get("interval_seconds") or 0))
        last = a.get("last_run") or 0
        return max(now, last + interval)
    # daily at HH:MM
    hm = (a.get("daily_time") or "09:00").split(":")
    try:
        target = datetime.now().replace(hour=int(hm[0]), minute=int(hm[1]),
                                        second=0, microsecond=0)
    except (ValueError, IndexError):
        target = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    ts = target.timestamp()
    if ts <= now:
        ts += 86400
    return ts


def list_automations() -> list:
    with _lock, _connect() as conn:
        rows = conn.execute("SELECT * FROM automations ORDER BY id").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["next_run"] = _compute_next_run(d)
        result.append(d)
    return result


def create_automation(name: str, trigger_type: str, action: str,
                      interval_seconds: int = 0, daily_time: str = "",
                      params: dict = None, enabled: bool = True) -> int:
    if action not in ("briefing", "job_scan", "market_summary", "learning_check"):
        raise ValueError(f"Unknown automation action: {action}")
    if trigger_type not in ("interval", "daily"):
        raise ValueError(f"Unknown trigger type: {trigger_type}")
    if trigger_type == "interval" and interval_seconds < 60:
        raise ValueError("interval_seconds must be >= 60")
    if trigger_type == "daily" and not daily_time:
        raise ValueError("daily_time required for daily automations")
    params_json = json.dumps(params or {})
    with _lock, _connect() as conn:
        cur = conn.execute("""
        INSERT INTO automations (name, trigger_type, interval_seconds, daily_time,
                                 action, params, enabled)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, trigger_type, interval_seconds, daily_time, action,
              params_json, int(enabled)))
        conn.commit()
        return cur.lastrowid


def update_automation(aid: int, **fields) -> bool:
    allowed = {"name", "trigger_type", "interval_seconds", "daily_time",
               "action", "params", "enabled"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    if "params" in updates and isinstance(updates["params"], dict):
        updates["params"] = json.dumps(updates["params"])
    with _lock, _connect() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        cur = conn.execute(
            f"UPDATE automations SET {set_clause} WHERE id = ?",
            list(updates.values()) + [aid],
        )
        conn.commit()
        return cur.rowcount > 0


def delete_automation(aid: int) -> bool:
    with _lock, _connect() as conn:
        cur = conn.execute("DELETE FROM automations WHERE id = ?", (aid,))
        conn.commit()
        return cur.rowcount > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Actions
# ═══════════════════════════════════════════════════════════════════════════════

def run_action(action: str, params: dict = None) -> str:
    """Execute one automation action; returns a short human-readable summary."""
    params = params or {}
    from services.notifications import push_notification

    if action == "briefing":
        from services.briefing import generate_daily_briefing
        b = generate_daily_briefing()
        top = "; ".join(
            f"{s['title']}: {' | '.join(s['lines'][:2])}" for s in b["sections"][:3]
        )
        push_notification("Daily Briefing", top[:2000], "briefing")
        return b["spoken_summary"]

    if action == "job_scan":
        from services.career_db import get_jobs
        min_score = int(params.get("min_score", 80))
        min_salary = float(params.get("min_salary", 0) or 0)
        jobs = get_jobs(min_score=min_score) or []
        hits = []
        for job in jobs[:20]:
            salary_raw = (job.get("salary_raw") or "").lower()
            if min_salary and "₹" in (job.get("salary_raw") or "") and "lpa" in salary_raw:
                try:
                    low = float(salary_raw.replace("₹", "").split("-")[0].replace(",", "").strip() or 0)
                    if low < min_salary:
                        continue
                except (ValueError, IndexError):
                    pass
            hits.append(f"{job.get('title')} @ {job.get('company')} ({job.get('match_score', 0)}%)")
        if hits:
            push_notification("Job Scan", " | ".join(hits[:5])[:2000], "career")
            return f"Found {len(hits)} high-match jobs."
        return "No new high-match jobs found."

    if action == "market_summary":
        from services.market_data import fetch_live_market_prices
        prices = fetch_live_market_prices() or {}
        picks = []
        for key in ("FX:EURUSD", "OANDA:XAUUSD", "OANDA:NAS100USD", "BINANCE:BTCUSDT"):
            item = prices.get(key)
            if item:
                picks.append(f"{item.get('name', key)} {item.get('price', '—')} ({item.get('changePct', '—')})")
        summary = " | ".join(picks) if picks else "Market feed unavailable."
        push_notification("Market Summary", summary[:2000], "market")
        return summary

    if action == "learning_check":
        from services.learning import check_streak
        return check_streak()

    if action == "consolidate_memory":
        # Phase 2.2 — nightly memory distillation (cron 03:30 local).
        from services.memory_consolidator import run as consolidate_run
        return consolidate_run()["report"]

    return f"Unknown action: {action}"


# ═══════════════════════════════════════════════════════════════════════════════
# Background runner (lifespan-managed)
# ═══════════════════════════════════════════════════════════════════════════════

def _runner_loop():
    while not _stop_event.is_set():
        try:
            now = time.time()
            for a in list_automations():
                if not a["enabled"]:
                    continue
                next_run = a["next_run"]
                if next_run <= now:
                    try:
                        run_action(a["action"], json.loads(a.get("params") or "{}"))
                        print(f"[Automation] ran '{a['name']}' ({a['action']})")
                    except Exception as err:
                        print(f"[Automation] '{a['name']}' failed: {err}")
                    with _lock, _connect() as conn:
                        conn.execute(
                            "UPDATE automations SET last_run = ?, next_run = ? WHERE id = ?",
                            (now, _compute_next_run(a), a["id"]),
                        )
                        conn.commit()
        except Exception as err:
            print(f"[Automation] runner error: {err}")
        _stop_event.wait(30)


def start_automation_runner() -> None:
    global _runner_thread
    if _runner_thread:
        return
    _stop_event.clear()
    t = threading.Thread(target=_runner_loop, daemon=True, name="automation-runner")
    t.start()
    _runner_thread = [t]
    print("[Automation] Background automation runner started.")


def stop_automation_runner() -> None:
    global _runner_thread
    _stop_event.set()
    _runner_thread = []
