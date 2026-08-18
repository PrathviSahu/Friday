"""services/agent/integrations/calendar/provider.py — Calendar Provider Abstraction & Data Models.

Defines the clean boundary between the F.R.I.D.A.Y. Agent Brain and underlying
calendar transports (Google Calendar API, Apple Calendar, or Mock/Dry-Run).
"""

import hashlib
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CalendarConnectionStatus(str, Enum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    CREDENTIALS_STORED = "CREDENTIALS_STORED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    CONNECTED = "CONNECTED"
    PARTIALLY_CONNECTED = "PARTIALLY_CONNECTED"
    TEMPORARILY_UNAVAILABLE = "TEMPORARILY_UNAVAILABLE"


def compute_calendar_content_hash(
    title: str,
    start_time: str,
    end_time: str,
    timezone: str,
    location: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    reminders: Optional[List[int]] = None
) -> str:
    """Computes a deterministic SHA-256 fingerprint for a calendar event draft."""
    att_str = ",".join(sorted(attendees or []))
    rem_str = ",".join(str(r) for r in sorted(reminders or []))
    raw = f"{title.strip().lower()}|{start_time.strip()}|{end_time.strip()}|{timezone.strip()}|{(location or '').strip().lower()}|{att_str}|{rem_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class CalendarEvent(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: str
    end_time: str
    timezone: str = "Asia/Kolkata"
    attendees: List[str] = Field(default_factory=list)
    reminders: List[int] = Field(default_factory=lambda: [30])
    recurrence: Optional[str] = None
    status: str = "confirmed"
    provider: str = "calendar"


class CalendarEventDraft(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: str
    end_time: str
    timezone: str = "Asia/Kolkata"
    attendees: List[str] = Field(default_factory=list)
    reminders: List[int] = Field(default_factory=lambda: [30])
    recurrence: Optional[str] = None
    created_at: float
    expires_at: float
    content_hash: str = ""
    status: str = "pending"  # "pending", "approved", "created", "cancelled"
    context_id: Optional[str] = None


class CalendarCreateResult(BaseModel):
    success: bool
    event_id: Optional[str] = None
    title: str
    start_time: str
    end_time: str
    timezone: str
    attendees: List[str] = Field(default_factory=list)
    timestamp: str
    provider: str = "calendar"
    status: str = "created"  # "created", "failed"
    error: Optional[str] = None


class CalendarVerificationResult(BaseModel):
    verified: bool
    provider_event_id: Optional[str] = None
    status: str
    note: str


class CalendarProvider(ABC):
    """Abstract interface for calendar capabilities."""

    @abstractmethod
    def check_connection(self) -> CalendarConnectionStatus:
        """Returns truthful connection status."""
        pass

    @abstractmethod
    def list_events(self, time_min: Optional[str] = None, time_max: Optional[str] = None, limit: int = 10) -> List[CalendarEvent]:
        """List events in time window without mutating state."""
        pass

    @abstractmethod
    def search_events(self, query: str, limit: int = 10) -> List[CalendarEvent]:
        """Search calendar by query string."""
        pass

    @abstractmethod
    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """Retrieve a specific calendar event by ID."""
        pass

    @abstractmethod
    def create_draft_event(
        self,
        title: str,
        start_time: str,
        end_time: str,
        timezone: str = "Asia/Kolkata",
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        reminders: Optional[List[int]] = None,
        recurrence: Optional[str] = None
    ) -> CalendarEventDraft:
        """Persist an event draft server-side with a TTL."""
        pass

    @abstractmethod
    def update_draft_event(
        self,
        draft_id: str,
        title: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        timezone: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        reminders: Optional[List[int]] = None
    ) -> Optional[CalendarEventDraft]:
        """Update an existing event draft and recompute content hash."""
        pass

    @abstractmethod
    def cancel_draft_event(self, draft_id: str) -> bool:
        """Cancel a pending event draft."""
        pass

    @abstractmethod
    def create_event(
        self,
        title: str,
        start_time: str,
        end_time: str,
        timezone: str = "Asia/Kolkata",
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        reminders: Optional[List[int]] = None,
        draft_id: Optional[str] = None
    ) -> CalendarCreateResult:
        """Dispatch approved calendar event to provider."""
        pass

    @abstractmethod
    def verify_event(self, provider_event_id: str) -> CalendarVerificationResult:
        """Independently verify event existence and metadata."""
        pass

    @abstractmethod
    def delete_event(self, event_id: str) -> bool:
        """Autonomous deletion is blocked."""
        pass
