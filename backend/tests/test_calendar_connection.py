"""Targeted unit tests for Phase 5.5C Calendar Step 2: Connection Architecture & Read-Only Connection Checks.
"""

import pytest
from unittest.mock import MagicMock, patch
from backend.services.calendar.config import (
    CalendarConnectionStatus,
    RealCalendarBlockedError,
    CALENDAR_LIVE_EXECUTION,
)
from backend.services.calendar.provider import (
    MockCalendarProvider,
    GoogleCalendarProvider,
)
from backend.services.calendar.service import check_calendar_connection
from backend.services.calendar.audit import calendar_audit_logger


@pytest.fixture(autouse=True)
def reset_audit_logs():
    """Reset audit logger before each test."""
    calendar_audit_logger.clear()


# ==============================================================================
# 1. TEST A: NOT_CONFIGURED
# ==============================================================================

def test_connection_status_not_configured():
    """Test A: NOT_CONFIGURED when no credentials or tokens are present."""
    provider = MockCalendarProvider()
    provider.simulated_status = CalendarConnectionStatus.NOT_CONFIGURED

    res = check_calendar_connection(provider=provider)

    assert res["status"] == CalendarConnectionStatus.NOT_CONFIGURED.value
    assert res["connected"] is False
    assert res["provider"] == "mock_calendar"


# ==============================================================================
# 2. TEST B: AUTH_REQUIRED
# ==============================================================================

def test_connection_status_auth_required():
    """Test B: AUTH_REQUIRED when credentials exist but user token is missing/expired."""
    provider = MockCalendarProvider()
    provider.simulated_status = CalendarConnectionStatus.AUTH_REQUIRED

    res = check_calendar_connection(provider=provider)

    assert res["status"] == CalendarConnectionStatus.AUTH_REQUIRED.value
    assert res["connected"] is False


# ==============================================================================
# 3. TEST C: AUTHENTICATION_FAILED
# ==============================================================================

def test_connection_status_auth_failed():
    """Test C: AUTHENTICATION_FAILED when token refresh fails."""
    provider = MockCalendarProvider()
    provider.simulated_status = CalendarConnectionStatus.AUTHENTICATION_FAILED

    res = check_calendar_connection(provider=provider)

    assert res["status"] == CalendarConnectionStatus.AUTHENTICATION_FAILED.value
    assert res["connected"] is False


# ==============================================================================
# 4. TEST D: PERMISSION_DENIED
# ==============================================================================

def test_connection_status_permission_denied():
    """Test D: PERMISSION_DENIED when 403 Forbidden or scope denial occurs."""
    provider = MockCalendarProvider()
    provider.simulated_status = CalendarConnectionStatus.PERMISSION_DENIED

    res = check_calendar_connection(provider=provider)

    assert res["status"] == CalendarConnectionStatus.PERMISSION_DENIED.value
    assert res["connected"] is False


# ==============================================================================
# 5. TEST E: TEMPORARILY_UNAVAILABLE
# ==============================================================================

def test_connection_status_temporarily_unavailable():
    """Test E: TEMPORARILY_UNAVAILABLE during network / provider failure."""
    provider = MockCalendarProvider()
    provider.should_fail = True

    res = check_calendar_connection(provider=provider)

    assert res["status"] == CalendarConnectionStatus.TEMPORARILY_UNAVAILABLE.value
    assert res["connected"] is False


# ==============================================================================
# 6. TEST F: CONNECTED SUCCESSFUL
# ==============================================================================

def test_connection_status_connected():
    """Test F: CONNECTED when read-only ping succeeds."""
    provider = MockCalendarProvider()
    provider.simulated_status = CalendarConnectionStatus.CONNECTED

    res = check_calendar_connection(provider=provider)

    assert res["status"] == CalendarConnectionStatus.CONNECTED.value
    assert res["connected"] is True
    assert "account" in res


# ==============================================================================
# 7. TEST G: SECRET REDACTION
# ==============================================================================

def test_connection_status_secret_redaction():
    """Test G: Ensure no access tokens, refresh tokens, or secrets exist in return status dict."""
    provider = MockCalendarProvider()
    res = check_calendar_connection(provider=provider)

    res_str = str(res).lower()
    assert "access_token" not in res_str
    assert "refresh_token" not in res_str
    assert "client_secret" not in res_str
    assert "private_key" not in res_str


# ==============================================================================
# 8. TEST H: NO MUTATION CALLED DURING CONNECTION CHECK
# ==============================================================================

def test_connection_check_causes_zero_mutations():
    """Test H: Connection check MUST NOT create, edit, or delete any event."""
    provider = MockCalendarProvider()
    initial_event_count = len(provider.list_events())

    res = check_calendar_connection(provider=provider)

    final_event_count = len(provider.list_events())
    assert initial_event_count == final_event_count == 0


# ==============================================================================
# 9. TEST I: REAL PROVIDER BLOCKED WHEN LIVE EXECUTION IS FALSE
# ==============================================================================

def test_real_provider_mutation_blocked():
    """Test I: Assert RealCalendarBlockedError is raised if RealCalendarProvider attempts event creation while CALENDAR_LIVE_EXECUTION=false."""
    assert CALENDAR_LIVE_EXECUTION is False, "CALENDAR_LIVE_EXECUTION must be false."

    google_provider = GoogleCalendarProvider()

    with pytest.raises(RealCalendarBlockedError) as exc_info:
        google_provider.create_event("Test Title", "2026-08-25T10:00:00Z", "2026-08-25T11:00:00Z")

    assert "SAFETY GUARD ACTIVE" in str(exc_info.value)
