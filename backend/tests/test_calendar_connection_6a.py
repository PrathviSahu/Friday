"""Targeted unit tests for Phase 5.5C Calendar Step 6A: Real Google Calendar Account Connection (Tests A through J).
"""

import pytest
from unittest.mock import MagicMock, patch
from backend.services.calendar.config import (
    CalendarConnectionStatus,
    RealCalendarBlockedError,
    CALENDAR_LIVE_EXECUTION,
)
from backend.services.calendar.provider import GoogleCalendarProvider
from backend.services.calendar_agent import CalendarUnavailableError


# ==============================================================================
# TEST A: NO OAUTH CONFIGURED (NOT_CONFIGURED)
# ==============================================================================

def test_step6a_not_configured():
    """Test A: NOT_CONFIGURED when credentials.json and tokens are missing."""
    provider = GoogleCalendarProvider()

    with patch("backend.services.calendar_agent.has_token_file", return_value=False), \
         patch("backend.services.calendar_agent.has_service_account_file", return_value=False), \
         patch("backend.services.calendar_agent.has_credentials_file", return_value=False):

        res = provider.check_connection()
        assert res["status"] == CalendarConnectionStatus.NOT_CONFIGURED.value
        assert res["connected"] is False
        assert res["provider"] == "google_calendar"


# ==============================================================================
# TEST B: OAUTH REQUIRED (AUTH_REQUIRED)
# ==============================================================================

def test_step6a_auth_required():
    """Test B: AUTH_REQUIRED when credentials.json exists but user token is missing."""
    provider = GoogleCalendarProvider()

    with patch("backend.services.calendar_agent.has_token_file", return_value=False), \
         patch("backend.services.calendar_agent.has_service_account_file", return_value=False), \
         patch("backend.services.calendar_agent.has_credentials_file", return_value=True):

        res = provider.check_connection()
        assert res["status"] == CalendarConnectionStatus.AUTH_REQUIRED.value
        assert res["connected"] is False


# ==============================================================================
# TEST C & I: SUCCESSFUL AUTHORIZATION (CONNECTED) & READ-ONLY METADATA
# ==============================================================================

def test_step6a_connected_success():
    """Tests C & I: Successful read-only API call returns CONNECTED and metadata."""
    provider = GoogleCalendarProvider()
    mock_service = MagicMock()
    mock_cal_list = MagicMock()
    mock_cal_list.list.return_value.execute.return_value = {
        "items": [
            {
                "summary": "Prem's Personal Calendar",
                "timeZone": "Asia/Kolkata",
                "primary": True,
            }
        ]
    }
    mock_service.calendarList.return_value = mock_cal_list

    with patch("backend.services.calendar_agent.has_token_file", return_value=True), \
         patch("backend.services.calendar_agent._build_service", return_value=mock_service):

        res = provider.check_connection()
        assert res["status"] == CalendarConnectionStatus.CONNECTED.value
        assert res["connected"] is True
        assert res["primary_calendar"] == "Prem's Personal Calendar"
        assert res["timezone"] == "Asia/Kolkata"
        assert "https://www.googleapis.com/auth/calendar.readonly" in res["granted_scopes"]


# ==============================================================================
# TEST D & E: EXPIRED TOKEN & REFRESH FAILURE (AUTHENTICATION_FAILED)
# ==============================================================================

def test_step6a_authentication_failed():
    """Tests D & E: Token refresh failure returns AUTHENTICATION_FAILED."""
    provider = GoogleCalendarProvider()

    with patch("backend.services.calendar_agent.has_token_file", return_value=True), \
         patch("backend.services.calendar_agent._build_service", side_effect=CalendarUnavailableError("Token refresh error: invalid_grant")):

        res = provider.check_connection()
        assert res["status"] == CalendarConnectionStatus.AUTHENTICATION_FAILED.value
        assert res["connected"] is False


# ==============================================================================
# TEST F: PERMISSION DENIED (403 Forbidden)
# ==============================================================================

def test_step6a_permission_denied():
    """Test F: 403 Forbidden API response returns PERMISSION_DENIED."""
    provider = GoogleCalendarProvider()

    mock_service = MagicMock()
    mock_cal_list = MagicMock()
    mock_cal_list.list.return_value.execute.side_effect = Exception("403 Forbidden: Insufficient Permission")
    mock_service.calendarList.return_value = mock_cal_list

    with patch("backend.services.calendar_agent.has_token_file", return_value=True), \
         patch("backend.services.calendar_agent._build_service", return_value=mock_service):

        res = provider.check_connection()
        assert res["status"] == CalendarConnectionStatus.PERMISSION_DENIED.value
        assert res["connected"] is False


# ==============================================================================
# TEST G: NETWORK FAILURE (TEMPORARILY_UNAVAILABLE)
# ==============================================================================

def test_step6a_network_failure():
    """Test G: Connection/DNS timeout returns TEMPORARILY_UNAVAILABLE."""
    provider = GoogleCalendarProvider()

    mock_service = MagicMock()
    mock_cal_list = MagicMock()
    mock_cal_list.list.return_value.execute.side_effect = Exception("Connection timed out (DNS lookup failed)")
    mock_service.calendarList.return_value = mock_cal_list

    with patch("backend.services.calendar_agent.has_token_file", return_value=True), \
         patch("backend.services.calendar_agent._build_service", return_value=mock_service):

        res = provider.check_connection()
        assert res["status"] == CalendarConnectionStatus.TEMPORARILY_UNAVAILABLE.value
        assert res["connected"] is False


# ==============================================================================
# TEST H: SECRET REDACTION
# ==============================================================================

def test_step6a_secret_redaction():
    """Test H: Status response must NEVER contain access tokens, refresh tokens, or client secrets."""
    provider = GoogleCalendarProvider()
    mock_service = MagicMock()
    mock_cal_list = MagicMock()
    mock_cal_list.list.return_value.execute.return_value = {"items": []}
    mock_service.calendarList.return_value = mock_cal_list

    with patch("backend.services.calendar_agent.has_token_file", return_value=True), \
         patch("backend.services.calendar_agent._build_service", return_value=mock_service):

        res = provider.check_connection()
        res_str = str(res).lower()
        assert "access_token" not in res_str
        assert "refresh_token" not in res_str
        assert "client_secret" not in res_str
        assert "authorization" not in res_str


# ==============================================================================
# TEST J: WRITE OPERATION REMAINS BLOCKED
# ==============================================================================

def test_step6a_write_operation_remains_blocked():
    """Test J: Assert that live event creation is strictly blocked when CALENDAR_LIVE_EXECUTION=false."""
    assert CALENDAR_LIVE_EXECUTION is False, "CALENDAR_LIVE_EXECUTION must be false."

    google_provider = GoogleCalendarProvider()
    with pytest.raises(RealCalendarBlockedError) as exc_info:
        google_provider.create_event("Test Title", "2026-08-25T10:00:00Z", "2026-08-25T11:00:00Z")

    assert "SAFETY GUARD ACTIVE" in str(exc_info.value)
