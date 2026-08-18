"""Email configuration and safety guards for FRIDAY email execution.

Ensures real SMTP sending is strictly disabled unless explicitly permitted.
"""

import os

# Default execution mode is DRY-RUN / MOCK ONLY
EMAIL_LIVE_EXECUTION = os.getenv("EMAIL_LIVE_EXECUTION", "false").lower() in ("true", "1", "yes")
MAILBOX_STATUS = "NOT_CONFIGURED"


class RealSMTPBlockedError(Exception):
    """Raised when real SMTP execution is attempted while EMAIL_LIVE_EXECUTION=False."""
    pass


def is_live_execution_enabled() -> bool:
    """Return whether live email execution is enabled via environment."""
    return EMAIL_LIVE_EXECUTION


def assert_live_execution_allowed():
    """Safety guard: raise RealSMTPBlockedError if live execution is disabled."""
    if not is_live_execution_enabled():
        raise RealSMTPBlockedError(
            "SAFETY GUARD ACTIVE: Real SMTP execution is strictly forbidden when EMAIL_LIVE_EXECUTION=false."
        )
