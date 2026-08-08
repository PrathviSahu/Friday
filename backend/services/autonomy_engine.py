"""autonomy_engine.py — Autonomy & Trust Engine (Phase 2.1).

Graduates proven habits from "Shall I…?" to guarded autonomous execution,
per next_phase_2_architecture.md §2.

Design rules (never violated):
  * Trust is layered UNDER the Permission Center — an autonomous run still
    passes check_permission(); trust never self-authorizes a disabled or
    unapproved 'ask' capability.
  * External-communication / irreversible tools are capped at 'confirm'
    tier forever (approval-first doctrine, Phase 1 → v4).
  * decide() is pure (no writes) so it is unit-testable in isolation.
  * Every autonomous act is journaled in autonomy_journal and undoable
    within UNDO_WINDOW_SECONDS where an undo payload exists.
  * Anti-annoyance invariants: budget ≤ 4 autonomous actions/hour/class,
    quiet hours 22:00–07:00 force 'confirm', meeting-shield/focus (Phase
    2.3 context engine, when present) forces 'confirm'.

Trust model:
    T(a) = (A + 1) / (A + R + 2) × e^(-λ·Δt)      λ = 0.10/day
    tier: silent  if T ≥ 0.85 ∧ N ≥ 10 ∧ reversible
          announce if 0.60 ≤ T ∧ N ≥ 3
          confirm  otherwise
    Hysteresis: a 'silent' action keeps its tier until T < 0.82.

Tables (unified friday_brain.db):
  action_trust      — per-action Bayesian ledger (accepts/rejects/tier)
  autonomy_journal  — audit + undo log of every autonomous execution
"""

import json
import math
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "friday_brain.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_lock = threading.RLock()

# ── Trust model constants (next_phase_2_architecture.md §2-B) ─────────────────

TRUST_DECAY_LAMBDA = 0.10         # per day — 2× faster than habit memory (0.05)
SILENT_THRESHOLD = 0.85           # gain 'silent' at/above this trust...
SILENT_LOSE_THRESHOLD = 0.82      # ...lose it only below this (0.03 hysteresis band)
ANNOUNCE_THRESHOLD = 0.60
MIN_EXECUTIONS_SILENT = 10        # sample-size gates, hard
MIN_EXECUTIONS_ANNOUNCE = 3
NEW_ACTION_PRIOR = 0.50           # Laplace prior for unseen actions

# ── Anti-annoyance invariants ─────────────────────────────────────────────────

AUTONOMY_BUDGET_PER_CLASS = 4     # autonomous executions / hour / action class
QUIET_HOUR_START = 22             # 22:00 local...
QUIET_HOUR_END = 7                # ...through 07:00 local → confirm only
UNDO_WINDOW_SECONDS = 300         # undo allowed within 5 minutes

# Tools with real-world consequences — capped at 'confirm' tier forever.
EXTERNAL_COMM_TOOLS = {
    "send_email", "send_whatsapp", "send_whatsapp_desktop", "create_calendar_event",
}

# Tool → Permission Center capability checked before ANY autonomous execution.
TOOL_CAPABILITY = {
    "send_email": "email.send",
    "send_whatsapp": "whatsapp.send",
    "send_whatsapp_desktop": "whatsapp.send",
    "create_calendar_event": "calendar.write",
    "take_screenshot": "screen.capture",
}

# Compensating Tool Router calls for reversible actions: tool → undo tool (+params).
UNDO_MAP = {
    "open_trading": ("close_trading", {}),
    "play_spotify": ("control_spotify", {"command": "pause"}),
}

# Coarse action classes for the autonomy budget.
_ACTION_CLASSES = {
    "play_spotify": "media", "control_spotify": "media",
    "open_spotify": "media", "play_music": "media", "play_hindi_playlist": "media",
    "play_english_playlist": "media",
    "open_trading": "trading", "trading": "trading", "trading_station": "trading",
    "get_weather": "info", "weather": "info", "web_search": "info", "search_web": "info",
    "open_app": "system", "navigate_to": "system", "system_control": "system",
    "engineering": "system", "vscode": "system", "job_search": "system",
}


def _now() -> datetime:
    """Single clock for the whole module — monkeypatched by tests."""
    return datetime.now()


# ── Database ──────────────────────────────────────────────────────────────────

def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_autonomy_db() -> None:
    """Create trust ledger + journal tables (unified friday_brain.db)."""
    with _db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS action_trust (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type     TEXT NOT NULL UNIQUE,
            accepts         INTEGER DEFAULT 0,
            rejects         INTEGER DEFAULT 0,       -- rejections (undo adds +2)
            tier            TEXT DEFAULT 'confirm',  -- 'silent' | 'announce' | 'confirm'
            last_acted_at   TIMESTAMP,
            last_undo_at    TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS autonomy_journal (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type     TEXT NOT NULL,
            tool_name       TEXT,
            tier            TEXT NOT NULL,           -- tier at time of execution
            params_json     TEXT,
            result_summary  TEXT,
            undo_payload    TEXT,                    -- {"tool": ..., "params": {...}} | NULL
            outcome         TEXT,                    -- NULL pending | auto_accepted | undone | failed
            undone          INTEGER DEFAULT 0,
            executed_at     TIMESTAMP NOT NULL
        )""")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_journal_time ON autonomy_journal(executed_at)")
        conn.commit()


init_autonomy_db()


# ── Pure trust math ───────────────────────────────────────────────────────────

def compute_trust(accepts: int, rejects: int, last_acted_at: datetime | None,
                  now: datetime | None = None) -> float:
    """Bayesian trust score with exponential decay — pure function."""
    now = now or _now()
    base = (accepts + 1) / (accepts + rejects + 2)          # Laplace prior 0.50
    if not last_acted_at:
        return base                                          # nothing acted on yet
    days = max(0.0, (now - last_acted_at).total_seconds() / 86400.0)
    return base * math.exp(-TRUST_DECAY_LAMBDA * days)


def assign_tier(trust: float, executions: int, reversible: bool,
                current_tier: str = "confirm") -> str:
    """Map trust → tier with the 0.03 hysteresis band at the silent boundary.

    An action GAINS 'silent' only at T ≥ 0.85 but KEEPS it until T < 0.82 —
    prevents tier flapping around the boundary.
    """
    if trust >= SILENT_THRESHOLD and executions >= MIN_EXECUTIONS_SILENT and reversible:
        return "silent"
    if current_tier == "silent" and trust >= SILENT_LOSE_THRESHOLD \
            and executions >= MIN_EXECUTIONS_SILENT and reversible:
        return "silent"                                      # hysteresis hold
    if trust >= ANNOUNCE_THRESHOLD and executions >= MIN_EXECUTIONS_ANNOUNCE:
        return "announce"
    return "confirm"


# ── Ledger helpers ────────────────────────────────────────────────────────────

def _get_trust_row(conn, action_type: str):
    return conn.execute(
        "SELECT * FROM action_trust WHERE action_type = ?", (action_type,)
    ).fetchone()


def _parse_ts(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _execution_count(conn, action_type: str) -> int:
    """N(a): habit frequency (via learning_engine's own store) + journal runs."""
    try:
        from services import learning_engine
        habits = learning_engine.get_action_frequency(action_type)
    except Exception:
        habits = 0  # habit memory unavailable → journal count alone (safe: lower N)
    try:
        journal = conn.execute(
            "SELECT COUNT(*) AS n FROM autonomy_journal "
            "WHERE action_type = ? AND (outcome IS NULL OR outcome != 'failed')",
            (action_type,)).fetchone()["n"]
    except sqlite3.OperationalError:
        journal = 0
    return int(habits or 0) + int(journal or 0)


def _action_class(action_type: str, tool_name: str | None = None) -> str:
    return _ACTION_CLASSES.get(action_type) or _ACTION_CLASSES.get(tool_name or "") or "general"


def _budget_used(conn, action_class: str, now: datetime) -> int:
    since = (now - timedelta(hours=1)).isoformat(timespec="seconds")
    count = 0
    for row in conn.execute(
            "SELECT action_type, tool_name FROM autonomy_journal WHERE executed_at >= ?",
            (since,)).fetchall():
        if _action_class(row["action_type"], row["tool_name"]) == action_class:
            count += 1
    return count


def _blocked_by_context() -> str | None:
    """Meeting shield / focus mode — consults Phase 2.3 context engine when present."""
    try:
        from services import context_engine  # type: ignore
        vec = context_engine.get_context()
        if vec.get("meeting_now"):
            return "meeting_in_progress"
        if vec.get("focus_mode"):
            return "focus_mode"
    except ImportError:
        pass
    except Exception:
        pass  # a broken context engine never blocks a decision
    return None


# ── Decision ──────────────────────────────────────────────────────────────────

def decide(action_type: str, tool_name: str | None = None,
           capability: str | None = None, now: datetime | None = None) -> dict:
    """Pure decision (no writes): what tier may `action_type` run at right now?

    Returns {'action_type', 'tier', 'trust', 'executions', 'blocked_reason'}.
    blocked_reason is NULL when the returned tier is organically earned; when
    an invariant forces 'confirm', the reason is reported instead.
    """
    now = now or _now()
    tool_name = tool_name or action_type

    # 1. Quiet hours — hard floor, no trust overrides bedtime.
    if now.hour >= QUIET_HOUR_START or now.hour < QUIET_HOUR_END:
        return _decision(action_type, "confirm", 0.0, 0, "quiet_hours")

    # 2. Meeting shield / focus mode (Phase 2.3 context engine, when shipped).
    ctx_block = _blocked_by_context()
    if ctx_block:
        return _decision(action_type, "confirm", 0.0, 0, ctx_block)

    # 3. External-communication tools are capped at confirm forever — checked
    #    before permissions so the reason is deterministic regardless of policy.
    if tool_name in EXTERNAL_COMM_TOOLS:
        return _decision(action_type, "confirm", 0.0, 0, "external_comm")

    # 4. Permission Center — trust never overrides policy.
    cap = capability or TOOL_CAPABILITY.get(tool_name)
    if cap:
        from services import permissions
        verdict = permissions.check_permission(cap)
        if verdict == "denied":
            return _decision(action_type, "confirm", 0.0, 0, "permission_denied")
        if verdict == "approval_required":
            # Autonomy may NOT consume interactive 'ask' approvals silently.
            return _decision(action_type, "confirm", 0.0, 0, "permission_approval")

    # 5. Autonomy budget: ≤ 4 autonomous executions/hour/class.
    action_class = _action_class(action_type, tool_name)
    with _db() as conn:
        used = _budget_used(conn, action_class, now)
        if used >= AUTONOMY_BUDGET_PER_CLASS:
            return _decision(action_type, "confirm", 0.0, 0, "budget_exhausted")

        # 6. Organic trust tier.
        row = _get_trust_row(conn, action_type)
        accepts = row["accepts"] if row else 0
        rejects = row["rejects"] if row else 0
        last_acted = _parse_ts(row["last_acted_at"]) if row else None
        current_tier = row["tier"] if row and row["tier"] else "confirm"
        executions = _execution_count(conn, action_type)

    trust = compute_trust(accepts, rejects, last_acted, now)
    reversible = tool_name in UNDO_MAP
    tier = assign_tier(trust, executions, reversible, current_tier)
    return _decision(action_type, tier, round(trust, 4), executions, None)


def _decision(action_type: str, tier: str, trust: float, executions: int,
              blocked: str | None) -> dict:
    return {"action_type": action_type, "tier": tier, "trust": trust,
            "executions": executions, "blocked_reason": blocked}


# ── Execution ─────────────────────────────────────────────────────────────────

def _dispatch_tool(name: str, params: dict) -> str:
    """Tool Router dispatch wrapper (monkeypatched in tests — never the GUI)."""
    from services.function_engine import dispatch
    return dispatch(name, params)


def run(action_type: str, tool_name: str, params: dict | None = None,
        capability: str | None = None) -> dict:
    """Attempt an autonomous execution. 'confirm' → suggestion, never a silent run."""
    now = _now()
    finalize_outcomes(now)                                  # lazy sweep first
    d = decide(action_type, tool_name, capability, now)

    if d["tier"] == "confirm":
        return {"executed": False, "decision": d,
                "suggestion": f"Prem, shall I {action_type.replace('_', ' ')}?"}

    params = params or {}
    result = _dispatch_tool(tool_name, params)
    failed = result.startswith("I hit a problem")
    timestamp = now.isoformat(timespec="seconds")

    journal_id = None
    undo = UNDO_MAP.get(tool_name)
    undo_payload = json.dumps({"tool": undo[0], "params": undo[1]}) if undo else None
    with _lock, _db() as conn:
        cur = conn.execute("""
        INSERT INTO autonomy_journal
            (action_type, tool_name, tier, params_json, result_summary,
             undo_payload, outcome, executed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (action_type, tool_name, d["tier"], json.dumps(params),
              result[:200], None if failed else undo_payload,
              "failed" if failed else None, timestamp))
        journal_id = cur.lastrowid
        if not failed:
            _touch_trust_row(conn, action_type, now)
        conn.commit()

    return {"executed": not failed, "journal_id": journal_id,
            "result": result, "announce": d["tier"] == "announce",
            "decision": d,
            "undo_available": (not failed) and tool_name in UNDO_MAP}


def _touch_trust_row(conn, action_type: str, now: datetime) -> None:
    """Ensure a ledger row exists and stamp last_acted_at (decay anchor)."""
    conn.execute("""
    INSERT INTO action_trust (action_type, accepts, rejects, tier, last_acted_at, updated_at)
    VALUES (?, 0, 0, 'confirm', ?, ?)
    ON CONFLICT(action_type) DO UPDATE SET
        last_acted_at = excluded.last_acted_at,
        updated_at = excluded.updated_at
    """, (action_type, now.isoformat(timespec="seconds"), now.isoformat(timespec="seconds")))


# ── Outcomes & trust updates ──────────────────────────────────────────────────

def record_outcome(action_type: str, outcome: str, now: datetime | None = None) -> dict:
    """Apply an outcome and recompute the stored tier.

    outcome: 'accepted' (A+1) | 'rejected' (R+1) | 'undone' (R+2 + last_undo_at)
    """
    now = now or _now()
    if outcome not in {"accepted", "rejected", "undone"}:
        return {"status": "error", "message": f"unknown outcome '{outcome}'"}

    with _lock, _db() as conn:
        _touch_trust_row(conn, action_type, now)
        if outcome == "accepted":
            conn.execute(
                "UPDATE action_trust SET accepts = accepts + 1 WHERE action_type = ?",
                (action_type,))
        elif outcome == "rejected":
            conn.execute(
                "UPDATE action_trust SET rejects = rejects + 1 WHERE action_type = ?",
                (action_type,))
        else:  # undone — strong negative signal: R+2 and stamp the undo
            conn.execute(
                "UPDATE action_trust SET rejects = rejects + 2, last_undo_at = ? "
                "WHERE action_type = ?",
                (now.isoformat(timespec="seconds"), action_type))

        row = _get_trust_row(conn, action_type)
        executions = _execution_count(conn, action_type)
        trust = compute_trust(row["accepts"], row["rejects"],
                              _parse_ts(row["last_acted_at"]), now)
        # Reversibility is unknown at the ledger level; tier holds broadest the
        # numbers allow and decide() re-caps per tool at run time.
        tier = assign_tier(trust, executions, reversible=True,
                           current_tier=row["tier"])
        conn.execute(
            "UPDATE action_trust SET tier = ?, updated_at = ? WHERE action_type = ?",
            (tier, now.isoformat(timespec="seconds"), action_type))
        conn.commit()

    # An accepted suggestion IS execution evidence — feed habit memory even
    # for actions outside learning_engine's curated high-value allowlist.
    if outcome == "accepted":
        try:
            from services import learning_engine
            learning_engine.log_user_action(action_type, force=True)
        except Exception:
            pass

    return {"status": "ok", "action_type": action_type,
            "trust": round(trust, 4), "tier": tier}


def finalize_outcomes(now: datetime | None = None) -> int:
    """Lazy sweep: silent executions older than the undo window with no undo
    count as implicit acceptances (A+1 each). No background threads needed —
    called at the top of run() and from the scheduled automation runner."""
    now = now or _now()
    cutoff = (now - timedelta(seconds=UNDO_WINDOW_SECONDS)).isoformat(timespec="seconds")
    finalized = 0
    with _lock, _db() as conn:
        rows = conn.execute("""
        SELECT id, action_type FROM autonomy_journal
        WHERE outcome IS NULL AND undone = 0 AND executed_at < ?
        """, (cutoff,)).fetchall()
        for row in rows:
            conn.execute(
                "UPDATE autonomy_journal SET outcome = 'auto_accepted' WHERE id = ?",
                (row["id"],))
            finalized += 1
        conn.commit()
    for row in rows:  # trust updates outside the batch loop (each re-reads state)
        record_outcome(row["action_type"], "accepted", now)
    return finalized


# ── Undo / revoke ─────────────────────────────────────────────────────────────

def undo(journal_id: int, now: datetime | None = None) -> dict:
    """Undo a journaled execution inside the 300-second window."""
    now = now or _now()
    with _lock, _db() as conn:
        row = conn.execute(
            "SELECT * FROM autonomy_journal WHERE id = ?", (journal_id,)).fetchone()
        if not row:
            return {"status": "error", "message": "journal entry not found"}
        if row["undone"]:
            return {"status": "error", "message": "already undone"}
        if not row["undo_payload"]:
            return {"status": "error", "message": "action is not reversible"}
        executed_at = _parse_ts(row["executed_at"])
        if executed_at and (now - executed_at).total_seconds() > UNDO_WINDOW_SECONDS:
            return {"status": "error", "message": "undo window expired (300s)"}

        payload = json.loads(row["undo_payload"])

    result = _dispatch_tool(payload["tool"], payload.get("params") or {})

    with _lock, _db() as conn:
        conn.execute(
            "UPDATE autonomy_journal SET undone = 1, outcome = 'undone' WHERE id = ?",
            (journal_id,))
        conn.commit()
    trust = record_outcome(row["action_type"], "undone", now)   # R+2, strong signal
    return {"status": "ok", "undone": True, "undo_result": result, "trust": trust}


def revoke(action_type: str) -> dict:
    """Owner one-tap revoke: reset the ledger, force 'confirm' to re-earn trust."""
    with _lock, _db() as conn:
        conn.execute("""
        INSERT INTO action_trust (action_type, accepts, rejects, tier, updated_at)
        VALUES (?, 0, 0, 'confirm', CURRENT_TIMESTAMP)
        ON CONFLICT(action_type) DO UPDATE SET
            accepts = 0, rejects = 0, tier = 'confirm',
            updated_at = CURRENT_TIMESTAMP
        """, (action_type,))
        conn.commit()
    return {"status": "ok", "action_type": action_type, "tier": "confirm"}


# ── Reporting (HUD Autonomy Panel) ───────────────────────────────────────────

def get_status(now: datetime | None = None) -> dict:
    """Per-action trust ledger + budget, for the HUD Autonomy panel."""
    now = now or _now()
    actions = []
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM action_trust ORDER BY updated_at DESC").fetchall()
        for row in rows:
            trust = compute_trust(row["accepts"], row["rejects"],
                                  _parse_ts(row["last_acted_at"]), now)
            actions.append({
                "action_type": row["action_type"],
                "accepts": row["accepts"], "rejects": row["rejects"],
                "trust": round(trust, 4), "tier": row["tier"],
                "last_undo_at": row["last_undo_at"],
            })
        classes = {}
        for cls in {*_ACTION_CLASSES.values(), "general"}:
            used = _budget_used(conn, cls, now)
            classes[cls] = max(0, AUTONOMY_BUDGET_PER_CLASS - used)
    return {"actions": actions, "budget": classes,
            "budget_remaining": min(classes.values()) if classes else AUTONOMY_BUDGET_PER_CLASS}


def get_journal(date: str | None = None, limit: int = 100) -> list:
    """Journal entries for a date (YYYY-MM-DD); defaults to today, local time."""
    date = date or _now().date().isoformat()
    with _db() as conn:
        rows = conn.execute("""
        SELECT id, action_type, tool_name, tier, result_summary,
               undo_payload, outcome, undone, executed_at
        FROM autonomy_journal
        WHERE executed_at LIKE ?
        ORDER BY id DESC LIMIT ?
        """, (f"{date}%", limit)).fetchall()
    return [dict(r) for r in rows]
