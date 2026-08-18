"""Calendar Event Draft & Hash Engine (Level 1 PREPARATION ONLY).

Drafts calendar events without creating them in external calendar providers.
Draft != Create Invariant is strictly enforced.
"""

import hashlib
import uuid
import re
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"delete\s+(all\s+)?events",
    r"wipe\s+calendar",
    r"bypass\s+approval",
    r"override\s+security",
]


class CalendarEventValidationError(Exception):
    """Raised when calendar event validation fails."""
    pass


class CalendarPromptInjectionError(Exception):
    """Raised when prompt injection is detected in calendar content."""
    pass


@dataclass
class CalendarEventDraft:
    event_id: str
    title: str
    start_time: str  # ISO format string or YYYY-MM-DD HH:MM
    end_time: str    # ISO format string or YYYY-MM-DD HH:MM
    location: str = ""
    description: str = ""
    attendees: List[str] = field(default_factory=list)
    version: int = 1
    event_hash: str = ""
    status: str = "PENDING"  # PENDING, MODIFIED, APPROVED, CREATED, CANCELLED
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "location": self.location,
            "description": self.description,
            "attendees": self.attendees,
            "version": self.version,
            "event_hash": self.event_hash,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def compute_event_hash(
    title: str,
    start_time: str,
    end_time: str,
    location: str = "",
    description: str = "",
    attendees: Optional[List[str]] = None
) -> str:
    """Compute SHA256 canonical hash for calendar event content."""
    c_title = title.strip()
    c_start = start_time.strip()
    c_end = end_time.strip()
    c_loc = location.strip()
    c_desc = description.strip()

    c_attendees = ""
    if attendees:
        c_attendees = "|".join(sorted(a.strip().lower() for a in attendees if a.strip()))

    payload = f"{c_title}\n{c_start}\n{c_end}\n{c_loc}\n{c_desc}\n{c_attendees}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def detect_calendar_prompt_injection(text: str):
    """Check text for known prompt injection attack patterns."""
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            raise CalendarPromptInjectionError(
                f"SECURITY GUARD: Prompt injection pattern detected matching '{pattern}'."
            )


def validate_event_times(start_time: str, end_time: str):
    """Validate event start and end time format and relationship."""
    if not start_time or not start_time.strip():
        raise CalendarEventValidationError("Start time cannot be empty.")
    if not end_time or not end_time.strip():
        raise CalendarEventValidationError("End time cannot be empty.")

    # Try parsing ISO or standard timestamps
    try:
        s_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        e_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        if e_dt <= s_dt:
            raise CalendarEventValidationError("Event end time must be strictly after start time.")
    except ValueError:
        # Fallback simple string check if not strict ISO
        if start_time >= end_time:
            raise CalendarEventValidationError("Event end time must be after start time.")


_event_draft_store: Dict[str, CalendarEventDraft] = {}


def draft_calendar_event(
    title: str,
    start_time: str,
    end_time: str,
    location: str = "",
    description: str = "",
    attendees: Optional[List[str]] = None
) -> CalendarEventDraft:
    """Level 1 PREPARATION: Create a calendar event draft.

    CRITICAL INVARIANT: This function ONLY creates an event draft. It CANNOT create real calendar events.
    """
    if not title or not title.strip():
        raise CalendarEventValidationError("Calendar event title cannot be empty.")

    detect_calendar_prompt_injection(title)
    detect_calendar_prompt_injection(description)
    validate_event_times(start_time, end_time)

    now_iso = datetime.now(timezone.utc).isoformat()
    event_id = f"evt_draft_{uuid.uuid4().hex[:12]}"
    event_hash = compute_event_hash(title, start_time, end_time, location, description, attendees)

    draft = CalendarEventDraft(
        event_id=event_id,
        title=title.strip(),
        start_time=start_time.strip(),
        end_time=end_time.strip(),
        location=location.strip(),
        description=description.strip(),
        attendees=attendees or [],
        version=1,
        event_hash=event_hash,
        status="PENDING",
        created_at=now_iso,
        updated_at=now_iso,
    )

    _event_draft_store[event_id] = draft
    return draft


def get_calendar_event_draft(event_id: str) -> Optional[CalendarEventDraft]:
    """Retrieve an event draft by ID."""
    return _event_draft_store.get(event_id)


def update_calendar_event_draft(
    event_id: str,
    new_title: Optional[str] = None,
    new_start_time: Optional[str] = None,
    new_end_time: Optional[str] = None,
    new_location: Optional[str] = None,
    new_description: Optional[str] = None,
    new_attendees: Optional[List[str]] = None,
) -> CalendarEventDraft:
    """Update an existing event draft, incrementing version and recomputing event_hash."""
    draft = _event_draft_store.get(event_id)
    if not draft:
        raise CalendarEventValidationError(f"Calendar event draft '{event_id}' not found.")

    if draft.status == "CREATED":
        raise CalendarEventValidationError(f"Cannot modify calendar event '{event_id}' as it has already been CREATED.")

    updated_title = new_title.strip() if new_title is not None else draft.title
    updated_start = new_start_time.strip() if new_start_time is not None else draft.start_time
    updated_end = new_end_time.strip() if new_end_time is not None else draft.end_time
    updated_location = new_location.strip() if new_location is not None else draft.location
    updated_description = new_description.strip() if new_description is not None else draft.description
    updated_attendees = new_attendees if new_attendees is not None else draft.attendees

    if not updated_title:
        raise CalendarEventValidationError("Calendar event title cannot be empty.")

    detect_calendar_prompt_injection(updated_title)
    detect_calendar_prompt_injection(updated_description)
    validate_event_times(updated_start, updated_end)

    now_iso = datetime.now(timezone.utc).isoformat()
    new_hash = compute_event_hash(
        updated_title, updated_start, updated_end, updated_location, updated_description, updated_attendees
    )

    draft.title = updated_title
    draft.start_time = updated_start
    draft.end_time = updated_end
    draft.location = updated_location
    draft.description = updated_description
    draft.attendees = updated_attendees
    draft.version += 1
    draft.event_hash = new_hash
    draft.status = "MODIFIED"
    draft.updated_at = now_iso

    return draft


def clear_calendar_draft_store():
    """Clear in-memory event draft store for tests."""
    _event_draft_store.clear()
