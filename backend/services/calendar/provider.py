"""Calendar provider dispatch engine.

Provides MockCalendarProvider for safe dry-run execution and RealCalendarProvider protected by safety guards.
"""

import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

from .config import assert_live_calendar_execution_allowed, is_live_calendar_execution_enabled, RealCalendarBlockedError


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


class MockCalendarProvider:
    """Deterministic Mock Calendar Provider for testing and dry-run execution.

    No external AppleScript / Google Calendar API calls.
    """

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self.should_fail: bool = False  # Flag to simulate provider failure in tests

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


class RealCalendarProvider:
    """Production Calendar Provider.

    Protected by assert_live_calendar_execution_allowed(). Will fail loudly if invoked
    while CALENDAR_LIVE_EXECUTION=false.
    """

    def create_event(self, title: str, start_time: str, end_time: str, **kwargs) -> Any:
        """Attempt real calendar creation. Must raise RealCalendarBlockedError if CALENDAR_LIVE_EXECUTION=false."""
        assert_live_calendar_execution_allowed()
        raise RealCalendarBlockedError("Real Calendar creation is not configured or allowed.")
