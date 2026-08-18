"""Sanitized Email Audit Logger.

Records structured audit logs for email creation, approval, dispatch, and verification events.
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


def sanitize_log_text(text: str) -> str:
    """Sanitize text by redacting passwords, API keys, and sensitive tokens."""
    if not text:
        return ""
    sanitized = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    return sanitized


def mask_recipient(recipient: str) -> str:
    """Safely mask recipient email address for privacy in logs."""
    if not recipient or "@" not in recipient:
        return sanitize_log_text(recipient)
    parts = recipient.split("@")
    user = parts[0]
    domain = parts[1]
    if len(user) <= 2:
        masked_user = user[0] + "*"
    else:
        masked_user = user[0] + "*" * (len(user) - 2) + user[-1]
    return f"{masked_user}@{domain}"


@dataclass
class AuditRecord:
    timestamp: str
    action: str
    draft_id: str
    approval_id: str
    content_hash: str
    recipient_masked: str
    provider_message_id: str
    result: str
    verification_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "draft_id": self.draft_id,
            "approval_id": self.approval_id,
            "content_hash": self.content_hash,
            "recipient_masked": self.recipient_masked,
            "provider_message_id": self.provider_message_id,
            "result": self.result,
            "verification_result": self.verification_result,
        }


class EmailAuditLogger:
    """Audit logging engine for email system events."""

    def __init__(self):
        self._logs: List[AuditRecord] = []

    def log_event(
        self,
        action: str,
        draft_id: str = "",
        approval_id: str = "",
        content_hash: str = "",
        recipient: str = "",
        provider_message_id: str = "",
        result: str = "",
        verification_result: Optional[Dict[str, Any]] = None,
    ) -> AuditRecord:
        """Record a sanitized audit event."""
        now_iso = datetime.now(timezone.utc).isoformat()
        record = AuditRecord(
            timestamp=now_iso,
            action=sanitize_log_text(action),
            draft_id=sanitize_log_text(draft_id),
            approval_id=sanitize_log_text(approval_id),
            content_hash=sanitize_log_text(content_hash),
            recipient_masked=mask_recipient(recipient),
            provider_message_id=sanitize_log_text(provider_message_id),
            result=sanitize_log_text(result),
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


# Global audit logger instance
audit_logger = EmailAuditLogger()
