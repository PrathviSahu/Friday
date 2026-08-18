"""Production Dry-Run Execution Test for Email Approval & Controlled Send.

Verifies end-to-end dry-run flow against MockEmailProvider with EMAIL_LIVE_EXECUTION=false.
"""

import pytest
from backend.services.email import (
    EMAIL_LIVE_EXECUTION,
    MAILBOX_STATUS,
    create_email_draft,
    send_email_with_approval,
    get_default_mock_provider,
    audit_logger,
)
from backend.services.email.draft import clear_draft_store
from backend.services.email.approval import clear_approval_store


@pytest.fixture(autouse=True)
def reset_stores():
    """Reset stores prior to dry-run test."""
    clear_draft_store()
    clear_approval_store()
    get_default_mock_provider().clear()
    audit_logger.clear()


def test_production_dry_run_workflow():
    """Execute complete Production Dry-Run in Safe Mode (EMAIL_LIVE_EXECUTION=False)."""

    # Assert environment safety state
    assert EMAIL_LIVE_EXECUTION is False, "EMAIL_LIVE_EXECUTION must be false for production dry-run."
    assert MAILBOX_STATUS == "NOT_CONFIGURED", "Mailbox status must be NOT_CONFIGURED."

    # 1. Create Draft & Generate Approval Token
    recipient = "hiring.manager@techcorp.io"
    subject = "Senior AI Engineer Application — Prem Sahu"
    body = "Dear Hiring Manager,\n\nI am writing to express my strong interest in the Senior AI Engineer position."

    prep = create_email_draft(recipient, subject, body)
    assert prep["status"] == "DRAFT_PREPARED"
    assert prep["mode"] == "DRY-RUN / MOCK PROVIDER"
    draft_id = prep["draft"]["draft_id"]
    approval_id = prep["approval_token"]["approval_id"]

    # 2. Explicit User Approval & Controlled Send
    confirmation_text = "Yes, send it."
    send_res = send_email_with_approval(
        approval_id=approval_id,
        draft_id=draft_id,
        user_confirmation_text=confirmation_text,
        session_user="Prem",
    )

    # 3. Assert Send & Verification
    assert send_res["success"] is True
    assert send_res["status"] == "SUCCESS"
    assert send_res["message"] == "Email sent and verified."
    assert send_res["mode"] == "DRY-RUN / MOCK PROVIDER"
    assert send_res["verified"] is True
    assert send_res["real_email_sent"] is False
    provider_msg_id = send_res["provider_message_id"]

    # 4. Independent Verification check
    mock_provider = get_default_mock_provider()
    msg_record = mock_provider.get_message(provider_msg_id)
    assert msg_record is not None
    assert msg_record["recipient"] == recipient
    assert msg_record["subject"] == subject
    assert msg_record["status"] == "RECORDED_SENT"

    # 5. Audit Log verification
    logs = audit_logger.get_logs()
    assert len(logs) >= 2
    sent_logs = [l for l in logs if l["action"] == "EMAIL_SENT_AND_VERIFIED"]
    assert len(sent_logs) == 1
    assert sent_logs[0]["provider_message_id"] == provider_msg_id

    # 6. Duplicate Attempt Blocked (Idempotency)
    duplicate_res = send_email_with_approval(
        approval_id=approval_id,
        draft_id=draft_id,
        user_confirmation_text=confirmation_text,
        session_user="Prem",
    )
    assert duplicate_res["success"] is False
    assert duplicate_res["message"] == "The email was already sent."
    assert len(mock_provider._outbox) == 1
