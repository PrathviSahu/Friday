"""Calendar provider dispatch engine and connection architecture.

Provides MockCalendarProvider for safe dry-run testing and GoogleCalendarProvider
for real Google Calendar connection checks.
"""

import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

from .config import (
    CalendarConnectionStatus,
    assert_live_calendar_execution_allowed,
    is_live_calendar_execution_enabled,
    RealCalendarBlockedError,
)


@dataclass
class MockCalendarResult:
    success: bool
    provider_event_id: str
    title: str
    start_time: str
    end_time: str
    timestamp: str
    mode: str = "DRY-RUN / MOCK CALENDAR PROVIDER"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "provider_event_id": self.provider_event_id,
            "title": self.title,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "timestamp": self.timestamp,
            "mode": self.mode,
        }


class BaseCalendarProvider(ABC):
    """Canonical Calendar Provider Abstract Interface."""

    @abstractmethod
    def check_connection(self) -> Dict[str, Any]:
        """Perform read-only connection check and return truthful status."""
        pass

    @abstractmethod
    def create_event(
        self,
        title: str,
        start_time: str,
        end_time: str,
        location: str = "",
        description: str = "",
        attendees: Optional[List[str]] = None,
        event_id: Optional[str] = None,
        approval_id: Optional[str] = None,
        event_hash: Optional[str] = None,
    ) -> Any:
        pass

    @abstractmethod
    def get_event(self, provider_event_id: str) -> Optional[Dict[str, Any]]:
        pass


class MockCalendarProvider(BaseCalendarProvider):
    """Deterministic Mock Calendar Provider for testing and dry-run execution.

    No external AppleScript / Google Calendar API calls.
    """

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self.should_fail: bool = False
        self.simulated_status: CalendarConnectionStatus = CalendarConnectionStatus.CONNECTED

    def check_connection(self) -> Dict[str, Any]:
        """Return simulated connection status for mock testing."""
        if self.should_fail:
            return {
                "status": CalendarConnectionStatus.TEMPORARILY_UNAVAILABLE.value,
                "connected": False,
                "provider": "mock_calendar",
                "details": "Simulated provider temporary error.",
            }
        is_connected = (self.simulated_status == CalendarConnectionStatus.CONNECTED)
        return {
            "status": self.simulated_status.value,
            "connected": is_connected,
            "provider": "mock_calendar",
            "account": "mock_user@friday.ai",
            "scopes": ["calendar.readonly"],
        }

    def create_event(
        self,
        title: str,
        start_time: str,
        end_time: str,
        location: str = "",
        description: str = "",
        attendees: Optional[List[str]] = None,
        event_id: Optional[str] = None,
        approval_id: Optional[str] = None,
        event_hash: Optional[str] = None,
    ) -> MockCalendarResult:
        """Simulate creating a calendar event and record in mock store."""
        if self.should_fail:
            raise RuntimeError("MockCalendarProvider simulated event creation failure.")

        evt_id = f"mock_cal_evt_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        record = {
            "provider_event_id": evt_id,
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
            "location": location,
            "description": description,
            "attendees": attendees or [],
            "event_id": event_id,
            "approval_id": approval_id,
            "event_hash": event_hash,
            "status": "RECORDED_CREATED",
            "timestamp": now_iso,
        }

        self._store[evt_id] = record

        return MockCalendarResult(
            success=True,
            provider_event_id=evt_id,
            title=title,
            start_time=start_time,
            end_time=end_time,
            timestamp=now_iso,
        )

    def get_event(self, provider_event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve created event record for independent verification."""
        return self._store.get(provider_event_id)

    def list_events(self) -> List[Dict[str, Any]]:
        """List all mock events."""
        return list(self._store.values())

    def clear(self):
        """Clear event store for tests."""
        self._store.clear()
        self.should_fail = False
        self.simulated_status = CalendarConnectionStatus.CONNECTED


class GoogleCalendarProvider(BaseCalendarProvider):
    """Live Google Calendar Provider.

    Protected by assert_live_calendar_execution_allowed() for event mutations.
    """

    def check_connection(self) -> Dict[str, Any]:
        """Perform read-only connection check against Google Calendar API.

        Never mutates calendar state. Never logs tokens or secrets.
        """
        try:
            try:
                from services import calendar_agent
            except ImportError:
                from backend.services import calendar_agent

            if not calendar_agent.is_configured():
                return {
                    "status": CalendarConnectionStatus.NOT_CONFIGURED.value,
                    "connected": False,
                    "provider": "google_calendar",
                    "reason": "Credentials or tokens not configured.",
                }


            # Query real status from calendar_agent
            status_info = calendar_agent.get_status() if hasattr(calendar_agent, "get_status") else {}
            is_connected = status_info.get("connected", False)

            if is_connected:
                conn_enum = CalendarConnectionStatus.CONNECTED
            elif status_info.get("configured"):
                conn_enum = CalendarConnectionStatus.AUTH_REQUIRED
            else:
                conn_enum = CalendarConnectionStatus.NOT_CONFIGURED

            return {
                "status": conn_enum.value,
                "connected": is_connected,
                "provider": "google_calendar",
                "account": status_info.get("account", "configured_user"),
                "scopes": ["https://www.googleapis.com/auth/calendar.readonly"],
            }
        except Exception as err:
            return {
                "status": CalendarConnectionStatus.TEMPORARILY_UNAVAILABLE.value,
                "connected": False,
                "provider": "google_calendar",
                "reason": str(err),
            }

    def create_event(self, title: str, start_time: str, end_time: str, **kwargs) -> Any:
        """Attempt real calendar creation. Must raise RealCalendarBlockedError if CALENDAR_LIVE_EXECUTION=false."""
        assert_live_calendar_execution_allowed()
        raise RealCalendarBlockedError("Real Calendar creation is not configured or allowed.")

    def get_event(self, provider_event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a real event (read-only)."""
        return None


# Alias for backward compatibility and uniform provider naming
RealCalendarProvider = GoogleCalendarProvider

