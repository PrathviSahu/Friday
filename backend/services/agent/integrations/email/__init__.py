"""services/agent/integrations/email — Hardened Email Provider Subsystem."""

import os
from typing import Optional

from services.agent.integrations.email.provider import (
    EmailProvider,
    EmailConnectionStatus,
    ConnectionTestResult,
    EmailMessage,
    EmailDraft,
    SendResult,
    VerificationResult,
)
from services.agent.integrations.email.mock_provider import MockEmailProvider
from services.agent.integrations.email.smtp_provider import SmtpImapEmailProvider

_override_provider: Optional[EmailProvider] = None
_default_mock_provider = MockEmailProvider()


def get_email_provider() -> EmailProvider:
    """Returns active email provider based on configuration & test overrides."""
    global _override_provider
    if _override_provider is not None:
        return _override_provider

    live_exec = os.getenv("EMAIL_LIVE_EXECUTION", "false").lower() == "true"
    if live_exec:
        return SmtpImapEmailProvider()

    return _default_mock_provider


def set_email_provider(provider: Optional[EmailProvider]):
    """Set custom or test provider override."""
    global _override_provider
    _override_provider = provider


__all__ = [
    "EmailProvider",
    "EmailConnectionStatus",
    "ConnectionTestResult",
    "EmailMessage",
    "EmailDraft",
    "SendResult",
    "VerificationResult",
    "MockEmailProvider",
    "SmtpImapEmailProvider",
    "get_email_provider",
    "set_email_provider",
]
