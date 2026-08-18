"""High-level Email Service Orchestrator for FRIDAY.

Enforces Step 5 pipeline:
DRAFT -> PREVIEW -> EXPLICIT APPROVAL -> TOKEN VALIDATION -> PERMISSION CHECK ->
IDEMPOTENCY CHECK -> MOCK PROVIDER SEND -> MESSAGE ID -> INDEPENDENT VERIFICATION ->
AUDIT LOG -> SUCCESS.
"""

from typing import Dict, Any, Optional, List

from .config import EMAIL_LIVE_EXECUTION, is_live_execution_enabled, RealSMTPBlockedError
from .draft import (
    Draft,
    draft_email,
    get_draft,
    update_draft,
    DraftValidationError,
    PromptInjectionDetectedError,
)
from .approval import (
    PendingApproval,
    create_approval_token,
    get_approval,
    invalidate_approvals_for_draft,
    consume_approval_token,
    validate_approval,
)
from .parser import evaluate_user_confirmation, is_explicit_send_approval
from .provider import MockEmailProvider, RealSMTPEmailProvider, MockSendResult
from .verifier import IndependentVerifier, IndependentVerificationError
from .audit import audit_logger


# Default mock provider instance for email service
_default_mock_provider = MockEmailProvider()


def get_default_mock_provider() -> MockEmailProvider:
    """Return the default mock provider instance."""
    return _default_mock_provider


def create_email_draft(
    recipient: str,
    subject: str,
    body: str,
    attachments: Optional[List[Dict[str, Any]]] = None,
    ttl_seconds: int = 300,
) -> Dict[str, Any]:
    """Level 1 PREPARATION: Prepare email draft and issue single-use approval token.

    Draft != Send Invariant: This function CANNOT send mail.
    """
    draft = draft_email(recipient, subject, body, attachments)
    approval = create_approval_token(draft, ttl_seconds=ttl_seconds)

    audit_logger.log_event(
        action="DRAFT_CREATED",
        draft_id=draft.draft_id,
        approval_id=approval.approval_id,
        content_hash=draft.content_hash,
        recipient=draft.recipient,
        result="DRAFT_AND_APPROVAL_PREPARED",
    )

    return {
        "status": "DRAFT_PREPARED",
        "draft": draft.to_dict(),
        "approval_token": approval.to_dict(),
        "preview": {
            "to": draft.recipient,
            "subject": draft.subject,
            "body": draft.body,
            "version": draft.version,
            "content_hash": draft.content_hash,
            "attachments": draft.attachments,
        },
        "mode": "DRY-RUN / MOCK PROVIDER" if not is_live_execution_enabled() else "LIVE",
    }


def edit_email_draft(
    draft_id: str,
    new_body: Optional[str] = None,
    new_subject: Optional[str] = None,
    new_recipient: Optional[str] = None,
    new_attachments: Optional[List[Dict[str, Any]]] = None,
    ttl_seconds: int = 300,
) -> Dict[str, Any]:
    """Modify an existing draft, increment version, update hash, and invalidate old approvals."""
    # 1. Invalidate old approval tokens
    invalidated_token_ids = invalidate_approvals_for_draft(draft_id, reason="draft_modified")

    # 2. Update draft (recomputes content_hash, increments version)
    updated_draft = update_draft(
        draft_id=draft_id,
        new_body=new_body,
        new_subject=new_subject,
        new_recipient=new_recipient,
        new_attachments=new_attachments,
    )

    # 3. Create fresh approval token for revised version
    fresh_approval = create_approval_token(updated_draft, ttl_seconds=ttl_seconds)

    audit_logger.log_event(
        action="DRAFT_MODIFIED",
        draft_id=updated_draft.draft_id,
        approval_id=fresh_approval.approval_id,
        content_hash=updated_draft.content_hash,
        recipient=updated_draft.recipient,
        result=f"DRAFT_MODIFIED_V{updated_draft.version}_OLD_APPROVALS_INVALIDATED",
    )

    return {
        "status": "DRAFT_MODIFIED",
        "draft": updated_draft.to_dict(),
        "invalidated_approval_ids": invalidated_token_ids,
        "fresh_approval_token": fresh_approval.to_dict(),
        "preview": {
            "to": updated_draft.recipient,
            "subject": updated_draft.subject,
            "body": updated_draft.body,
            "version": updated_draft.version,
            "content_hash": updated_draft.content_hash,
            "attachments": updated_draft.attachments,
        },
    }


def send_email_with_approval(
    approval_id: str,
    draft_id: str,
    user_confirmation_text: str,
    session_user: str = "Prem",
    now: Optional[float] = None,
    provider: Optional[Any] = None,
    simulate_verification_failure: bool = False,
    attempt_real_smtp: bool = False,
) -> Dict[str, Any]:
    """Execute Step 5 Controlled Send with Explicit Approval and Verification.

    ALL 10 checks, idempotency, single-use token consumption, mock provider send,
    independent verification, and audit logging are strictly enforced.
    """
    effective_provider = provider if provider is not None else _default_mock_provider

    # SAFETY CHECK: If attempt_real_smtp is True or real SMTP provider passed, check safety guard
    if attempt_real_smtp or isinstance(effective_provider, RealSMTPEmailProvider):
        if not is_live_execution_enabled():
            audit_logger.log_event(
                action="REAL_SMTP_BLOCKED",
                draft_id=draft_id,
                approval_id=approval_id,
                result="BLOCKED_BY_SAFETY_GUARD",
            )
            raise RealSMTPBlockedError(
                "SAFETY GUARD ACTIVE: Real SMTP execution is strictly forbidden when EMAIL_LIVE_EXECUTION=false."
            )

    # 1. Evaluate User Confirmation Language (Explicit vs Ambiguous vs Broad)
    is_confirmed, confirmation_reason = evaluate_user_confirmation(user_confirmation_text)

    if not is_confirmed:
        audit_logger.log_event(
            action="SEND_REJECTED_LANGUAGE",
            draft_id=draft_id,
            approval_id=approval_id,
            result=f"REJECTED: {confirmation_reason}",
        )
        return {
            "success": False,
            "status": "REJECTED_LANGUAGE",
            "message": confirmation_reason,
            "real_email_sent": False,
        }

    # 2. Validate Approval Token (Checks 1-10)
    is_valid, validation_reason, approval_obj = validate_approval(
        approval_id=approval_id,
        draft_id=draft_id,
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
            status_code = "ALREADY_SENT"
            validation_reason = "The email was already sent."

        audit_logger.log_event(
            action="SEND_BLOCKED_VALIDATION",
            draft_id=draft_id,
            approval_id=approval_id,
            result=f"BLOCKED: {validation_reason}",
        )

        return {
            "success": False,
            "status": status_code,
            "message": validation_reason,
            "real_email_sent": False,
        }

    draft = get_draft(draft_id)
    if not draft:
        return {
            "success": False,
            "status": "DRAFT_NOT_FOUND",
            "message": f"Draft '{draft_id}' not found.",
            "real_email_sent": False,
        }

    # 3. Idempotency Check (If draft is already SENT)
    if draft.status == "SENT":
        audit_logger.log_event(
            action="SEND_BLOCKED_IDEMPOTENCY",
            draft_id=draft_id,
            approval_id=approval_id,
            content_hash=draft.content_hash,
            recipient=draft.recipient,
            result="BLOCKED: The email was already sent.",
        )
        return {
            "success": False,
            "status": "ALREADY_SENT",
            "message": "The email was already sent.",
            "real_email_sent": False,
        }

    # 4. Dispatch via Mock Provider (or passed provider)
    try:
        send_result: MockSendResult = effective_provider.send(
            recipient=draft.recipient,
            subject=draft.subject,
            body=draft.body,
            attachments=draft.attachments,
            draft_id=draft.draft_id,
            approval_id=approval_id,
            content_hash=draft.content_hash,
        )
    except Exception as exc:
        audit_logger.log_event(
            action="SEND_FAILED_PROVIDER",
            draft_id=draft.draft_id,
            approval_id=approval_id,
            content_hash=draft.content_hash,
            recipient=draft.recipient,
            result=f"PROVIDER_ERROR: {str(exc)}",
        )
        return {
            "success": False,
            "status": "PROVIDER_FAILURE",
            "message": f"Email provider send failed: {str(exc)}",
            "real_email_sent": False,
        }

    # 5. Immediately Consume Approval Token & Update Draft Status
    consume_approval_token(approval_id)
    draft.status = "SENT"

    # 6. Perform Independent Verification
    try:
        verification_data = IndependentVerifier.verify_delivery(
            provider=effective_provider,
            provider_message_id=send_result.provider_message_id,
            expected_recipient=draft.recipient,
            expected_subject=draft.subject,
            expected_content_hash=draft.content_hash,
            should_simulate_verification_failure=simulate_verification_failure,
        )
    except IndependentVerificationError as ver_err:
        audit_logger.log_event(
            action="VERIFICATION_FAILED",
            draft_id=draft.draft_id,
            approval_id=approval_id,
            content_hash=draft.content_hash,
            recipient=draft.recipient,
            provider_message_id=send_result.provider_message_id,
            result=f"VERIFICATION_FAILED: {str(ver_err)}",
        )
        return {
            "success": False,
            "status": "VERIFICATION_FAILURE",
            "message": str(ver_err),
            "provider_message_id": send_result.provider_message_id,
            "real_email_sent": False,
        }

    # 7. Audit Log Success Event
    audit_logger.log_event(
        action="EMAIL_SENT_AND_VERIFIED",
        draft_id=draft.draft_id,
        approval_id=approval_id,
        content_hash=draft.content_hash,
        recipient=draft.recipient,
        provider_message_id=send_result.provider_message_id,
        result="SUCCESS",
        verification_result=verification_data,
    )

    return {
        "success": True,
        "status": "SUCCESS",
        "message": "Email sent and verified.",
        "provider_message_id": send_result.provider_message_id,
        "mode": "DRY-RUN / MOCK PROVIDER",
        "verified": True,
        "verification_details": verification_data,
        "real_email_sent": False,
    }
