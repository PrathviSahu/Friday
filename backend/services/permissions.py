"""permissions.py — Permission Center (v3.1).

A persisted policy store for every sensitive capability FRIDAY can perform.
Each capability has a mode:

  enabled     — allowed (still owner-gated via auth)
  ask         — "ask every time": requires a short-lived one-time approval
  disabled    — always blocked

One-time approvals (mode `ask`) are granted via POST /api/permissions/approve
and expire after a few minutes. Every enforcement decision is written to the
permission_audit table so the HUD can show an activity log.

Design rule (from the roadmap): actions with real-world consequences
(send email, apply to jobs, execute trades, delete files, place phone calls)
default to `ask` — FRIDAY can prepare them, but the human approves first.
"""

import json
import os
import sqlite3
import threading
import time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "friday_brain.db"

_lock = threading.RLock()

# ── Capability catalog ────────────────────────────────────────────────────────
# key -> (default_mode, human label, description)
# Defaults keep everything the current UI uses working (`enabled`); future /
# high-stakes capabilities default to `ask` so nothing can happen without
# explicit approval.
CAPABILITIES = {
    "system.control":  ("enabled", "Computer Control", "Open apps, brightness, volume, lock screen"),
    "music.control":   ("enabled", "Music Control", "Spotify playback, volume, seek"),
    "tasks.write":     ("enabled", "Tasks & Reminders", "Create/edit todos and reminders"),
    "web.search":      ("enabled", "Web Search", "Search the web and open pages"),
    "screen.capture":  ("ask",     "Screen Capture", "Screenshots and screen recording"),
    "gdrive.write":    ("enabled", "Google Drive Backup", "Write DB backups to Drive"),
    "email.read":      ("ask",     "Read Email", "Read and summarize inbox (needs Gmail/IMAP)"),
    "email.send":      ("ask",     "Send Email", "Draft and send emails (always ask)"),
    "calendar.read":   ("ask",     "Read Calendar", "Read calendar events (needs Google Calendar)"),
    "meetings.read":   ("enabled", "Meetings", "Read meeting summaries and action items"),
    "meetings.create": ("enabled", "Meetings", "Transcribe & process meeting recordings (Groq credits)"),
    "documents.read":  ("enabled", "Documents", "Read, search, ask & summarize uploaded documents"),
    "documents.upload": ("enabled", "Documents", "Upload documents for the Document AI (Groq credits)"),
    "coding.analyze":  ("enabled", "Coding AI", "Review, explain, test & document pasted code (Groq credits)"),
    "whatsapp.read":   ("ask",     "Read WhatsApp", "Read and summarize chats (needs WhatsApp)"),
    "whatsapp.send":   ("ask",     "Send WhatsApp", "Send messages (always ask)"),
    "phone.call":      ("ask",     "Phone Calls", "Make calls (always ask, needs phone link)"),
    "calendar.write":  ("ask",     "Calendar", "Create meetings and reminders"),
    "jobs.apply":      ("ask",     "Apply to Jobs", "Submit job applications (always ask)"),
    "trades.execute":  ("ask",     "Execute Trades", "Place trading orders (always ask)"),
    "files.delete":    ("disabled", "Delete Files", "Permanently delete files (disabled by default)"),
    "vault.access":    ("enabled", "Personal Vault", "Encrypted credential vault"),
    "plugins.install": ("ask",     "Install Plugins", "Install new plugins or integrations"),
    "agent.autonomy":  ("ask",     "Autonomous Agents", "Let agents take multi-step actions"),
}


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_permissions_db():
    with _lock, _connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS permissions (
            capability TEXT PRIMARY KEY,
            mode       TEXT NOT NULL DEFAULT 'enabled',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS permission_audit (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            capability  TEXT NOT NULL,
            decision    TEXT NOT NULL,       -- allowed | denied | approval_granted | approval_expired
            detail      TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        # Seed defaults (only missing capabilities; user overrides survive)
        for cap, (mode, _label, _desc) in CAPABILITIES.items():
            conn.execute(
                "INSERT OR IGNORE INTO permissions (capability, mode) VALUES (?, ?)",
                (cap, mode),
            )
        conn.commit()


init_permissions_db()


def get_permissions() -> list:
    """Return every capability with its effective mode + label + description."""
    with _lock, _connect() as conn:
        rows = {r["capability"]: r["mode"] for r in
                conn.execute("SELECT capability, mode FROM permissions").fetchall()}
    result = []
    for cap, (default, label, desc) in CAPABILITIES.items():
        result.append({
            "capability": cap,
            "label": label,
            "description": desc,
            "mode": rows.get(cap, default),
            "default_mode": default,
        })
    return result


def get_mode(capability: str) -> str:
    if capability not in CAPABILITIES:
        return "disabled"
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT mode FROM permissions WHERE capability = ?", (capability,)
        ).fetchone()
    return row["mode"] if row else CAPABILITIES[capability][0]


def set_mode(capability: str, mode: str) -> bool:
    """Update a capability's mode. Valid: enabled | ask | disabled."""
    if capability not in CAPABILITIES:
        return False
    if mode not in ("enabled", "ask", "disabled"):
        return False
    with _lock, _connect() as conn:
        conn.execute("""
        INSERT INTO permissions (capability, mode, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(capability) DO UPDATE SET
            mode = excluded.mode, updated_at = CURRENT_TIMESTAMP
        """, (capability, mode))
        conn.commit()
    return True


# ── One-time approvals ─────────────────────────────────────────────────────────
_APPROVALS: dict = {}  # capability -> expiry timestamp (in-memory, short-lived)
APPROVAL_DEFAULT_SECONDS = 300  # 5 minutes


def grant_approval(capability: str, seconds: int = APPROVAL_DEFAULT_SECONDS) -> bool:
    """Grant a one-time approval for `seconds`. Returns False for unknown caps."""
    if capability not in CAPABILITIES:
        return False
    with _lock:
        _APPROVALS[capability] = time.time() + max(10, int(seconds))
        _audit(capability, "approval_granted", f"approved for {seconds}s")
    return True


def revoke_approval(capability: str) -> None:
    with _lock:
        _APPROVALS.pop(capability, None)


def has_valid_approval(capability: str) -> bool:
    with _lock:
        expiry = _APPROVALS.get(capability, 0)
        if expiry and time.time() < expiry:
            return True
        if expiry:
            _APPROVALS.pop(capability, None)
            _audit(capability, "approval_expired", "")
    return False


def _audit(capability: str, decision: str, detail: str = "") -> None:
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO permission_audit (capability, decision, detail) VALUES (?, ?, ?)",
                (capability, decision, detail),
            )
            conn.commit()
    except Exception:
        pass


def check_permission(capability: str) -> str:
    """Enforce a capability. Returns 'allowed' | 'approval_required' | 'denied'.

    - enabled  → allowed
    - ask      → allowed only while a valid one-time approval exists
    - disabled → denied
    """
    mode = get_mode(capability)
    if mode == "disabled":
        _audit(capability, "denied", "capability disabled")
        return "denied"
    if mode == "enabled":
        _audit(capability, "allowed", "mode enabled")
        return "allowed"
    # ask
    if has_valid_approval(capability):
        _audit(capability, "allowed", "one-time approval")
        return "allowed"
    _audit(capability, "approval_required", "mode ask — grant via /api/permissions/approve")
    return "approval_required"


def require_permission(capability: str):
    """FastAPI dependency factory: 403 unless the capability is permitted.

    Attach to sensitive endpoints:  dependencies=[Depends(require_permission('trades.execute'))]
    """
    from fastapi import HTTPException

    def dependency():
        decision = check_permission(capability)
        if decision == "allowed":
            return
        raise HTTPException(
            status_code=403,
            detail={
                "permission": capability,
                "decision": decision,
                "message": (
                    f"Permission '{capability}' requires approval. "
                    "Grant it in the Permission Center or via /api/permissions/approve."
                ),
            },
        )
    return dependency


def get_audit_log(limit: int = 30) -> list:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT capability, decision, detail, created_at FROM permission_audit "
            "ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]
