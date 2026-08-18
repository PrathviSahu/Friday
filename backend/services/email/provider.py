"""Email provider dispatch engine.

Provides MockEmailProvider for safe dry-run execution and RealSMTPEmailProvider protected by safety guards.
"""

import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

from .config import assert_live_execution_allowed, is_live_execution_enabled, RealSMTPBlockedError


@dataclass
class MockSendResult:
    success: bool
    provider_message_id: str
    accepted_recipient: str
    timestamp: str
    mode: str = "DRY-RUN / MOCK PROVIDER"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "provider_message_id": self.provider_message_id,
            "accepted_recipient": self.accepted_recipient,
            "timestamp": self.timestamp,
            "mode": self.mode,
        }


class MockEmailProvider:
    """Deterministic Mock Email Provider for testing and dry-run execution.

    No external network calls, no SMTP sockets.
    """

    def __init__(self):
        self._outbox: Dict[str, Dict[str, Any]] = {}
        self.should_fail: bool = False  # Flag to simulate provider failure in tests

    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        draft_id: Optional[str] = None,
        approval_id: Optional[str] = None,
        content_hash: Optional[str] = None,
    ) -> MockSendResult:
        """Simulate sending an email and record in mock outbox."""
        if self.should_fail:
            raise RuntimeError("MockEmailProvider simulated dispatch failure.")

        msg_id = f"mock_msg_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        record = {
            "provider_message_id": msg_id,
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "attachments": attachments or [],
            "draft_id": draft_id,
            "approval_id": approval_id,
            "content_hash": content_hash,
            "status": "RECORDED_SENT",
            "timestamp": now_iso,
        }

        self._outbox[msg_id] = record

        return MockSendResult(
            success=True,
            provider_message_id=msg_id,
            accepted_recipient=recipient,
            timestamp=now_iso,
        )

    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve dispatched message record for independent verification."""
        return self._outbox.get(message_id)

    def clear(self):
        """Clear outbox store for tests."""
        self._outbox.clear()
        self.should_fail = False


class RealSMTPEmailProvider:
    """Production SMTP Email Provider.

    Protected by assert_live_execution_allowed(). Will fail loudly if invoked
    while EMAIL_LIVE_EXECUTION=false.
    """

    def send(self, recipient: str, subject: str, body: str, attachments: Optional[List[Dict[str, Any]]] = None) -> Any:
        """Attempt real SMTP send. Must raise RealSMTPBlockedError if EMAIL_LIVE_EXECUTION=false."""
        assert_live_execution_allowed()
        # If live execution were enabled, real SMTP logic would go here.
        # However, for safety in this environment, raise if ever invoked.
        raise RealSMTPBlockedError("Real SMTP execution is not configured or allowed.")
