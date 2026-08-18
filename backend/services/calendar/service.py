"""High-level Calendar Service Orchestrator for FRIDAY.

Enforces Calendar pipeline:
READ -> DRAFT -> PREVIEW -> EXPLICIT APPROVAL -> TOKEN VALIDATION -> PERMISSION CHECK ->
IDEMPOTENCY CHECK -> MOCK PROVIDER DISPATCH -> EVENT ID -> INDEPENDENT VERIFICATION ->
AUDIT LOG -> SUCCESS.
"""

from typing import Dict, Any, Optional, List

from .config import CALENDAR_LIVE_EXECUTION, is_live_calendar_execution_enabled, RealCalendarBlockedError
from .event import (
    CalendarEventDraft,
    draft_calendar_event,
    get_calendar_event_draft,
    update_calendar_event_draft,
    CalendarEventValidationError,
    CalendarPromptInjectionError,
)
from .approval import (
    PendingCalendarApproval,
    create_calendar_approval_token,
    get_calendar_approval,
    invalidate_approvals_for_calendar_event,
    consume_calendar_approval_token,
    validate_calendar_approval,
)
from .parser import evaluate_calendar_confirmation, is_explicit_calendar_approval
from .provider import (
    BaseCalendarProvider,
    MockCalendarProvider,
    RealCalendarProvider,
    GoogleCalendarProvider,
    MockCalendarResult,
)
from .verifier import IndependentCalendarVerifier, IndependentCalendarVerificationError
from .audit import calendar_audit_logger


_default_mock_calendar_provider = MockCalendarProvider()


def get_default_mock_calendar_provider() -> MockCalendarProvider:
    """Return the default mock calendar provider instance."""
    return _default_mock_calendar_provider


def check_calendar_connection(provider: Optional[Any] = None) -> Dict[str, Any]:
    """Perform read-only connection check against the active or passed calendar provider."""
    eff_provider = provider if provider is not None else _default_mock_calendar_provider
    res = eff_provider.check_connection()

    calendar_audit_logger.log_event(
        action="CALENDAR_CONNECTION_CHECK",
        result=f"STATUS_{res.get('status')}",
    )

    return res


def list_calendars(provider: Optional[Any] = None) -> List[Dict[str, Any]]:
    """List user's calendars using read-only provider API."""
    eff_provider = provider if provider is not None else _default_mock_calendar_provider
    cals = eff_provider.list_calendars()

    calendar_audit_logger.log_event(
        action="CALENDAR_LIST_CALENDARS",
        result=f"COUNT_{len(cals)}",
    )

    return cals


def get_today_events(provider: Optional[Any] = None, tz_name: str = "Asia/Kolkata") -> List[Dict[str, Any]]:
    """Retrieve today's calendar events using read-only provider API."""
    eff_provider = provider if provider is not None else _default_mock_calendar_provider
    events = eff_provider.get_today_events(tz_name=tz_name)

    calendar_audit_logger.log_event(
        action="CALENDAR_GET_TODAY",
        result=f"COUNT_{len(events)}",
    )

    return events


def get_upcoming_events(limit: int = 10, provider: Optional[Any] = None, tz_name: str = "Asia/Kolkata") -> List[Dict[str, Any]]:
    """Retrieve upcoming calendar events up to default limit of 10."""
    eff_provider = provider if provider is not None else _default_mock_calendar_provider
    events = eff_provider.get_upcoming_events(limit=limit, tz_name=tz_name)

    calendar_audit_logger.log_event(
        action="CALENDAR_GET_UPCOMING",
        result=f"COUNT_{len(events)}",
    )

    return events


def search_calendar_events(query: str, limit: int = 10, provider: Optional[Any] = None, tz_name: str = "Asia/Kolkata") -> List[Dict[str, Any]]:
    """Search calendar events matching query string up to default limit of 10."""
    eff_provider = provider if provider is not None else _default_mock_calendar_provider
    if not query or not query.strip():
        return []

    events = eff_provider.search_events(query=query.strip(), limit=limit, tz_name=tz_name)

    calendar_audit_logger.log_event(
        action="CALENDAR_SEARCH",
        result=f"QUERY_{query.strip()}_COUNT_{len(events)}",
    )

    return events


def read_calendar_events(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    provider: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """Read calendar events from provider."""
    eff_provider = provider if provider is not None else _default_mock_calendar_provider
    events = eff_provider.list_events()

    calendar_audit_logger.log_event(
        action="CALENDAR_READ",
        result=f"READ_{len(events)}_EVENTS",
    )

    return events


def prepare_calendar_event(
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
    ttl_seconds: int = 300,
) -> Dict[str, Any]:
    """Level 1 PREPARATION: Prepare calendar event draft and issue single-use approval token.

    Draft != Create Invariant: This function CANNOT create real calendar events.
    """
    draft = draft_calendar_event(
        title=title,
        start_time=start_time,
        end_time=end_time,
        timezone_name=timezone_name,
        location=location,
        description=description,
        attendees=attendees,
        reminders=reminders,
        recurrence=recurrence,
        is_all_day=is_all_day,
    )
    approval = create_calendar_approval_token(draft, ttl_seconds=ttl_seconds)

    calendar_audit_logger.log_event(
        action="EVENT_DRAFT_CREATED",
        event_id=draft.event_id,
        approval_id=approval.approval_id,
        event_hash=draft.event_hash,
        title=draft.title,
        result="DRAFT_AND_APPROVAL_PREPARED",
    )

    return {
        "status": "EVENT_DRAFT_PREPARED",
        "message": "Calendar event draft prepared. Requires explicit user approval to create event.",
        "event_draft": draft.to_dict(),
        "approval_token": approval.to_dict(),
        "mode": "DRY-RUN / MOCK CALENDAR PROVIDER" if not is_live_calendar_execution_enabled() else "LIVE",
    }



def edit_calendar_event_draft(
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
    ttl_seconds: int = 300,
) -> Dict[str, Any]:
    """Modify an existing calendar event draft, increment version, update hash, and invalidate old approvals."""
    # 1. Invalidate old approval tokens
    invalidated_token_ids = invalidate_approvals_for_calendar_event(event_id, reason="event_modified")

    # 2. Update event draft
    updated_draft = update_calendar_event_draft(
        event_id=event_id,
        new_title=new_title,
        new_start_time=new_start_time,
        new_end_time=new_end_time,
        new_timezone=new_timezone,
        new_location=new_location,
        new_description=new_description,
        new_attendees=new_attendees,
        new_reminders=new_reminders,
        new_recurrence=new_recurrence,
        new_is_all_day=new_is_all_day,
    )


    # 3. Create fresh approval token for revised version
    fresh_approval = create_calendar_approval_token(updated_draft, ttl_seconds=ttl_seconds)

    calendar_audit_logger.log_event(
        action="EVENT_DRAFT_MODIFIED",
        event_id=updated_draft.event_id,
        approval_id=fresh_approval.approval_id,
        event_hash=updated_draft.event_hash,
        title=updated_draft.title,
        result=f"EVENT_MODIFIED_V{updated_draft.version}_OLD_APPROVALS_INVALIDATED",
    )

    return {
        "status": "EVENT_DRAFT_MODIFIED",
        "event_draft": updated_draft.to_dict(),
        "invalidated_approval_ids": invalidated_token_ids,
        "fresh_approval_token": fresh_approval.to_dict(),
        "preview": {
            "title": updated_draft.title,
            "start_time": updated_draft.start_time,
            "end_time": updated_draft.end_time,
            "location": updated_draft.location,
            "description": updated_draft.description,
            "attendees": updated_draft.attendees,
            "version": updated_draft.version,
            "event_hash": updated_draft.event_hash,
        },
    }


def create_calendar_event_with_approval(
    approval_id: str,
    event_id: str,
    user_confirmation_text: str,
    session_user: str = "Prem",
    now: Optional[float] = None,
    provider: Optional[Any] = None,
    simulate_verification_failure: bool = False,
    attempt_real_calendar: bool = False,
) -> Dict[str, Any]:
    """Execute Controlled Calendar Event Creation with Explicit Approval and Verification."""

    effective_provider = provider if provider is not None else _default_mock_calendar_provider

    # Safety Guard check
    if attempt_real_calendar or isinstance(effective_provider, RealCalendarProvider):
        if not is_live_calendar_execution_enabled():
            calendar_audit_logger.log_event(
                action="REAL_CALENDAR_BLOCKED",
                event_id=event_id,
                approval_id=approval_id,
                result="BLOCKED_BY_SAFETY_GUARD",
            )
            raise RealCalendarBlockedError(
                "SAFETY GUARD ACTIVE: Real Calendar creation is strictly forbidden when CALENDAR_LIVE_EXECUTION=false."
            )

    # 1. Evaluate User Confirmation Language
    is_confirmed, confirmation_reason = evaluate_calendar_confirmation(user_confirmation_text)

    if not is_confirmed:
        calendar_audit_logger.log_event(
            action="CREATE_REJECTED_LANGUAGE",
            event_id=event_id,
            approval_id=approval_id,
            result=f"REJECTED: {confirmation_reason}",
        )
        return {
            "success": False,
            "status": "REJECTED_LANGUAGE",
            "message": confirmation_reason,
            "real_event_created": False,
        }

    # 2. Validate Approval Token
    is_valid, validation_reason, approval_obj = validate_calendar_approval(
        approval_id=approval_id,
        event_id=event_id,
        session_user=session_user,
        now=now,
    )

    if not is_valid:
        status_code = "VALIDATION_FAILED"
        if approval_obj and approval_obj.status == "INVALIDATED":
            status_code = "EDIT_INVALIDATION"
        elif approval_obj and approval_obj.status == "EXPIRED":
            status_code = "TOKEN_EXPIRED"
        elif approval_obj and approval_obj.status == "CONSUMED":
            status_code = "ALREADY_CREATED"
            validation_reason = "The calendar event was already created."

        calendar_audit_logger.log_event(
            action="CREATE_BLOCKED_VALIDATION",
            event_id=event_id,
            approval_id=approval_id,
            result=f"BLOCKED: {validation_reason}",
        )

        return {
            "success": False,
            "status": status_code,
            "message": validation_reason,
            "real_event_created": False,
        }

    draft = get_calendar_event_draft(event_id)
    if not draft:
        return {
            "success": False,
            "status": "DRAFT_NOT_FOUND",
            "message": f"Calendar event draft '{event_id}' not found.",
            "real_event_created": False,
        }

    # 3. Idempotency Check
    if draft.status == "CREATED":
        calendar_audit_logger.log_event(
            action="CREATE_BLOCKED_IDEMPOTENCY",
            event_id=event_id,
            approval_id=approval_id,
            event_hash=draft.event_hash,
            title=draft.title,
            result="BLOCKED: The calendar event was already created.",
        )
        return {
            "success": False,
            "status": "ALREADY_CREATED",
            "message": "The calendar event was already created.",
            "real_event_created": False,
        }

    # 4. Dispatch via Mock Provider
    try:
        creation_result: MockCalendarResult = effective_provider.create_event(
            title=draft.title,
            start_time=draft.start_time,
            end_time=draft.end_time,
            location=draft.location,
            description=draft.description,
            attendees=draft.attendees,
            event_id=draft.event_id,
            approval_id=approval_id,
            event_hash=draft.event_hash,
        )
    except Exception as exc:
        calendar_audit_logger.log_event(
            action="CREATE_FAILED_PROVIDER",
            event_id=draft.event_id,
            approval_id=approval_id,
            event_hash=draft.event_hash,
            title=draft.title,
            result=f"PROVIDER_ERROR: {str(exc)}",
        )
        return {
            "success": False,
            "status": "PROVIDER_FAILURE",
            "message": f"Calendar provider event creation failed: {str(exc)}",
            "real_event_created": False,
        }

    # 5. Consume Approval Token & Update Draft Status
    consume_calendar_approval_token(approval_id)
    draft.status = "CREATED"

    # 6. Perform Independent Verification
    try:
        verification_data = IndependentCalendarVerifier.verify_event(
            provider=effective_provider,
            provider_event_id=creation_result.provider_event_id,
            expected_title=draft.title,
            expected_start_time=draft.start_time,
            expected_end_time=draft.end_time,
            expected_event_hash=draft.event_hash,
            should_simulate_verification_failure=simulate_verification_failure,
        )
    except IndependentCalendarVerificationError as ver_err:
        calendar_audit_logger.log_event(
            action="VERIFICATION_FAILED",
            event_id=draft.event_id,
            approval_id=approval_id,
            event_hash=draft.event_hash,
            title=draft.title,
            provider_event_id=creation_result.provider_event_id,
            result=f"VERIFICATION_FAILED: {str(ver_err)}",
        )
        return {
            "success": False,
            "status": "VERIFICATION_FAILURE",
            "message": str(ver_err),
            "provider_event_id": creation_result.provider_event_id,
            "real_event_created": False,
        }

    # 7. Audit Log Success Event
    calendar_audit_logger.log_event(
        action="CALENDAR_EVENT_CREATED_AND_VERIFIED",
        event_id=draft.event_id,
        approval_id=approval_id,
        event_hash=draft.event_hash,
        title=draft.title,
        provider_event_id=creation_result.provider_event_id,
        result="SUCCESS",
        verification_result=verification_data,
    )

    return {
        "success": True,
        "status": "SUCCESS",
        "message": "Calendar event created and verified.",
        "provider_event_id": creation_result.provider_event_id,
        "mode": "DRY-RUN / MOCK CALENDAR PROVIDER",
        "verified": True,
        "verification_details": verification_data,
        "real_event_created": False,
    }
