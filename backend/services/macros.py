"""macros.py — Voice Macro & Workflow Composer (Phase 2.4).

User-defined multi-step routines chained from the Tool Router's registered
tools, per next_phase_2_architecture.md §4-D:

    "Friday, when I say 'start my morning', open my trading station,
     give me the weather, and play lofi."

  * CREATION  — via the `create_macro` tool (LLM function-calling parses the
    free-form sentence) or the HUD builder; every step's tool is validated
    against the live registry before save.
  * EXECUTION — an exact saved trigger phrase is matched at chat entry,
    BEFORE regex intents and before any LLM round-trip (0ms fast path —
    same doctrine as Phase 1's fast-path evaluator, layered above it for
    user-defined phrases). Steps dispatch sequentially; a failing step
    HALTS the chain and reports which step failed.
  * TRUST     — a macro inherits the MINIMUM autonomy tier of its steps:
    one 'confirm'-tier step makes the whole macro ask-first. Macros are
    first-class rows in action_trust ('macro:<trigger>'), so accepted
    runs grow trust exactly like single actions.
  * Per-step execution on the organic path goes through autonomy_engine.run
    → journaled and undoable individually. Forced runs (owner-approved from
    the HUD/API) dispatch directly — the owner's click IS the approval.

Tables (unified friday_brain.db): voice_macros, macro_runs.
"""

import json
import re
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "friday_brain.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_lock = threading.RLock()

MAX_STEPS = 8                     # keep voice routines legible
# Tools that must never appear inside a macro (recursion / policy bypass).
FORBIDDEN_STEP_TOOLS = {"create_macro", "delete_macro", "guest_permission"}
TIER_RANK = {"confirm": 0, "announce": 1, "silent": 2}


def _now() -> datetime:
    return datetime.now()


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_macros_db() -> None:
    with _db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS voice_macros (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            trigger_phrase  TEXT NOT NULL UNIQUE,
            steps_json      TEXT NOT NULL,       -- [{"tool": str, "params": {...}}]
            enabled         INTEGER DEFAULT 1,
            created_by      TEXT DEFAULT 'voice',
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS macro_runs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            macro_id        INTEGER NOT NULL REFERENCES voice_macros(id),
            steps_ok        INTEGER DEFAULT 0,
            steps_failed    INTEGER DEFAULT 0,
            ran_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()


init_macros_db()


class MacroError(ValueError):
    """Validation failure with a user-speakable message."""


# ── Normalization & validation ────────────────────────────────────────────────

def _normalize(phrase: str) -> str:
    """Exact-match normalization for the 0ms trigger fast path."""
    text = re.sub(r"[?.!,।]+$", "", (phrase or "").strip().lower())
    return " ".join(text.split())


def _validate_steps(steps: list) -> list:
    """Coerce + validate steps against the live tool registry. Raises MacroError."""
    from services.function_engine import _REGISTRY
    if not isinstance(steps, list) or not steps:
        raise MacroError("a macro needs at least one step")
    if len(steps) > MAX_STEPS:
        raise MacroError(f"a macro can have at most {MAX_STEPS} steps")
    clean = []
    for i, step in enumerate(steps, start=1):
        if isinstance(step, str):                      # tolerate LLM shorthand
            step = {"tool": step, "params": {}}
        tool = str((step or {}).get("tool", "")).strip()
        params = (step or {}).get("params") or {}
        if not tool:
            raise MacroError(f"step {i} is missing a tool name")
        if tool in FORBIDDEN_STEP_TOOLS:
            raise MacroError(f"step {i}: '{tool}' cannot be used inside a macro")
        if tool not in _REGISTRY:
            raise MacroError(f"step {i}: unknown tool '{tool}'")
        if not isinstance(params, dict):
            raise MacroError(f"step {i}: params must be an object")
        clean.append({"tool": tool, "params": params})
    return clean


# ── CRUD ─────────────────────────────────────────────────────────────────────

def create_macro(trigger: str, steps: list, created_by: str = "voice") -> dict:
    trigger_norm = _normalize(trigger)
    if len(trigger_norm) < 3:
        raise MacroError("trigger phrase is too short")
    clean = _validate_steps(steps)
    with _lock, _db() as conn:
        if conn.execute("SELECT 1 FROM voice_macros WHERE trigger_phrase = ?",
                        (trigger_norm,)).fetchone():
            raise MacroError(f"a macro called '{trigger_norm}' already exists")
        cur = conn.execute(
            "INSERT INTO voice_macros (trigger_phrase, steps_json, created_by)"
            " VALUES (?, ?, ?)", (trigger_norm, json.dumps(clean), created_by))
        conn.commit()
        macro_id = cur.lastrowid
    return {"status": "ok", "id": macro_id, "trigger_phrase": trigger_norm,
            "steps": clean, "created_by": created_by}


def delete_macro(macro_id: int | None = None, trigger: str | None = None) -> dict:
    with _lock, _db() as conn:
        if macro_id is None and trigger:
            row = conn.execute("SELECT id FROM voice_macros WHERE trigger_phrase = ?",
                               (_normalize(trigger),)).fetchone()
            macro_id = row["id"] if row else None
        if macro_id is None:
            return {"status": "error", "message": "missing macro id or trigger"}
        cur = conn.execute("DELETE FROM voice_macros WHERE id = ?", (macro_id,))
        deleted = cur.rowcount > 0
        if deleted:
            conn.execute("DELETE FROM macro_runs WHERE macro_id = ?", (macro_id,))
        conn.commit()
    return {"status": "ok" if deleted else "error",
            "message": None if deleted else "macro not found"}


def _row_to_macro(row, conn=None) -> dict:
    macro = {"id": row["id"], "trigger_phrase": row["trigger_phrase"],
             "steps": json.loads(row["steps_json"]), "enabled": bool(row["enabled"]),
             "created_by": row["created_by"], "created_at": row["created_at"]}
    if conn is not None:
        macro["recent_runs"] = [dict(r) for r in conn.execute(
            "SELECT steps_ok, steps_failed, ran_at FROM macro_runs "
            "WHERE macro_id = ? ORDER BY id DESC LIMIT 3", (row["id"],)).fetchall()]
    return macro


def list_macros() -> list:
    with _db() as conn:
        rows = conn.execute("SELECT * FROM voice_macros ORDER BY id DESC").fetchall()
        return [_row_to_macro(r, conn) for r in rows]


def get_macro(macro_id: int) -> dict | None:
    with _db() as conn:
        row = conn.execute("SELECT * FROM voice_macros WHERE id = ?", (macro_id,)).fetchone()
    return _row_to_macro(row) if row else None


def get_macro_by_trigger(text: str) -> dict | None:
    """Exact normalized match — the 0ms chat-entry fast path."""
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM voice_macros WHERE trigger_phrase = ? AND enabled = 1",
            (_normalize(text),)).fetchone()
    return _row_to_macro(row) if row else None


# ── Execution ─────────────────────────────────────────────────────────────────

def _dispatch(tool: str, params: dict) -> str:
    """Dispatch wrapper (monkeypatched in tests — never the real GUI/LLM)."""
    from services.function_engine import dispatch
    return dispatch(tool, params)


def _failed(reply: str) -> bool:
    return (reply or "").startswith("I hit a problem")


def _record_run(macro_id: int, ok: int, failed: int, now: datetime) -> None:
    with _lock, _db() as conn:
        conn.execute(
            "INSERT INTO macro_runs (macro_id, steps_ok, steps_failed, ran_at)"
            " VALUES (?, ?, ?, ?)",
            (macro_id, ok, failed, now.isoformat(timespec="seconds")))
        conn.commit()


def _min_step_tier(steps: list, now: datetime) -> tuple[str, list]:
    """A macro inherits the MINIMUM autonomy tier of its steps."""
    from services import autonomy_engine as ae
    decisions = [ae.decide(step["tool"], step["tool"], now=now) for step in steps]
    lowest = min(decisions, key=lambda d: TIER_RANK.get(d["tier"], 0))
    return lowest["tier"], decisions


def run_macro(macro_id: int | None = None, trigger: str | None = None,
              force: bool = False) -> dict:
    """Execute a macro's chain (or return a confirm-tier suggestion).

    force=True is the owner's explicit approval (HUD run button / API) and
    dispatches steps directly; the organic path routes each step through
    autonomy_engine.run so it is journaled and individually undoable.
    """
    now = _now()
    macro = get_macro(macro_id) if macro_id is not None else get_macro_by_trigger(trigger or "")
    if not macro:
        return {"status": "error", "message": "macro not found", "executed": False}
    steps = macro["steps"]
    label = macro["trigger_phrase"]
    trust_action = f"macro:{label}"

    tier, decisions = _min_step_tier(steps, now)
    if not force and tier == "confirm":
        return {"status": "ok", "executed": False, "tier": tier,
                "suggestion": f"Prem, shall I run '{label}'?"}

    from services import autonomy_engine as ae
    replies, steps_ok = [], 0
    failed_at = None
    for step in steps:
        if force:
            reply = _dispatch(step["tool"], step["params"])
            step_failed = _failed(reply)
        else:
            outcome = ae.run(step["tool"], step["tool"], step["params"])
            reply = outcome.get("result", "")
            step_failed = not outcome.get("executed")
        if step_failed:
            failed_at = (len(replies) + 1, step["tool"], reply)
            break
        replies.append(reply)
        steps_ok += 1

    _record_run(macro["id"], steps_ok, 1 if failed_at else 0, now)
    ae.record_outcome(trust_action, "rejected" if failed_at else "accepted", now=now)

    if failed_at:
        n, tool, reply = failed_at
        return {"status": "error", "executed": False, "tier": tier,
                "steps_ok": steps_ok, "steps_failed": 1,
                "failed_step": {"index": n, "tool": tool},
                "reply": f"Macro '{label}' stopped at step {n} ({tool}). {reply}"}

    joined = " | ".join(r for r in replies if r)[:400]
    return {"status": "ok", "executed": True, "tier": tier,
            "steps_ok": steps_ok, "steps_failed": 0,
            "reply": f"Macro '{label}' complete. {joined}".strip(),
            "announce": tier == "announce"}


def match_and_maybe_run(text: str) -> dict | None:
    """Chat-entry fast path. None → not a macro trigger (brain handles text)."""
    macro = get_macro_by_trigger(text)
    if not macro:
        return None
    result = run_macro(trigger=text)
    if not result.get("executed") and result.get("suggestion"):
        return {"reply": result["suggestion"], "action": "macro_confirm"}
    return {"reply": result.get("reply", "Done."), "action": "macro"}


# ── Tool Router handlers (voice creation/deletion) ───────────────────────────

def handle_create_macro(args: dict) -> str:
    try:
        result = create_macro(
            trigger=str(args.get("trigger") or args.get("trigger_phrase") or ""),
            steps=args.get("steps") or [],
            created_by="voice")
    except MacroError as err:
        return f"I couldn't save that macro: {err}."
    tools = ", ".join(s["tool"] for s in result["steps"])
    return (f"Macro '{result['trigger_phrase']}' saved with "
            f"{len(result['steps'])} steps: {tools}. Say "
            f"'{result['trigger_phrase']}' anytime, Prem.")


def handle_delete_macro(args: dict) -> str:
    result = delete_macro(trigger=str(args.get("trigger") or ""))
    if result["status"] != "ok":
        return "I couldn't find a macro with that trigger phrase."
    return "Macro deleted, Prem."
