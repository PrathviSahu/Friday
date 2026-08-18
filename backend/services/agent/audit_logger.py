"""services/agent/audit_logger.py — Safe Audit Logging & Idempotency Store.

Records all agent tool executions in SQLite with automatic secret sanitization.
Prevents duplicate execution of risky external operations (emails, applications, trades).
"""

import json
import time
import sqlite3
import threading
from typing import Dict, Any, Optional
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "friday_brain.db"
_audit_lock = threading.RLock()

# Idempotency cache: key -> timestamp
_idempotency_store: Dict[str, float] = {}
IDEMPOTENCY_WINDOW_SECONDS = 300  # 5 minutes


def _db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_audit_db():
    """Initializes the action_audit_log table."""
    with _audit_lock, _db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS action_audit_log (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id       TEXT UNIQUE NOT NULL,
            timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_request       TEXT,
            domain             TEXT,
            tool_name          TEXT NOT NULL,
            sanitized_args     TEXT NOT NULL,
            permission_level   TEXT NOT NULL,
            approval_required  BOOLEAN NOT NULL,
            approved           BOOLEAN NOT NULL,
            success            BOOLEAN NOT NULL,
            verified           BOOLEAN NOT NULL,
            verification_note  TEXT,
            error_code         TEXT
        )""")
        conn.commit()


init_audit_db()


def sanitize_payload(payload: Any) -> Any:
    """Recursively redacts passwords, tokens, API keys, and sensitive secrets."""
    if isinstance(payload, dict):
        sanitized = {}
        for k, v in payload.items():
            if any(sec in k.lower() for sec in ["password", "pass", "token", "api_key", "secret", "bearer", "private_key", "auth", "credential"]):
                sanitized[k] = "[REDACTED_SECRET]"
            else:
                sanitized[k] = sanitize_payload(v)
        return sanitized
    elif isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    return payload


def check_idempotency(idempotency_key: str) -> bool:
    """Returns True if this exact action was already executed within the idempotency window."""
    with _audit_lock:
        now = time.time()
        # Evict old keys
        for k in list(_idempotency_store):
            if now - _idempotency_store[k] > IDEMPOTENCY_WINDOW_SECONDS:
                del _idempotency_store[k]
        
        if idempotency_key in _idempotency_store:
            return True
        return False


def record_idempotency(idempotency_key: str):
    """Mark an action as executed to prevent duplicates."""
    with _audit_lock:
        _idempotency_store[idempotency_key] = time.time()


def clear_idempotency_store():
    """Clear in-memory idempotency cache (useful for tests)."""
    with _audit_lock:
        _idempotency_store.clear()


def log_audit_record(
    execution_id: str,
    user_request: str,
    domain: str,
    tool_name: str,
    arguments: Dict[str, Any],
    permission_level: str,
    approval_required: bool,
    approved: bool,
    success: bool,
    verified: bool,
    verification_note: str = "",
    error_code: Optional[str] = None
):
    """Persists a sanitized tool execution record."""
    clean_args = json.dumps(sanitize_payload(arguments))
    with _audit_lock, _db() as conn:
        conn.execute("""
        INSERT INTO action_audit_log (
            execution_id, user_request, domain, tool_name, sanitized_args,
            permission_level, approval_required, approved, success, verified,
            verification_note, error_code
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            execution_id, user_request, domain, tool_name, clean_args,
            permission_level, approval_required, approved, success, verified,
            verification_note, error_code
        ))
        conn.commit()
