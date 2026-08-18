"""Production Dry-Run Execution Test for Calendar Approval & Event Creation.

Verifies end-to-end dry-run flow against MockCalendarProvider with CALENDAR_LIVE_EXECUTION=false.
"""

import pytest
from backend.services.calendar import (
    CALENDAR_LIVE_EXECUTION,
    CALENDAR_STATUS,
    prepare_calendar_event,
    create_calendar_event_with_approval,
    get_default_mock_calendar_provider,
    calendar_audit_logger,
)
from backend.services.calendar.event import clear_calendar_draft_store
from backend.services.calendar.approval import clear_calendar_approval_store


@pytest.fixture(autouse=True)
def reset_calendar_stores():
    """Reset stores prior to dry-run test."""
    clear_calendar_draft_store()
    clear_calendar_approval_store()
    get_default_mock_calendar_provider().clear()
    calendar_audit_logger.clear()


def test_calendar_production_dry_run_workflow():
    """Execute complete Production Dry-Run for Calendar in Safe Mode (CALENDAR_LIVE_EXECUTION=False)."""

    # Assert environment safety state
    assert CALENDAR_LIVE_EXECUTION is False, "CALENDAR_LIVE_EXECUTION must be false for production dry-run."
    assert CALENDAR_STATUS == "MOCK_MODE", "Calendar status must be MOCK_MODE."

    # 1. Create Calendar Event Draft & Generate Approval Token
    title = "Q4 Product Strategy Review"
    start_time = "2026-08-25T14:00:00Z"
    end_time = "2026-08-25T15:30:00Z"
    location = "Executive Boardroom & Google Meet"
    description = "Discussing Q4 roadmap and feature priorities."
    attendees = ["sarah.vp@techcorp.io", "prem@techcorp.io"]

    prep = prepare_calendar_event(
        title=title,
        start_time=start_time,
        end_time=end_time,
        location=location,
        description=description,
        attendees=attendees,
    )

    assert prep["status"] == "EVENT_DRAFT_PREPARED"
    assert prep["mode"] == "DRY-RUN / MOCK CALENDAR PROVIDER"
    event_id = prep["event_draft"]["event_id"]
    approval_id = prep["approval_token"]["approval_id"]

    # 2. Explicit User Approval & Controlled Creation
    confirmation_text = "Yes, create it."
    create_res = create_calendar_event_with_approval(
        approval_id=approval_id,
        event_id=event_id,
        user_confirmation_text=confirmation_text,
        session_user="Prem",
    )

    # 3. Assert Creation & Independent Verification
    assert create_res["success"] is True
    assert create_res["status"] == "SUCCESS"
    assert create_res["message"] == "Calendar event created and verified."
    assert create_res["mode"] == "DRY-RUN / MOCK CALENDAR PROVIDER"
    assert create_res["verified"] is True
    assert create_res["real_event_created"] is False
    provider_event_id = create_res["provider_event_id"]

    # 4. Independent Verification check against mock provider store
    mock_provider = get_default_mock_calendar_provider()
    msg_record = mock_provider.get_event(provider_event_id)
    assert msg_record is not None
    assert msg_record["title"] == title
    assert msg_record["start_time"] == start_time
    assert msg_record["end_time"] == end_time
    assert msg_record["status"] == "RECORDED_CREATED"

    # 5. Audit Log verification
    logs = calendar_audit_logger.get_logs()
    assert len(logs) >= 2
    created_logs = [l for l in logs if l["action"] == "CALENDAR_EVENT_CREATED_AND_VERIFIED"]
    assert len(created_logs) == 1
    assert created_logs[0]["provider_event_id"] == provider_event_id

    # 6. Duplicate Attempt Blocked (Idempotency)
    duplicate_res = create_calendar_event_with_approval(
        approval_id=approval_id,
        event_id=event_id,
        user_confirmation_text=confirmation_text,
        session_user="Prem",
    )
    assert duplicate_res["success"] is False
    assert duplicate_res["message"] == "The calendar event was already created."
    assert len(mock_provider._store) == 1
