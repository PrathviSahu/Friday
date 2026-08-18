"""services/agent/integrations/calendar/mock_provider.py — Mock Calendar Provider.

Provides an in-memory, deterministic calendar transport for automated testing,
local development, and safe dry-run execution.
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


class MockCalendarProvider(CalendarProvider):
    """Deterministic in-memory calendar provider."""

    def __init__(self, initial_status: CalendarConnectionStatus = CalendarConnectionStatus.CONNECTED):
        self.status = initial_status
        now = time.time()
        self.events: Dict[str, CalendarEvent] = {
            "evt-101": CalendarEvent(
                id="evt-101",
                title="JPMorgan Technical Interview — Full Stack",
                description="Technical evaluation: Java Spring Boot microservices and React performance.",
                location="Google Meet: meet.google.com/abc-jpmc-xyz",
                start_time=time.strftime("%Y-%m-%dT15:00:00", time.localtime(now + 86400)),
                end_time=time.strftime("%Y-%m-%dT16:00:00", time.localtime(now + 90000)),
                timezone="Asia/Kolkata",
                attendees=["sarah.jenkins@jpmorgan.com", "prem@example.com"],
                reminders=[30, 10],
                status="confirmed",
                provider="mock_calendar"
            ),
            "evt-102": CalendarEvent(
                id="evt-102",
                title="ZDL Sprint Planning & Architecture Review",
                description="Bi-weekly engineering sprint review and sub-100ms API optimization sync.",
                location="Conference Room B / Zoom",
                start_time=time.strftime("%Y-%m-%dT11:00:00", time.localtime(now)),
                end_time=time.strftime("%Y-%m-%dT12:00:00", time.localtime(now + 3600)),
                timezone="Asia/Kolkata",
                attendees=["team@zeptodigitallabs.com"],
                reminders=[15],
                status="confirmed",
                provider="mock_calendar"
            ),
        }
        self.drafts: Dict[str, CalendarEventDraft] = {}
        self.created_events: Dict[str, CalendarCreateResult] = {}

    def check_connection(self) -> CalendarConnectionStatus:
        return self.status

    def set_connection_status(self, new_status: CalendarConnectionStatus):
        self.status = new_status

    def list_events(self, time_min: Optional[str] = None, time_max: Optional[str] = None, limit: int = 10) -> List[CalendarEvent]:
        if self.status != CalendarConnectionStatus.CONNECTED:
            return []
        evts = list(self.events.values())
        return sorted(evts, key=lambda x: x.start_time)[:limit]

    def search_events(self, query: str, limit: int = 10) -> List[CalendarEvent]:
        if self.status != CalendarConnectionStatus.CONNECTED:
            return []
        q = query.lower()
        matched = []
        for e in self.events.values():
            if (
                q in e.title.lower()
                or (e.description and q in e.description.lower())
                or (e.location and q in e.location.lower())
                or any(q in att.lower() for att in e.attendees)
            ):
                matched.append(e)
        return sorted(matched, key=lambda x: x.start_time)[:limit]

    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        return self.events.get(event_id)

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
        draft_id = f"draft-cal-{uuid.uuid4().hex[:8]}"
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
        draft = CalendarEventDraft(
            id=draft_id,
            title=title,
            description=description,
            location=location,
            start_time=start_time,
            end_time=end_time,
            timezone=timezone,
            attendees=atts,
            reminders=rems,
            recurrence=recurrence,
            created_at=now,
            expires_at=now + 900,  # 15 min TTL
            content_hash=chash,
            status="pending"
        )
        self.drafts[draft_id] = draft
        return draft

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
        draft = self.drafts.get(draft_id)
        if not draft:
            return None
        if title is not None:
            draft.title = title
        if start_time is not None:
            draft.start_time = start_time
        if end_time is not None:
            draft.end_time = end_time
        if timezone is not None:
            draft.timezone = timezone
        if description is not None:
            draft.description = description
        if location is not None:
            draft.location = location
        if attendees is not None:
            draft.attendees = attendees
        if reminders is not None:
            draft.reminders = reminders
        
        draft.created_at = time.time()
        draft.expires_at = time.time() + 900
        draft.content_hash = compute_calendar_content_hash(
            title=draft.title,
            start_time=draft.start_time,
            end_time=draft.end_time,
            timezone=draft.timezone,
            location=draft.location,
            attendees=draft.attendees,
            reminders=draft.reminders
        )
        return draft

    def cancel_draft_event(self, draft_id: str) -> bool:
        if draft_id in self.drafts:
            self.drafts[draft_id].status = "cancelled"
            return True
        return False

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
        if self.status != CalendarConnectionStatus.CONNECTED:
            return CalendarCreateResult(
                success=False,
                title=title,
                start_time=start_time,
                end_time=end_time,
                timezone=timezone,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                provider="mock_calendar",
                status="failed",
                error="Mock calendar provider not connected."
            )

        event_id = f"evt-mock-{uuid.uuid4().hex[:8]}"
        res = CalendarCreateResult(
            success=True,
            event_id=event_id,
            title=title,
            start_time=start_time,
            end_time=end_time,
            timezone=timezone,
            attendees=attendees or [],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            provider="mock_calendar",
            status="created"
        )
        # Store in provider event store
        self.events[event_id] = CalendarEvent(
            id=event_id,
            title=title,
            description=description,
            location=location,
            start_time=start_time,
            end_time=end_time,
            timezone=timezone,
            attendees=attendees or [],
            reminders=reminders or [30],
            status="confirmed",
            provider="mock_calendar"
        )
        self.created_events[event_id] = res
        if draft_id and draft_id in self.drafts:
            self.drafts[draft_id].status = "created"
        return res

    def verify_event(self, provider_event_id: str) -> CalendarVerificationResult:
        """Independently verifies event existence and state in provider store."""
        if provider_event_id in self.events:
            evt = self.events[provider_event_id]
            return CalendarVerificationResult(
                verified=True,
                provider_event_id=provider_event_id,
                status="verified",
                note=f"Event '{evt.title}' confirmed in provider store."
            )
        return CalendarVerificationResult(
            verified=False,
            provider_event_id=provider_event_id,
            status="not_found",
            note="Event ID not present in provider store."
        )

    def delete_event(self, event_id: str) -> bool:
        # Autonomous deletion is strictly blocked
        return False
