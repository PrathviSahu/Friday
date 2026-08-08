"""presence.py — Cross-Device Presence (Phase 2.5).

Pushes FRIDAY's pending approvals to Prem's devices — Telegram inline
[ ✅ Approve ] [ ❌ Deny ] buttons and PWA Web Push — so approval-first
survives beyond the desktop, per next_phase_2_architecture.md §4-E.

Doctrine (exactly per spec):
  * Presence devices can only RESOLVE approvals (approve/deny), never mint
    new capabilities: `resolve_decision` consumes a one-time token bound to
    a specific capability and delegates to the SAME Permission Center
    one-time-approval mechanism (`permissions.grant_approval`).
  * No new daemons: the Telegram path rides the existing telegram_bot's
    application/loop; the PWA path is a stateless VAPID-signed "tickle"
    push that wakes the service worker to pull pending items.
  * No new dependencies: Web Push uses payload-free POSTs (RFC 8030 permits
    empty bodies), so no message encryption is needed — only a VAPID ES256
    JWT, signed with the already-shipped `cryptography` package.
  * Everything graceful: no bot token / no VAPID keys / offline → the push
    is logged to the outbox as unsent and the approval still works from the
    desktop Permission Center.

Table (unified friday_brain.db): presence_tokens (per spec §3-C).
"""

import base64
import json
import os
import secrets
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "friday_brain.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_lock = threading.RLock()

DEVICE_KINDS = {"pwa", "telegram"}
PENDING_TTL_SECONDS = 300           # approvals expire like Permission Center ones

# ── In-memory pending store + push hooks (same doctrine as permissions.) ──────

_PENDING: dict = {}                # token -> approval record
_OUTBOX: list = []                 # observability for pushes (sent or skipped)

# Set by telegram_bot while it runs: callable(chat_id: str, record: dict).
TELEGRAM_SENDER = None


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_presence_db() -> None:
    with _db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS presence_tokens (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            device_kind     TEXT NOT NULL,          -- 'pwa' | 'telegram'
            token           TEXT NOT NULL UNIQUE,   -- push subscription JSON or chat_id
            label           TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()


init_presence_db()


# ── Device registry ───────────────────────────────────────────────────────────

def register_device(device_kind: str, token: str, label: str = "") -> dict:
    device_kind = (device_kind or "").strip().lower()
    token = (token or "").strip()
    if device_kind not in DEVICE_KINDS:
        return {"status": "error",
                "message": f"device_kind must be one of {sorted(DEVICE_KINDS)}"}
    if len(token) < 4:
        return {"status": "error", "message": "token is required"}
    with _lock, _db() as conn:
        conn.execute("""
        INSERT INTO presence_tokens (device_kind, token, label)
        VALUES (?, ?, ?)
        ON CONFLICT(token) DO UPDATE SET device_kind = excluded.device_kind,
                                         label = excluded.label
        """, (device_kind, token, (label or "").strip()[:80]))
        conn.commit()
    return {"status": "ok", "device_kind": device_kind,
            "label": label, "devices": len(list_devices())}


def list_devices() -> list:
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, device_kind, token, label, created_at FROM presence_tokens "
            "ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def remove_device(device_id: int | None = None, token: str | None = None) -> dict:
    with _lock, _db() as conn:
        if device_id is not None:
            cur = conn.execute("DELETE FROM presence_tokens WHERE id = ?", (device_id,))
        elif token:
            cur = conn.execute("DELETE FROM presence_tokens WHERE token = ?", (token,))
        else:
            return {"status": "error", "message": "missing device id or token"}
        conn.commit()
        deleted = cur.rowcount > 0
    return {"status": "ok" if deleted else "error",
            "message": None if deleted else "device not found"}


# ── Pending approvals ─────────────────────────────────────────────────────────

def _prune_expired() -> None:
    now = time.time()
    for key in [k for k, v in _PENDING.items() if v["expires_at"] < now]:
        _PENDING.pop(key, None)


def create_approval(capability: str, description: str,
                    action: dict | None = None, push: bool = True) -> dict:
    """Create a resolvable approval and push it to every registered device.

    `action` (optional) is an executable descriptor such as
    {"kind": "email_send_draft", "draft_id": "..."} — resolved AFTER the
    human approves, using the freshly granted one-time approval.
    """
    from services import permissions
    capability = (capability or "").strip()
    if capability not in permissions.CAPABILITIES:
        return {"status": "error", "message": f"unknown capability '{capability}'"}
    _prune_expired()
    token = secrets.token_urlsafe(16)
    record = {
        "approval_token": token,
        "capability": capability,
        "description": (description or "")[:300],
        "action": action,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "expires_at": time.time() + PENDING_TTL_SECONDS,
    }
    _PENDING[token] = record
    if push:
        push_approval(record)
    return {"status": "ok", "approval_token": token,
            "expires_in": PENDING_TTL_SECONDS}


def list_pending() -> list:
    """Safe pending view for devices/service workers (no internal state)."""
    _prune_expired()
    return [{"approval_token": p["approval_token"],
             "capability": p["capability"],
             "description": p["description"],
             "created_at": p["created_at"],
             "has_action": bool(p["action"])}
            for p in sorted(_PENDING.values(), key=lambda r: r["created_at"], reverse=True)]


def _resolve_action(action: dict) -> tuple[bool, str]:
    """Execute an approval's deferred payload after the human said yes."""
    kind = (action or {}).get("kind")
    try:
        if kind == "email_send_draft":
            from services import email_agent
            result = email_agent.send_draft(str(action.get("draft_id", "")))
            return True, result.get("message", "Email sent.") if isinstance(result, dict) \
                else str(result)
        if kind == "macro_run":
            from services import macros
            result = macros.run_macro(macro_id=int(action.get("macro_id", 0)), force=True)
            return bool(result.get("executed")), result.get("reply", "")
        return False, f"no resolver for action kind '{kind}'"
    except Exception as err:
        return False, f"action failed: {err}"


def resolve_decision(approval_token: str, decision: str) -> dict:
    """Resolve one pending approval from ANY trusted device.

    Security boundary: this can grant ONLY the specific capability the
    approval was created for, via the standard Permission Center mechanism.
    It cannot create capabilities, change modes, or skip owner gating.
    """
    _prune_expired()
    record = _PENDING.pop(approval_token, None)
    if not record:
        return {"status": "error", "message": "unknown or expired approval"}

    decision = (decision or "").strip().lower()
    if decision not in {"approve", "deny"}:
        _PENDING[approval_token] = record            # invalid decision ≠ consume
        return {"status": "error", "message": "decision must be 'approve' or 'deny'"}

    if decision == "deny":
        from services import permissions
        permissions._audit(record["capability"], "presence_denied",
                           f"denied from device, token …{approval_token[-4:]}")
        return {"status": "ok", "decision": "deny", "executed": False,
                "message": f"Denied: {record['capability']}"}

    from services import permissions
    granted = permissions.grant_approval(record["capability"])
    if not granted:
        return {"status": "error", "message": "capability no longer exists"}

    executed, result_text = False, ""
    if record["action"]:
        executed, result_text = _resolve_action(record["action"])
    permissions._audit(record["capability"], "presence_approved",
                       f"approved from device, token …{approval_token[-4:]}")
    return {"status": "ok", "decision": "approve", "executed": executed,
            "capability": record["capability"],
            "message": result_text or f"Approved: {record['capability']} for "
                                     f"{permissions.APPROVAL_DEFAULT_SECONDS}s."}


# ── Push delivery (Telegram + PWA Web Push tickle) ────────────────────────────

def push_approval(record: dict) -> list:
    """Push a pending approval to every registered device. Returns outbox rows."""
    results = []
    for device in list_devices():
        if device["device_kind"] == "telegram":
            results.append(_push_telegram(device, record))
        elif device["device_kind"] == "pwa":
            results.append(_push_pwa(device, record))
    return results


def _outbox(device_kind: str, sent: bool, reason: str = "") -> dict:
    row = {"device_kind": device_kind, "sent": sent, "reason": reason,
           "at": datetime.now().isoformat(timespec="seconds")}
    _OUTBOX.append(row)
    del _OUTBOX[:-50]                                # keep last 50
    return row


def _push_telegram(device: dict, record: dict) -> dict:
    """Hand off to the running bot's inline-keyboard sender, if it is live."""
    sender = TELEGRAM_SENDER
    if sender is None:
        return _outbox("telegram", False, "bot not running")
    try:
        sender(device["token"], record)
        return _outbox("telegram", True)
    except Exception as err:
        return _outbox("telegram", False, str(err)[:120])


def _vapid_jwt(endpoint: str) -> tuple[str, str] | None:
    """Build the VAPID (t, k) pair for a push endpoint, or None if unconfigured."""
    public_key = os.getenv("VAPID_PUBLIC_KEY", "").strip()
    private_key = os.getenv("VAPID_PRIVATE_KEY", "").strip()
    if not public_key or not private_key:
        return None
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec, utils

        key_int = int.from_bytes(_b64url_decode(private_key), "big")
        key = ec.derive_private_key(key_int, ec.SECP256R1())

        def _b64url(data: bytes) -> str:
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

        header = _b64url(json.dumps({"typ": "JWT", "alg": "ES256"}).encode())
        from urllib.parse import urlparse
        aud = f"{urlparse(endpoint).scheme}://{urlparse(endpoint).netloc}"
        claims = _b64url(json.dumps({
            "aud": aud, "exp": int(time.time()) + 12 * 3600,
            "sub": os.getenv("VAPID_SUBJECT", "mailto:prem@friday.local"),
        }).encode())
        sig = key.sign(f"{header}.{claims}".encode(), ec.ECDSA(hashes.SHA256()))
        r, s = utils.decode_dss_signature(sig)
        jwt = f"{header}.{claims}.{_b64url(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))}"
        return jwt, public_key
    except Exception:
        return None


def _push_pwa(device: dict, record: dict) -> dict:
    """Payload-free 'tickle' push: wake the SW, it pulls /api/presence/pending."""
    try:
        sub = json.loads(device["token"])
        endpoint = sub.get("endpoint", "")
    except (json.JSONDecodeError, AttributeError):
        return _outbox("pwa", False, "invalid subscription")
    if not endpoint:
        return _outbox("pwa", False, "missing endpoint")
    vapid = _vapid_jwt(endpoint)
    if vapid is None:
        return _outbox("pwa", False, "VAPID keys not configured")
    jwt, public_key = vapid
    try:
        import requests
        resp = requests.post(endpoint, timeout=8, headers={
            "TTL": "60", "Urgency": "high",
            "Authorization": f"vapid t={jwt}, k={public_key}",
        })
        return _outbox("pwa", resp.status_code in (200, 201, 202),
                       f"push service {resp.status_code}")
    except Exception as err:
        return _outbox("pwa", False, str(err)[:120])


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def get_outbox() -> list:
    """Last push attempts — diagnostics for the DevTools panel."""
    return list(_OUTBOX)
