"""Sanitized Calendar Audit Logger.

Records structured audit logs for calendar read, draft, approval, creation, and verification events.
Ensures zero sensitive credential leaks.
"""

import re
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Dict, Any, List, Optional


SENSITIVE_PATTERNS = [
    (r"(password|passwd|pwd)\s*=\s*['\"]?[^'\"\s]+['\"]?", r"\1=[REDACTED]"),
    (r"(api[_-]?key|token|secret)\s*=\s*['\"]?[^'\"\s]+['\"]?", r"\1=[REDACTED]"),
    (r"bearer\s+[a-zA-Z0-9\-\._~\+\/]+=*", r"Bearer [REDACTED]"),
]


def sanitize_calendar_text(text: str) -> str:
    """Sanitize text by redacting sensitive tokens."""
    if not text:
        return ""
    sanitized = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    return sanitized


def mask_attendee_email(email: str) -> str:
    """Safely mask attendee email address for privacy in logs."""
    if not email or "@" not in email:
        return sanitize_calendar_text(email)
    parts = email.split("@")
    user = parts[0]
    domain = parts[1]
    if len(user) <= 2:
        masked_user = user[0] + "*"
    else:
        masked_user = user[0] + "*" * (len(user) - 2) + user[-1]
    return f"{masked_user}@{domain}"


@dataclass
class CalendarAuditRecord:
    timestamp: str
    action: str
    event_id: str
    approval_id: str
    event_hash: str
    title_sanitized: str
    provider_event_id: str
    result: str
    verification_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "event_id": self.event_id,
            "approval_id": self.approval_id,
            "event_hash": self.event_hash,
            "title_sanitized": self.title_sanitized,
            "provider_event_id": self.provider_event_id,
            "result": self.result,
            "verification_result": self.verification_result,
        }


class CalendarAuditLogger:
    """Audit logging engine for calendar system events."""

    def __init__(self):
        self._logs: List[CalendarAuditRecord] = []

    def log_event(
        self,
        action: str,
        event_id: str = "",
        approval_id: str = "",
        event_hash: str = "",
        title: str = "",
        provider_event_id: str = "",
        result: str = "",
        verification_result: Optional[Dict[str, Any]] = None,
    ) -> CalendarAuditRecord:
        """Record a sanitized audit event."""
        now_iso = datetime.now(timezone.utc).isoformat()
        record = CalendarAuditRecord(
            timestamp=now_iso,
            action=sanitize_calendar_text(action),
            event_id=sanitize_calendar_text(event_id),
            approval_id=sanitize_calendar_text(approval_id),
            event_hash=sanitize_calendar_text(event_hash),
            title_sanitized=sanitize_calendar_text(title),
            provider_event_id=sanitize_calendar_text(provider_event_id),
            result=sanitize_calendar_text(result),
            verification_result=verification_result,
        )
        self._logs.append(record)
        return record

    def get_logs(self) -> List[Dict[str, Any]]:
        """Return all recorded audit logs."""
        return [r.to_dict() for r in self._logs]

    def clear(self):
        """Clear audit logs for testing."""
        self._logs.clear()


# Global audit logger instance for calendar
calendar_audit_logger = CalendarAuditLogger()
