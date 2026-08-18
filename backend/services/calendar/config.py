"""Calendar configuration, safety guards, and connection state definitions for FRIDAY.

Ensures real calendar event creation (Apple Calendar / Google Calendar) is strictly disabled unless explicitly permitted.
"""

import os
from enum import Enum


class CalendarConnectionStatus(str, Enum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    CONNECTED = "CONNECTED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    TEMPORARILY_UNAVAILABLE = "TEMPORARILY_UNAVAILABLE"


# Default execution mode is DRY-RUN / MOCK ONLY
CALENDAR_LIVE_EXECUTION = os.getenv("CALENDAR_LIVE_EXECUTION", "false").lower() in ("true", "1", "yes")
CALENDAR_STATUS = CalendarConnectionStatus.NOT_CONFIGURED


class RealCalendarBlockedError(Exception):
    """Raised when real calendar event mutation is attempted while CALENDAR_LIVE_EXECUTION=False."""
    pass


def is_live_calendar_execution_enabled() -> bool:
    """Return whether live calendar execution is enabled via environment."""
    return CALENDAR_LIVE_EXECUTION


def assert_live_calendar_execution_allowed():
    """Safety guard: raise RealCalendarBlockedError if live execution is disabled."""
    if not is_live_calendar_execution_enabled():
        raise RealCalendarBlockedError(
            "SAFETY GUARD ACTIVE: Real Calendar creation is strictly forbidden when CALENDAR_LIVE_EXECUTION=false."
        )
