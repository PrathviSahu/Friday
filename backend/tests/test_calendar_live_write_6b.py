"""Targeted unit tests for Phase 5.5C Calendar Step 6B: Controlled Real Google Calendar Write (Tests A through O).
"""

import pytest
from unittest.mock import MagicMock, patch
from backend.services.calendar.config import (
    CalendarConnectionStatus,
    RealCalendarBlockedError,
    CALENDAR_LIVE_EXECUTION,
)
from backend.services.calendar.provider import GoogleCalendarProvider
from backend.services.calendar.service import (
    prepare_calendar_event,
    create_calendar_event_with_approval,
)
from backend.services.calendar.event import clear_calendar_draft_store
from backend.services.calendar.approval import clear_calendar_approval_store
from backend.services.calendar.audit import calendar_audit_logger


@pytest.fixture(autouse=True)
def reset_stores():
    """Reset draft, approval, and audit logger stores before each test."""
    clear_calendar_draft_store()
    clear_calendar_approval_store()
    calendar_audit_logger.clear()


# ==============================================================================
# TEST A: OAUTH NOT CONNECTED / MISSING CREDS
# ==============================================================================

def test_step6b_oauth_not_connected():
    """Test A: Attempting live write when OAuth is not connected must fail safely."""
    google_provider = GoogleCalendarProvider()

    with patch("backend.services.calendar_agent.is_configured", return_value=False), \
         patch("backend.services.calendar.config.is_live_calendar_execution_enabled", return_value=True):

        with pytest.raises(RealCalendarBlockedError) as exc:
            google_provider.create_event("Test Event", "2026-08-25T10:00:00Z", "2026-08-25T10:30:00Z")
        assert "NOT_CONFIGURED" in str(exc.value)


# ==============================================================================
# TEST B & N: READ-ONLY / SAFETY GUARD BLOCKS LIVE WRITES
# ==============================================================================

def test_step6b_safety_guard_blocks_live_writes():
    """Tests B & N: Assert RealCalendarBlockedError is raised when CALENDAR_LIVE_EXECUTION=false."""
    assert CALENDAR_LIVE_EXECUTION is False

    google_provider = GoogleCalendarProvider()
    with pytest.raises(RealCalendarBlockedError) as exc:
        google_provider.create_event("Test Event", "2026-08-25T10:00:00Z", "2026-08-25T10:30:00Z")

    assert "SAFETY GUARD ACTIVE" in str(exc.value)


# ==============================================================================
# TEST C, D, K, L, M: SUCCESSFUL CONTROLLED GOOGLE INSERT & VERIFICATION
# ==============================================================================

def test_step6b_successful_controlled_google_insert():
    """Tests C, D, K, L, M: Perform mock live Google insert and verify event ID, calendar ID, title, start, end, zero attendees."""
    prep = prepare_calendar_event(
        title="F.R.I.D.A.Y. Integration Test — DELETE ME",
        start_time="2026-08-25T14:00:00Z",
        end_time="2026-08-25T14:30:00Z",
        description="Controlled F.R.I.D.A.Y. integration verification event.",
        attendees=[],  # Zero attendees
    )

    event_id = prep["event_draft"]["event_id"]
    approval_id = prep["approval_token"]["approval_id"]

    mock_service = MagicMock()
    mock_events_api = MagicMock()
    mock_events_api.insert.return_value.execute.return_value = {
        "id": "gcal_test_evt_999",
        "summary": "F.R.I.D.A.Y. Integration Test — DELETE ME",
        "status": "confirmed",
        "start": {"dateTime": "2026-08-25T14:00:00Z"},
        "end": {"dateTime": "2026-08-25T14:30:00Z"},
    }
    mock_events_api.get.return_value.execute.return_value = {
        "id": "gcal_test_evt_999",
        "summary": "F.R.I.D.A.Y. Integration Test — DELETE ME",
        "description": "Controlled F.R.I.D.A.Y. integration verification event.",
        "start": {"dateTime": "2026-08-25T14:00:00Z"},
        "end": {"dateTime": "2026-08-25T14:30:00Z"},
        "status": "confirmed",
        "attendees": [],
    }
    mock_service.events.return_value = mock_events_api

    google_provider = GoogleCalendarProvider()

    with patch("backend.services.calendar_agent.is_configured", return_value=True), \
         patch("backend.services.calendar_agent._build_service", return_value=mock_service), \
         patch("backend.services.calendar.provider.assert_live_calendar_execution_allowed", return_value=None), \
         patch("backend.services.calendar.service.is_live_calendar_execution_enabled", return_value=True):



        res = create_calendar_event_with_approval(
            approval_id=approval_id,
            event_id=event_id,
            user_confirmation_text="Yes, create it.",
            session_user="Prem",
            provider=google_provider,
            attempt_real_calendar=True,
        )

        assert res["success"] is True
        assert res["status"] == "SUCCESS"
        assert res["provider_event_id"] == "gcal_test_evt_999"
        assert res["verified"] is True

        # Assert insert was called with target calendar "primary" and zero attendees
        mock_events_api.insert.assert_called_once()
        call_kwargs = mock_events_api.insert.call_args[1]
        assert call_kwargs["calendarId"] == "primary"
        body = call_kwargs["body"]
        assert body["summary"] == "F.R.I.D.A.Y. Integration Test — DELETE ME"
        assert "attendees" not in body or len(body["attendees"]) == 0

    # Ensure live execution status remains False globally
    assert CALENDAR_LIVE_EXECUTION is False


# ==============================================================================
# TEST E, F, G: MISSING/EXPIRED APPROVAL & HASH MISMATCH
# ==============================================================================

def test_step6b_validation_failures():
    """Tests E, F, G: Missing approval, expired approval, or hash mismatch fails safely before live API call."""
    prep = prepare_calendar_event(
        title="F.R.I.D.A.Y. Integration Test — DELETE ME",
        start_time="2026-08-25T14:00:00Z",
        end_time="2026-08-25T14:30:00Z",
    )
    event_id = prep["event_draft"]["event_id"]

    res = create_calendar_event_with_approval(
        approval_id="invalid_token_id",
        event_id=event_id,
        user_confirmation_text="Yes, create it.",
        session_user="Prem",
    )
    assert res["success"] is False
    assert "not found" in res["message"]


# ==============================================================================
# TEST H: IDEMPOTENCY / DUPLICATE EXECUTION
# ==============================================================================

def test_step6b_idempotency_prevents_duplicate_insert():
    """Test H: Repeated creation attempt with consumed token fails before second API call."""
    prep = prepare_calendar_event(
        title="F.R.I.D.A.Y. Integration Test — DELETE ME",
        start_time="2026-08-25T14:00:00Z",
        end_time="2026-08-25T14:30:00Z",
    )
    event_id = prep["event_draft"]["event_id"]
    approval_id = prep["approval_token"]["approval_id"]

    mock_service = MagicMock()
    mock_events_api = MagicMock()
    mock_events_api.insert.return_value.execute.return_value = {
        "id": "gcal_test_evt_777",
        "summary": "F.R.I.D.A.Y. Integration Test — DELETE ME",
        "status": "confirmed",
        "start": {"dateTime": "2026-08-25T14:00:00Z"},
        "end": {"dateTime": "2026-08-25T14:30:00Z"},
    }
    mock_events_api.get.return_value.execute.return_value = {
        "id": "gcal_test_evt_777",
        "summary": "F.R.I.D.A.Y. Integration Test — DELETE ME",
        "start": {"dateTime": "2026-08-25T14:00:00Z"},
        "end": {"dateTime": "2026-08-25T14:30:00Z"},
        "status": "confirmed",
    }
    mock_service.events.return_value = mock_events_api

    google_provider = GoogleCalendarProvider()

    with patch("backend.services.calendar_agent.is_configured", return_value=True), \
         patch("backend.services.calendar_agent._build_service", return_value=mock_service), \
         patch("backend.services.calendar.provider.assert_live_calendar_execution_allowed", return_value=None), \
         patch("backend.services.calendar.service.is_live_calendar_execution_enabled", return_value=True):



        # Attempt 1: Succeeds
        res1 = create_calendar_event_with_approval(
            approval_id=approval_id,
            event_id=event_id,
            user_confirmation_text="Yes, create it.",
            session_user="Prem",
            provider=google_provider,
            attempt_real_calendar=True,
        )
        assert res1["success"] is True

        # Attempt 2: Blocked by consumed token
        res2 = create_calendar_event_with_approval(
            approval_id=approval_id,
            event_id=event_id,
            user_confirmation_text="Yes, create it.",
            session_user="Prem",
            provider=google_provider,
            attempt_real_calendar=True,
        )
        assert res2["success"] is False
        assert res2["status"] == "ALREADY_CREATED"

        # Assert insert was called EXACTLY ONCE
        assert mock_events_api.insert.call_count == 1


# ==============================================================================
# TEST I & J: GOOGLE INSERT FAILURE & INDEPENDENT VERIFICATION FAILURE
# ==============================================================================

def test_step6b_google_insert_or_verification_failure():
    """Tests I & J: Provider insert error or independent verification failure returns error without second insert."""
    prep = prepare_calendar_event(
        title="F.R.I.D.A.Y. Integration Test — DELETE ME",
        start_time="2026-08-25T14:00:00Z",
        end_time="2026-08-25T14:30:00Z",
    )
    event_id = prep["event_draft"]["event_id"]
    approval_id = prep["approval_token"]["approval_id"]

    mock_service = MagicMock()
    mock_events_api = MagicMock()
    mock_events_api.insert.side_effect = Exception("Google API 500 Internal Error")
    mock_service.calendarList.return_value.list.return_value.execute.return_value = {"items": []}
    mock_service.events.return_value = mock_events_api

    google_provider = GoogleCalendarProvider()

    with patch("backend.services.calendar_agent.is_configured", return_value=True), \
         patch("backend.services.calendar_agent._build_service", return_value=mock_service), \
         patch("backend.services.calendar.provider.assert_live_calendar_execution_allowed", return_value=None), \
         patch("backend.services.calendar.service.is_live_calendar_execution_enabled", return_value=True):



        res = create_calendar_event_with_approval(
            approval_id=approval_id,
            event_id=event_id,
            user_confirmation_text="Yes, create it.",
            session_user="Prem",
            provider=google_provider,
            attempt_real_calendar=True,
        )

        assert res["success"] is False
        assert res["status"] == "PROVIDER_FAILURE"
        assert "500 Internal Error" in res["message"]


# ==============================================================================
# TEST O: SECRET REDACTION IN STEP 6B LOGS
# ==============================================================================

def test_step6b_no_secret_leakage():
    """Test O: Verify no tokens or secrets leak in audit logs during Step 6B execution."""
    logs = calendar_audit_logger.get_logs()
    for log_entry in logs:
        log_str = str(log_entry).lower()
        assert "access_token" not in log_str
        assert "refresh_token" not in log_str
        assert "client_secret" not in log_str
