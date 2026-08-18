"""tests/test_email_integration.py — Phase 5.5 Real Integration Hardening: Email Suite."""

import pytest
import os
from services.agent.integrations.email import (
    get_email_provider,
    set_email_provider,
    MockEmailProvider,
    EmailConnectionStatus,
    EmailMessage
)
from services.agent import execute_tool, check_idempotency, clear_idempotency_store
from services.brain.engine import respond
from services.brain.context_manager import reset_context, get_context, update_context


@pytest.fixture(autouse=True)
def setup_email_test_env():
    """Ensure clean test state with a fresh MockEmailProvider."""
    reset_context()
    clear_idempotency_store()
    mock_prov = MockEmailProvider()
    set_email_provider(mock_prov)
    yield
    reset_context()
    clear_idempotency_store()
    set_email_provider(None)


class TestEmailIntegrationSuite:
    """Comprehensive test suite for Phase 5.5 Email Integration."""

    # ── 1. CONNECTION STATUS TESTS ──

    def test_connection_status_states(self):
        """Verifies truthful connection status reporting."""
        prov = MockEmailProvider(initial_status=EmailConnectionStatus.CONNECTED)
        assert prov.check_connection() == EmailConnectionStatus.CONNECTED

        prov.set_connection_status(EmailConnectionStatus.AUTHENTICATION_FAILED)
        assert prov.check_connection() == EmailConnectionStatus.AUTHENTICATION_FAILED

        prov.set_connection_status(EmailConnectionStatus.NOT_CONFIGURED)
        assert prov.check_connection() == EmailConnectionStatus.NOT_CONFIGURED

    # ── 2. READ & SEARCH TESTS ──

    def test_read_unread_emails(self):
        """Reading unread emails returns structured messages without side effects."""
        res = execute_tool("read_emails", {"limit": 5, "unread_only": True}, is_boss=True)
        assert res.success is True
        assert res.verified is True
        msgs = res.result.get("messages", [])
        assert len(msgs) == 2
        assert msgs[0]["sender"] == "recruiter@jpmorgan.com"
        assert msgs[0]["priority"] is True

    def test_search_emails_by_sender(self):
        """Search emails filters by sender keyword (e.g. LinkedIn)."""
        res = execute_tool("search_emails", {"query": "LinkedIn", "limit": 5}, is_boss=True)
        assert res.success is True
        msgs = res.result.get("messages", [])
        assert len(msgs) >= 1
        assert "linkedin" in msgs[0]["sender"].lower()

    def test_conversational_read_emails(self):
        """Conversational query 'Check my unread emails' returns natural summary."""
        r = respond("Check my unread emails.")
        assert "2 unread emails" in r["reply"].lower() or "jpmorgan" in r["reply"].lower()

    def test_conversational_search_emails(self):
        """Conversational query 'Find emails from LinkedIn' returns matching items."""
        r = respond("Find emails from LinkedIn.")
        assert "linkedin" in r["reply"].lower()

    # ── 3. DRAFTING WITH CAREER CONTEXT ──

    def test_draft_email_with_career_context(self):
        """Drafting resolves active job, recruiter, candidate details, and resume."""
        # Set active context to JPMorgan role
        update_context(
            domain="CAREER",
            job_id="jpmc-sde",
            job_title="Software Engineer — Full Stack",
            company="JPMorgan Chase",
            salary="14–18 LPA"
        )
        r = respond("Draft an email to the recruiter for the second job.")
        assert "recruiter@jpmorgan.com" in r["reply"]
        assert "resume_v3.pdf" in r["reply"].lower()
        ctx = get_context()
        assert ctx.active_pending_action is not None
        assert ctx.active_pending_action["tool_name"] == "send_email"
        assert ctx.active_pending_action["arguments"]["to"] == "recruiter@jpmorgan.com"

    # ── 4. EDIT FLOW & APPROVAL INVALIDATION ──

    def test_edit_draft_invalidates_previous_approval(self):
        """Editing draft modifies content and invalidates prior approval token."""
        # Step 1: Create draft
        respond("Draft an email to the recruiter.")
        ctx = get_context()
        prev_body = ctx.active_pending_action["arguments"]["body"]

        # Step 2: Edit request
        r_edit = respond("Make it shorter.")
        assert "updated the draft" in r_edit["reply"].lower() or "more concise" in r_edit["reply"].lower()
        assert "invalidated" in r_edit["reply"].lower()

        # Verify content was updated and previous state was replaced
        new_ctx = get_context()
        new_body = new_ctx.active_pending_action["arguments"]["body"]
        assert new_body != prev_body
        assert "Prem Sahu" in new_body

    # ── 5. APPROVAL GATING & SEND ──

    def test_email_send_without_approval_blocked(self):
        """Sending an email without explicit approval is gated at Level 2."""
        res = execute_tool(
            "send_email",
            {"to": "recruiter@jpmorgan.com", "subject": "Hi", "body": "Body"},
            is_boss=True,
            user_approved=False
        )
        assert res.status == "needs_approval"
        assert "Shall I send it?" in res.approval_prompt or "Ready to send" in res.approval_prompt

    def test_email_send_with_valid_approval_succeeds(self):
        """Turn 1: Draft email -> Turn 2: 'Send it' dispatches and verifies."""
        respond("Draft an email to the recruiter.")
        assert get_context().active_pending_action is not None

        r_send = respond("Send it.")
        assert "email sent and verified" in r_send["reply"].lower() or "dispatched" in r_send["reply"].lower()
        assert get_context().active_pending_action is None

    # ── 6. INDEPENDENT VERIFICATION & IDEMPOTENCY ──

    def test_independent_verification_confirms_message_id(self):
        """Executor verifies provider accepted message with valid message ID."""
        res = execute_tool(
            "send_email",
            {"to": "verified_recruiter@company.com", "subject": "Application", "body": "Hello"},
            is_boss=True,
            user_approved=True
        )
        assert res.success is True
        assert res.verified is True
        assert res.result["status"] == "sent"
        assert res.result["message_id"].startswith("<msg-mock-")

    def test_idempotency_prevents_duplicate_send(self):
        """Retrying the exact same email execution within 5 minutes is blocked."""
        args = {"to": "unique_recruiter@test.com", "subject": "Subj 1", "body": "Body 1"}
        res1 = execute_tool("send_email", args, is_boss=True, user_approved=True)
        assert res1.success is True

        res2 = execute_tool("send_email", args, is_boss=True, user_approved=True)
        assert res2.status == "duplicate_prevented"
        assert res2.success is False

    # ── 7. SECURITY & SECRETS REDACTION ──

    def test_credentials_never_exposed(self):
        """Audit logging and tool outputs never expose SMTP or IMAP passwords."""
        from services.agent.audit_logger import sanitize_payload
        dirty = {
            "to": "recruiter@test.com",
            "FRIDAY_EMAIL_PASS": "SuperSecretPassword123!",
            "auth_token": "bearer-xyz",
            "subject": "Hello"
        }
        clean = sanitize_payload(dirty)
        assert clean["FRIDAY_EMAIL_PASS"] == "[REDACTED_SECRET]"
        assert clean["auth_token"] == "[REDACTED_SECRET]"
        assert clean["to"] == "recruiter@test.com"
