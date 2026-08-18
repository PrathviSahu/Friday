"""FRIDAY Email Service Package."""

from .config import EMAIL_LIVE_EXECUTION, MAILBOX_STATUS, RealSMTPBlockedError
from .draft import draft_email, update_draft, get_draft, Draft
from .approval import create_approval_token, validate_approval, consume_approval_token, PendingApproval
from .parser import is_explicit_send_approval, evaluate_user_confirmation
from .provider import MockEmailProvider, RealSMTPEmailProvider
from .verifier import IndependentVerifier, IndependentVerificationError
from .audit import audit_logger, EmailAuditLogger
from .service import (
    create_email_draft,
    edit_email_draft,
    send_email_with_approval,
    get_default_mock_provider,
)

__all__ = [
    "EMAIL_LIVE_EXECUTION",
    "MAILBOX_STATUS",
    "RealSMTPBlockedError",
    "draft_email",
    "update_draft",
    "get_draft",
    "Draft",
    "create_approval_token",
    "validate_approval",
    "consume_approval_token",
    "PendingApproval",
    "is_explicit_send_approval",
    "evaluate_user_confirmation",
    "MockEmailProvider",
    "RealSMTPEmailProvider",
    "IndependentVerifier",
    "IndependentVerificationError",
    "audit_logger",
    "EmailAuditLogger",
    "create_email_draft",
    "edit_email_draft",
    "send_email_with_approval",
    "get_default_mock_provider",
]
