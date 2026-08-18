"""Calendar Event Draft & Hash Engine (Level 1 PREPARATION ONLY).

Drafts calendar events without creating them in external calendar providers.
Draft != Create Invariant is strictly enforced.
Draft TTL: 15 minutes (900 seconds).
"""

import hashlib
import uuid
import re
from datetime import datetime, timezone, timedelta
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


class CalendarClarificationRequired(Exception):
    """Raised when required event parameters are missing or ambiguous."""
    pass


@dataclass
class CalendarEventDraft:
    event_id: str
    title: str
    start_time: str  # ISO format string or YYYY-MM-DD HH:MM
    end_time: str    # ISO format string or YYYY-MM-DD HH:MM
    timezone: str = "Asia/Kolkata"
    location: str = ""
    description: str = ""
    attendees: List[str] = field(default_factory=list)
    reminders: List[Dict[str, Any]] = field(default_factory=list)
    recurrence: Optional[Dict[str, Any]] = None
    is_all_day: bool = False
    version: int = 1
    event_hash: str = ""
    status: str = "PENDING"  # PENDING, MODIFIED, APPROVED, CREATED, CANCELLED
    created_at: str = ""
    updated_at: str = ""
    expires_at: str = ""

    @property
    def draft_id(self) -> str:
        return self.event_id

    def is_expired(self) -> bool:
        """Return True if the draft TTL (15 mins) has elapsed."""
        if not self.expires_at:
            return False
        try:
            exp_dt = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) > exp_dt
        except Exception:
            return False

    def format_preview(self) -> str:
        """Format clean preview for user displaying all draft fields."""
        atts = ", ".join(self.attendees) if self.attendees else "None"
        rems = ", ".join(f"{r.get('minutes', 30)} min before" for r in self.reminders) if self.reminders else "None"
        rec = str(self.recurrence) if self.recurrence else "None"

        return (
            f"=== CALENDAR EVENT PREVIEW (DRAFT v{self.version}) ===\n"
            f"TITLE: {self.title}\n"
            f"START: {self.start_time}\n"
            f"END: {self.end_time}\n"
            f"TIMEZONE: {self.timezone}\n"
            f"LOCATION: {self.location or 'Not specified'}\n"
            f"ATTENDEES: {atts}\n"
            f"REMINDERS: {rems}\n"
            f"RECURRENCE: {rec}\n"
            f"ALL-DAY: {'Yes' if self.is_all_day else 'No'}\n"
            f"STATUS: {self.status}\n"
            f"EVENT HASH: {self.event_hash[:16]}...\n"
            f"\nNothing has been added to your calendar yet."
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "draft_id": self.event_id,
            "event_id": self.event_id,
            "title": self.title,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "timezone": self.timezone,
            "location": self.location,
            "description": self.description,
            "attendees": self.attendees,
            "reminders": self.reminders,
            "recurrence": self.recurrence,
            "is_all_day": self.is_all_day,
            "version": self.version,
            "event_hash": self.event_hash,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "preview": self.format_preview(),
        }


def compute_event_hash(
    title: str,
    start_time: str,
    end_time: str,
    location: str = "",
    description: str = "",
    attendees: Optional[List[str]] = None,
    tz_name: str = "Asia/Kolkata",
    reminders: Optional[List[Dict[str, Any]]] = None,
    recurrence: Optional[Dict[str, Any]] = None,
) -> str:
    """Compute SHA256 canonical hash for calendar event content."""
    c_title = title.strip()
    c_start = start_time.strip()
    c_end = end_time.strip()
    c_loc = location.strip()
    c_desc = description.strip()
    c_tz = tz_name.strip()

    c_attendees = ""
    if attendees:
        c_attendees = "|".join(sorted(a.strip().lower() for a in attendees if a.strip()))

    c_reminders = str(reminders or [])
    c_rec = str(recurrence or {})

    payload = f"{c_title}\n{c_start}\n{c_end}\n{c_tz}\n{c_loc}\n{c_desc}\n{c_attendees}\n{c_reminders}\n{c_rec}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def detect_calendar_prompt_injection(text: str):
    """Check text for known prompt injection attack patterns."""
    if not text:
        return
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            raise CalendarPromptInjectionError(
                f"SECURITY GUARD: Prompt injection pattern detected matching '{pattern}'."
            )


def validate_event_times(start_time: str, end_time: str, is_all_day: bool = False):
    """Validate event start and end time format and relationship."""
    if not start_time or not start_time.strip():
        raise CalendarEventValidationError("Start time cannot be empty.")
    if not end_time or not end_time.strip():
        raise CalendarEventValidationError("End time cannot be empty.")

    if is_all_day:
        if len(start_time) == 10 and len(end_time) == 10:
            if end_time < start_time:
                raise CalendarEventValidationError("All-day event end date cannot precede start date.")
            return

    try:
        s_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        e_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        if e_dt <= s_dt:
            raise CalendarEventValidationError("Event end time must be strictly after start time.")
    except ValueError:
        if start_time >= end_time:
            raise CalendarEventValidationError("Event end time must be after start time.")


def validate_attendees(attendees: Optional[List[str]] = None) -> List[str]:
    """Validate email address format for all attendees."""
    if not attendees:
        return []
    valid = []
    email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    for att in attendees:
        att_str = att.strip()
        if not att_str:
            continue
        if "@" in att_str:
            if not re.match(email_regex, att_str):
                raise CalendarClarificationRequired(f"Attendee '{att_str}' is an invalid email address. Please clarify email.")
            valid.append(att_str.lower())
        else:
            raise CalendarClarificationRequired(f"Cannot identify email for attendee '{att_str}'. What is their email address?")
    return valid


_event_draft_store: Dict[str, CalendarEventDraft] = {}


def clear_calendar_draft_store():
    """Clear draft store for testing."""
    _event_draft_store.clear()


def draft_calendar_event(
    title: str,
    start_time: str,
    end_time: str,
    timezone_name: str = "Asia/Kolkata",
    location: str = "",
    description: str = "",
    attendees: Optional[List[str]] = None,
    reminders: Optional[List[Dict[str, Any]]] = None,
    recurrence: Optional[Dict[str, Any]] = None,
    is_all_day: bool = False,
) -> CalendarEventDraft:
    """Level 1 PREPARATION: Create a calendar event draft with 15-minute TTL.

    CRITICAL INVARIANT: This function ONLY creates an event draft. It CANNOT create real calendar events.
    """
    if not title or not title.strip():
        raise CalendarEventValidationError("Calendar event title cannot be empty.")

    detect_calendar_prompt_injection(title)
    detect_calendar_prompt_injection(description)
    validate_event_times(start_time, end_time, is_all_day)
    val_attendees = validate_attendees(attendees)

    now_utc = datetime.now(timezone.utc)
    exp_utc = now_utc + timedelta(seconds=900)  # 15 minutes TTL

    created_iso = now_utc.isoformat()
    expires_iso = exp_utc.isoformat()

    event_id = f"evt_draft_{uuid.uuid4().hex[:12]}"
    event_hash = compute_event_hash(
        title, start_time, end_time, location, description, val_attendees, timezone_name, reminders, recurrence
    )

    draft = CalendarEventDraft(
        event_id=event_id,
        title=title.strip(),
        start_time=start_time.strip(),
        end_time=end_time.strip(),
        timezone=timezone_name.strip(),
        location=location.strip(),
        description=description.strip(),
        attendees=val_attendees,
        reminders=reminders or [],
        recurrence=recurrence,
        is_all_day=is_all_day,
        version=1,
        event_hash=event_hash,
        status="PENDING",
        created_at=created_iso,
        updated_at=created_iso,
        expires_at=expires_iso,
    )

    _event_draft_store[event_id] = draft
    return draft


def get_calendar_event_draft(event_id: str) -> Optional[CalendarEventDraft]:
    """Retrieve an event draft by ID, checking expiration."""
    draft = _event_draft_store.get(event_id)
    if draft and draft.is_expired():
        draft.status = "EXPIRED"
    return draft


def update_calendar_event_draft(
    event_id: str,
    new_title: Optional[str] = None,
    new_start_time: Optional[str] = None,
    new_end_time: Optional[str] = None,
    new_timezone: Optional[str] = None,
    new_location: Optional[str] = None,
    new_description: Optional[str] = None,
    new_attendees: Optional[List[str]] = None,
    new_reminders: Optional[List[Dict[str, Any]]] = None,
    new_recurrence: Optional[Dict[str, Any]] = None,
    new_is_all_day: Optional[bool] = None,
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
    updated_tz = new_timezone.strip() if new_timezone is not None else draft.timezone
    updated_location = new_location.strip() if new_location is not None else draft.location
    updated_description = new_description.strip() if new_description is not None else draft.description
    updated_attendees = validate_attendees(new_attendees) if new_attendees is not None else draft.attendees
    updated_reminders = new_reminders if new_reminders is not None else draft.reminders
    updated_recurrence = new_recurrence if new_recurrence is not None else draft.recurrence
    updated_all_day = new_is_all_day if new_is_all_day is not None else draft.is_all_day

    if not updated_title:
        raise CalendarEventValidationError("Calendar event title cannot be empty.")

    detect_calendar_prompt_injection(updated_title)
    detect_calendar_prompt_injection(updated_description)
    validate_event_times(updated_start, updated_end, updated_all_day)

    now_utc = datetime.now(timezone.utc)
    exp_utc = now_utc + timedelta(seconds=900)  # Reset 15 mins TTL on edit

    new_hash = compute_event_hash(
        updated_title, updated_start, updated_end, updated_location, updated_description, updated_attendees, updated_tz, updated_reminders, updated_recurrence
    )

    draft.title = updated_title
    draft.start_time = updated_start
    draft.end_time = updated_end
    draft.timezone = updated_tz
    draft.location = updated_location
    draft.description = updated_description
    draft.attendees = updated_attendees
    draft.reminders = updated_reminders
    draft.recurrence = updated_recurrence
    draft.is_all_day = updated_all_day
    draft.version += 1
    draft.event_hash = new_hash
    draft.status = "MODIFIED"
    draft.updated_at = now_utc.isoformat()
    draft.expires_at = exp_utc.isoformat()

    return draft
