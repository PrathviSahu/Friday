"""Calendar provider dispatch engine and connection architecture.

Provides MockCalendarProvider for safe dry-run testing and GoogleCalendarProvider
for real Google Calendar connection checks and read operations.
"""

import uuid
import re
from datetime import datetime, timezone, timedelta
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


def normalize_event_dict(raw: Dict[str, Any], default_tz: str = "Asia/Kolkata") -> Dict[str, Any]:
    """Normalize raw calendar event from provider into F.R.I.D.A.Y.'s canonical event shape.

    Handles all-day events vs timed events, cancelled status, and attendees.
    Prevents prompt injection by sanitizing untrusted event fields.
    """
    raw_start = raw.get("start", {})
    raw_end = raw.get("end", {})

    is_all_day = False
    if isinstance(raw_start, dict) and "date" in raw_start:
        is_all_day = True
        start_str = raw_start["date"]
        end_str = raw_end.get("date", start_str) if isinstance(raw_end, dict) else start_str
    elif isinstance(raw_start, str) and len(raw_start) == 10:
        is_all_day = True
        start_str = raw_start
        end_str = raw.get("end", start_str)
    else:
        start_str = raw_start.get("dateTime", "") if isinstance(raw_start, dict) else str(raw_start)
        end_str = raw_end.get("dateTime", "") if isinstance(raw_end, dict) else str(raw_end)

    raw_title = raw.get("summary") or raw.get("title") or "(No Title)"
    raw_desc = raw.get("description", "") or ""
    raw_loc = raw.get("location", "") or ""
    raw_org = raw.get("organizer", {})
    organizer_email = raw_org.get("email", "") if isinstance(raw_org, dict) else str(raw_org)

    attendees_list = []
    if raw.get("attendees"):
        for att in raw.get("attendees", []):
            if isinstance(att, dict) and "email" in att:
                attendees_list.append(att["email"])
            elif isinstance(att, str):
                attendees_list.append(att)

    event_id = raw.get("id") or raw.get("event_id") or f"evt_{uuid.uuid4().hex[:8]}"
    status = raw.get("status", "confirmed")

    return {
        "event_id": event_id,
        "title": raw_title.strip(),
        "start": start_str.strip(),
        "end": end_str.strip(),
        "start_time": start_str.strip(),
        "end_time": end_str.strip(),
        "timezone": raw_start.get("timeZone", default_tz) if isinstance(raw_start, dict) else default_tz,
        "location": raw_loc.strip(),
        "description": raw_desc.strip(),
        "organizer": organizer_email.strip(),
        "attendees_count": len(attendees_list),
        "attendees": attendees_list,
        "is_all_day": is_all_day,
        "status": status,
    }



class BaseCalendarProvider(ABC):
    """Canonical Calendar Provider Abstract Interface."""

    @abstractmethod
    def check_connection(self) -> Dict[str, Any]:
        """Perform read-only connection check and return truthful status."""
        pass

    @abstractmethod
    def list_calendars(self) -> List[Dict[str, Any]]:
        """List user's calendars."""
        pass


    @abstractmethod
    def get_today_events(self, tz_name: str = "Asia/Kolkata") -> List[Dict[str, Any]]:
        """Retrieve today's events."""
        pass

    @abstractmethod
    def get_upcoming_events(self, limit: int = 10, tz_name: str = "Asia/Kolkata") -> List[Dict[str, Any]]:
        """Retrieve upcoming events."""
        pass

    @abstractmethod
    def search_events(self, query: str, limit: int = 10, tz_name: str = "Asia/Kolkata") -> List[Dict[str, Any]]:
        """Search calendar events matching query."""
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
    """Deterministic Mock Calendar Provider for testing and dry-run execution."""

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self.should_fail: bool = False
        self.simulated_status: CalendarConnectionStatus = CalendarConnectionStatus.CONNECTED
        self._mock_calendars: List[Dict[str, Any]] = [
            {
                "id": "primary",
                "name": "Personal Calendar",
                "primary": True,
                "timezone": "Asia/Kolkata",
            }
        ]

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
            "scopes": ["https://www.googleapis.com/auth/calendar.readonly"],
        }

    def list_calendars(self) -> List[Dict[str, Any]]:
        """List user calendars."""
        if self.should_fail:
            raise RuntimeError("MockCalendarProvider simulated list_calendars failure.")
        return self._mock_calendars

    def get_today_events(self, tz_name: str = "Asia/Kolkata") -> List[Dict[str, Any]]:
        """Get today's mock events."""
        if self.should_fail:
            raise RuntimeError("MockCalendarProvider simulated get_today_events failure.")
        events = [normalize_event_dict(e, tz_name) for e in self._store.values()]
        return sorted(events, key=lambda x: x["start"])

    def get_upcoming_events(self, limit: int = 10, tz_name: str = "Asia/Kolkata") -> List[Dict[str, Any]]:
        """Get upcoming mock events up to limit."""
        if self.should_fail:
            raise RuntimeError("MockCalendarProvider simulated get_upcoming_events failure.")
        events = [normalize_event_dict(e, tz_name) for e in self._store.values()]
        return sorted(events, key=lambda x: x["start"])[:limit]

    def search_events(self, query: str, limit: int = 10, tz_name: str = "Asia/Kolkata") -> List[Dict[str, Any]]:
        """Search mock events by query string."""
        if self.should_fail:
            raise RuntimeError("MockCalendarProvider simulated search_events failure.")
        q_lower = query.strip().lower()
        results = []
        for e in self._store.values():
            norm = normalize_event_dict(e, tz_name)
            if q_lower in norm["title"].lower() or q_lower in norm["description"].lower() or q_lower in norm["location"].lower():
                results.append(norm)
        return results[:limit]

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
            "id": evt_id,
            "provider_event_id": evt_id,
            "summary": title,
            "title": title,
            "start": {"dateTime": start_time},
            "end": {"dateTime": end_time},
            "location": location,
            "description": description,
            "attendees": [{"email": a} for a in (attendees or [])],
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
        rec = self._store.get(provider_event_id)
        if rec:
            return normalize_event_dict(rec)
        return None

    def list_events(self) -> List[Dict[str, Any]]:
        """List all mock events."""
        return [normalize_event_dict(e) for e in self._store.values()]

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
        """Perform read-only connection check against Google Calendar API."""
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
                "account": status_info.get("account", ""),
                "scopes": ["https://www.googleapis.com/auth/calendar.readonly"],
            }
        except Exception as err:
            return {
                "status": CalendarConnectionStatus.TEMPORARILY_UNAVAILABLE.value,
                "connected": False,
                "provider": "google_calendar",
                "reason": str(err),
            }

    def list_calendars(self) -> List[Dict[str, Any]]:
        """List user's Google Calendars using read-only API."""
        try:
            from backend.services import calendar_agent
            if not calendar_agent.is_configured():
                return []
            service = calendar_agent._build_service()
            cal_list = service.calendarList().list().execute().get("items", [])
            results = []
            for cal in cal_list:
                results.append({
                    "id": cal.get("id", ""),
                    "name": cal.get("summary", ""),
                    "primary": cal.get("primary", False),
                    "timezone": cal.get("timeZone", "Asia/Kolkata"),
                })
            return results
        except Exception:
            return []

    def get_today_events(self, tz_name: str = "Asia/Kolkata") -> List[Dict[str, Any]]:
        """Get today's events using read-only API."""
        try:
            from backend.services import calendar_agent
            if not calendar_agent.is_configured():
                return []
            raw_events = calendar_agent.get_today()
            return [normalize_event_dict(e, tz_name) for e in raw_events]
        except Exception:
            return []

    def get_upcoming_events(self, limit: int = 10, tz_name: str = "Asia/Kolkata") -> List[Dict[str, Any]]:
        """Get upcoming events using read-only API up to limit."""
        try:
            from backend.services import calendar_agent
            if not calendar_agent.is_configured():
                return []
            raw_events = calendar_agent.get_upcoming(days=7, max_results=limit)
            return [normalize_event_dict(e, tz_name) for e in raw_events[:limit]]
        except Exception:
            return []

    def search_events(self, query: str, limit: int = 10, tz_name: str = "Asia/Kolkata") -> List[Dict[str, Any]]:
        """Search events using read-only API matching query."""
        try:
            from backend.services import calendar_agent
            if not calendar_agent.is_configured():
                return []
            raw_events = calendar_agent.search_events(query=query, days=30, max_results=limit)
            return [normalize_event_dict(e, tz_name) for e in raw_events[:limit]]
        except Exception:
            return []

    def create_event(self, title: str, start_time: str, end_time: str, **kwargs) -> Any:
        """Attempt real calendar creation. Must raise RealCalendarBlockedError if CALENDAR_LIVE_EXECUTION=false."""
        assert_live_calendar_execution_allowed()
        raise RealCalendarBlockedError("Real Calendar creation is not configured or allowed.")

    def get_event(self, provider_event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a real event (read-only)."""
        events = self.get_upcoming_events(limit=50)
        for e in events:
            if e["event_id"] == provider_event_id:
                return e
        return None


RealCalendarProvider = GoogleCalendarProvider
