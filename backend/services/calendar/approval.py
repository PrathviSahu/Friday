"""Calendar approval token lifecycle & validation module.

Manages single-use, time-limited, version-bound approval tokens for calendar event creation.
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List

from .event import CalendarEventDraft, get_calendar_event_draft, compute_event_hash


@dataclass
class PendingCalendarApproval:
    approval_id: str
    event_id: str
    event_hash: str
    title: str
    start_time: str
    end_time: str
    event_version: int
    created_at: float
    expires_at: float
    consumed_at: Optional[float] = None
    status: str = "PENDING"  # PENDING, EXPIRED, INVALIDATED, CONSUMED

    def is_expired(self, now: Optional[float] = None) -> bool:
        current_time = now if now is not None else time.time()
        return current_time > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "event_id": self.event_id,
            "event_hash": self.event_hash,
            "title": self.title,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "event_version": self.event_version,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "consumed_at": self.consumed_at,
            "status": self.status,
        }


_cal_approval_store: Dict[str, PendingCalendarApproval] = {}
_event_approvals: Dict[str, List[str]] = {}  # event_id -> list of approval_ids


def create_calendar_approval_token(draft: CalendarEventDraft, ttl_seconds: int = 300) -> PendingCalendarApproval:
    """Generate a single-use approval token scoped to a specific event version and hash."""
    actual_ttl = min(ttl_seconds, 300)
    now = time.time()
    expires_at = now + actual_ttl
    approval_id = f"cal_appr_{uuid.uuid4().hex[:12]}"

    approval = PendingCalendarApproval(
        approval_id=approval_id,
        event_id=draft.event_id,
        event_hash=draft.event_hash,
        title=draft.title,
        start_time=draft.start_time,
        end_time=draft.end_time,
        event_version=draft.version,
        created_at=now,
        expires_at=expires_at,
        consumed_at=None,
        status="PENDING",
    )

    _cal_approval_store[approval_id] = approval
    if draft.event_id not in _event_approvals:
        _event_approvals[draft.event_id] = []
    _event_approvals[draft.event_id].append(approval_id)

    return approval


def get_calendar_approval(approval_id: str) -> Optional[PendingCalendarApproval]:
    """Retrieve a calendar approval token by ID."""
    return _cal_approval_store.get(approval_id)


def invalidate_approvals_for_calendar_event(event_id: str, reason: str = "event_modified") -> List[str]:
    """Invalidate all pending approval tokens for an event draft."""
    invalidated_ids = []
    approval_ids = _event_approvals.get(event_id, [])
    for app_id in approval_ids:
        appr = _cal_approval_store.get(app_id)
        if appr and appr.status == "PENDING":
            appr.status = "INVALIDATED"
            invalidated_ids.append(app_id)
    return invalidated_ids


def consume_calendar_approval_token(approval_id: str) -> bool:
    """Mark a calendar approval token as CONSUMED upon successful creation."""
    appr = _cal_approval_store.get(approval_id)
    if appr and appr.status == "PENDING":
        appr.status = "CONSUMED"
        appr.consumed_at = time.time()
        return True
    return False


def validate_calendar_approval(
    approval_id: str,
    event_id: str,
    session_user: str = "Prem",
    now: Optional[float] = None
) -> Tuple[bool, str, Optional[PendingCalendarApproval]]:
    """Validate calendar approval token against all security & verification checks.

    Returns (is_valid, failure_reason, approval_object).
    """
    current_time = now if now is not None else time.time()

    if not approval_id:
        return False, "Missing calendar approval token.", None

    approval = _cal_approval_store.get(approval_id)
    if not approval:
        return False, f"Calendar approval token '{approval_id}' not found.", None

    if approval.is_expired(now=current_time):
        approval.status = "EXPIRED"
        return False, f"Calendar approval token '{approval_id}' has expired (TTL: 5 mins).", approval

    if approval.status == "CONSUMED":
        return False, f"Calendar approval token '{approval_id}' has already been consumed.", approval

    if approval.status == "INVALIDATED":
        return False, "The calendar event changed after the previous approval, so I need a new approval for the revised event.", approval

    if approval.status != "PENDING":
        return False, f"Calendar approval token '{approval_id}' is in invalid state '{approval.status}'.", approval

    draft = get_calendar_event_draft(event_id)
    if not draft:
        return False, f"Calendar event draft '{event_id}' not found.", approval

    if draft.status == "CREATED":
        return False, f"Calendar event '{event_id}' has already been CREATED.", approval

    if draft.event_hash != approval.event_hash:
        approval.status = "INVALIDATED"
        return False, "The calendar event changed after the previous approval, so I need a new approval for the revised event.", approval

    if draft.title != approval.title or draft.version != approval.event_version:
        approval.status = "INVALIDATED"
        return False, "The calendar event changed after the previous approval, so I need a new approval for the revised event.", approval

    if draft.start_time != approval.start_time or draft.end_time != approval.end_time:
        approval.status = "INVALIDATED"
        return False, "The calendar event changed after the previous approval, so I need a new approval for the revised event.", approval

    if not session_user or session_user.lower() not in ("prem", "boss", "owner"):
        return False, f"Unauthorized session user '{session_user}'. Only Prem can authorize event creation.", approval

    return True, "", approval


def clear_calendar_approval_store():
    """Clear in-memory calendar approval store for tests."""
    _cal_approval_store.clear()
    _event_approvals.clear()
