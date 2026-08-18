"""services/agent/integrations/calendar/__init__.py — Calendar Integration Package & Factory.

Respects CALENDAR_LIVE_EXECUTION (default: false) and test overrides.
"""

import os
from typing import Optional

from services.agent.integrations.calendar.provider import (
    CalendarProvider,
    CalendarConnectionStatus,
    CalendarEvent,
    CalendarEventDraft,
    CalendarCreateResult,
    CalendarVerificationResult,
    compute_calendar_content_hash,
)
from services.agent.integrations.calendar.mock_provider import MockCalendarProvider
from services.agent.integrations.calendar.google_provider import GoogleCalendarProvider

_override_calendar_provider: Optional[CalendarProvider] = None
_default_mock_calendar_provider = MockCalendarProvider()


def get_calendar_provider() -> CalendarProvider:
    """Returns active calendar provider based on configuration & test overrides."""
    global _override_calendar_provider
    if _override_calendar_provider is not None:
        return _override_calendar_provider

    live_exec = os.getenv("CALENDAR_LIVE_EXECUTION", "false").lower() == "true"
    if live_exec:
        return GoogleCalendarProvider()

    return _default_mock_calendar_provider


def set_calendar_provider(provider: Optional[CalendarProvider]):
    """Set custom or test calendar provider override."""
    global _override_calendar_provider
    _override_calendar_provider = provider


__all__ = [
    "CalendarProvider",
    "CalendarConnectionStatus",
    "CalendarEvent",
    "CalendarEventDraft",
    "CalendarCreateResult",
    "CalendarVerificationResult",
    "MockCalendarProvider",
    "GoogleCalendarProvider",
    "get_calendar_provider",
    "set_calendar_provider",
    "compute_calendar_content_hash",
]
