"""services/agent/integrations/email/provider.py — Email Provider Abstraction & Data Models.

Defines the clean boundary between the F.R.I.D.A.Y. Agent Brain and underlying
email transports (IMAP/SMTP, Gmail API, macOS Mail, or Mock/Dry-Run).
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EmailConnectionStatus(str, Enum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    CREDENTIALS_STORED = "CREDENTIALS_STORED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    CONNECTED = "CONNECTED"
    PARTIALLY_CONNECTED = "PARTIALLY_CONNECTED"
    TEMPORARILY_UNAVAILABLE = "TEMPORARILY_UNAVAILABLE"


class ConnectionTestResult(BaseModel):
    status: EmailConnectionStatus
    imap_connected: bool
    smtp_connected: bool
    imap_detail: str
    smtp_detail: str
    tested_at: str


class EmailMessage(BaseModel):
    id: str
    thread_id: Optional[str] = None
    sender: str
    sender_name: Optional[str] = None
    subject: str
    timestamp: int
    preview: str
    body: Optional[str] = None
    is_unread: bool = True
    priority: bool = False
    provider: str = "email"


class EmailDraft(BaseModel):
    id: str
    to: str
    subject: str
    body: str
    attachments: List[str] = Field(default_factory=list)
    created_at: float
    expires_at: float
    status: str = "pending"  # "pending", "approved", "sent", "cancelled"


class SendResult(BaseModel):
    success: bool
    message_id: Optional[str] = None
    recipient: str
    subject: str
    timestamp: str
    provider: str
    status: str  # "sent", "accepted", "failed", "duplicate_prevented"
    error: Optional[str] = None


class VerificationResult(BaseModel):
    verified: bool
    provider_message_id: Optional[str] = None
    status: str
    note: str


class EmailProvider(ABC):
    """Abstract interface for email capabilities."""

    @abstractmethod
    def check_connection(self) -> EmailConnectionStatus:
        """Returns truthful connection status."""
        pass

    @abstractmethod
    def test_connection(self) -> ConnectionTestResult:
        """Runs independent IMAP and SMTP connection tests."""
        pass

    @abstractmethod
    def get_messages(self, limit: int = 10, unread_only: bool = True) -> List[EmailMessage]:
        """Fetch incoming emails without modifying external state."""
        pass

    @abstractmethod
    def search_messages(self, query: str, limit: int = 10) -> List[EmailMessage]:
        """Search inbox by subject, sender, or content."""
        pass

    @abstractmethod
    def create_draft(self, to: str, subject: str, body: str, attachments: Optional[List[str]] = None) -> EmailDraft:
        """Persist a draft server-side with a TTL."""
        pass

    @abstractmethod
    def update_draft(self, draft_id: str, to: Optional[str] = None, subject: Optional[str] = None, body: Optional[str] = None) -> Optional[EmailDraft]:
        """Update an existing draft."""
        pass

    @abstractmethod
    def get_draft(self, draft_id: str) -> Optional[EmailDraft]:
        """Retrieve active draft."""
        pass

    @abstractmethod
    def send_message(self, to: str, subject: str, body: str, attachments: Optional[List[str]] = None, draft_id: Optional[str] = None) -> SendResult:
        """Send an approved message through the transport."""
        pass

    @abstractmethod
    def verify_message(self, provider_message_id: str) -> VerificationResult:
        """Independently verify message acceptance by provider."""
        pass
