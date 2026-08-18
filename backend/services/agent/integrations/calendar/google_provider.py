"""services/agent/integrations/calendar/google_provider.py — Live Google Calendar Provider.

Wraps existing calendar_agent primitives for real Google Calendar API interactions
when CALENDAR_LIVE_EXECUTION=true and credentials are configured.
"""

import time
import uuid
from typing import List, Optional, Dict, Any

from services.agent.integrations.calendar.provider import (
    CalendarProvider,
    CalendarConnectionStatus,
    CalendarEvent,
    CalendarEventDraft,
    CalendarCreateResult,
    CalendarVerificationResult,
    compute_calendar_content_hash,
)
from services import calendar_agent


class GoogleCalendarProvider(CalendarProvider):
    """Live Google Calendar Provider."""

    def check_connection(self) -> CalendarConnectionStatus:
        if not calendar_agent.is_configured():
            return CalendarConnectionStatus.NOT_CONFIGURED
        try:
            status = calendar_agent.get_status()
            if status.get("connected") and status.get("status") == "authenticated":
                return CalendarConnectionStatus.CONNECTED
            elif status.get("configured"):
                return CalendarConnectionStatus.CREDENTIALS_STORED
            return CalendarConnectionStatus.AUTHENTICATION_FAILED
        except Exception:
            return CalendarConnectionStatus.TEMPORARILY_UNAVAILABLE

    def list_events(self, time_min: Optional[str] = None, time_max: Optional[str] = None, limit: int = 10) -> List[CalendarEvent]:
        try:
            raw_events = calendar_agent.get_upcoming(days=7, max_results=limit)
            results = []
            for item in raw_events:
                results.append(
                    CalendarEvent(
                        id=item.get("id", f"evt-{abs(hash(item.get('summary', ''))) % 100000}"),
                        title=item.get("summary", "Untitled Event"),
                        description=item.get("description"),
                        location=item.get("location"),
                        start_time=item.get("start", {}).get("dateTime", item.get("start", {}).get("date", "")),
                        end_time=item.get("end", {}).get("dateTime", item.get("end", {}).get("date", "")),
                        timezone=item.get("start", {}).get("timeZone", "Asia/Kolkata"),
                        attendees=[a.get("email") for a in item.get("attendees", []) if isinstance(a, dict) and "email" in a],
                        status="confirmed",
                        provider="google_calendar"
                    )
                )
            return results
        except Exception:
            return []

    def search_events(self, query: str, limit: int = 10) -> List[CalendarEvent]:
        try:
            raw_events = calendar_agent.search_events(query, max_results=limit)
            results = []
            for item in raw_events:
                results.append(
                    CalendarEvent(
                        id=item.get("id", f"evt-{abs(hash(item.get('summary', ''))) % 100000}"),
                        title=item.get("summary", "Untitled Event"),
                        description=item.get("description"),
                        location=item.get("location"),
                        start_time=item.get("start", {}).get("dateTime", item.get("start", {}).get("date", "")),
                        end_time=item.get("end", {}).get("dateTime", item.get("end", {}).get("date", "")),
                        timezone=item.get("start", {}).get("timeZone", "Asia/Kolkata"),
                        attendees=[a.get("email") for a in item.get("attendees", []) if isinstance(a, dict) and "email" in a],
                        status="confirmed",
                        provider="google_calendar"
                    )
                )
            return results
        except Exception:
            return []

    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        events = self.list_events(limit=50)
        for e in events:
            if e.id == event_id:
                return e
        return None

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
        raw = calendar_agent.create_draft(summary=title, start=start_time, end=end_time, description=description or "")
        now = time.time()
        atts = attendees or []
        rems = reminders if reminders is not None else [30]
        chash = compute_calendar_content_hash(
            title=title,
            start_time=start_time,
            end_time=end_time,
            timezone=timezone,
            location=location,
            attendees=atts,
            reminders=rems
        )
        return CalendarEventDraft(
            id=raw["id"],
            title=raw["summary"],
            description=raw.get("description"),
            location=location,
            start_time=raw["start"],
            end_time=raw["end"],
            timezone=timezone,
            attendees=atts,
            reminders=rems,
            recurrence=recurrence,
            created_at=raw["created_at"],
            expires_at=raw["expires_at"],
            content_hash=chash,
            status="pending"
        )

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
        raw = calendar_agent.get_draft(draft_id)
        if not raw:
            return None
        new_title = title or raw["summary"]
        new_start = start_time or raw["start"]
        new_end = end_time or raw["end"]
        new_desc = description if description is not None else raw.get("description", "")
        calendar_agent.cancel_draft(draft_id)
        return self.create_draft_event(
            title=new_title,
            start_time=new_start,
            end_time=new_end,
            timezone=timezone or "Asia/Kolkata",
            description=new_desc,
            location=location,
            attendees=attendees,
            reminders=reminders
        )

    def cancel_draft_event(self, draft_id: str) -> bool:
        return calendar_agent.cancel_draft(draft_id)

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
        try:
            if not draft_id:
                draft = self.create_draft_event(
                    title=title,
                    start_time=start_time,
                    end_time=end_time,
                    timezone=timezone,
                    description=description,
                    location=location,
                    attendees=attendees,
                    reminders=reminders
                )
                draft_id = draft.id
            raw_created = calendar_agent.create_event(draft_id)
            event_id = raw_created.get("id") or f"evt-gcal-{uuid.uuid4().hex[:8]}"
            return CalendarCreateResult(
                success=True,
                event_id=event_id,
                title=title,
                start_time=start_time,
                end_time=end_time,
                timezone=timezone,
                attendees=attendees or [],
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                provider="google_calendar",
                status="created"
            )
        except Exception as e:
            return CalendarCreateResult(
                success=False,
                title=title,
                start_time=start_time,
                end_time=end_time,
                timezone=timezone,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                provider="google_calendar",
                status="failed",
                error=str(e)
            )

    def verify_event(self, provider_event_id: str) -> CalendarVerificationResult:
        try:
            evt = self.get_event(provider_event_id)
            if evt:
                return CalendarVerificationResult(
                    verified=True,
                    provider_event_id=provider_event_id,
                    status="verified",
                    note=f"Google Calendar event '{evt.title}' verified."
                )
            return CalendarVerificationResult(
                verified=False,
                provider_event_id=provider_event_id,
                status="not_found",
                note="Event ID not confirmed by Google Calendar API."
            )
        except Exception as e:
            return CalendarVerificationResult(
                verified=False,
                provider_event_id=provider_event_id,
                status="error",
                note=str(e)
            )

    def delete_event(self, event_id: str) -> bool:
        # Autonomous deletion is strictly blocked
        return False
