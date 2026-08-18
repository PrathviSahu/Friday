"""tests/test_agent_executor.py — Phase 5 Autonomous Execution & Tool-Use Test Suite."""

import pytest
from services.agent import (
    get_tool,
    list_tools,
    RiskLevel,
    create_execution_plan,
    validate_plan,
    execute_tool,
    check_tool_permission,
    check_idempotency,
    record_idempotency
)
from services.agent.audit_logger import sanitize_payload
from services.brain.engine import respond
from services.brain.context_manager import reset_context, get_context, update_context


@pytest.fixture(autouse=True)
def clean_state():
    """Reset working memory before every test."""
    reset_context()
    yield
    reset_context()


class TestAgentExecutionSuite:
    """Comprehensive test suite for Phase 5 Agent Execution Engine."""

    # ── 1. TOOL REGISTRY TESTS ──

    def test_tool_discovery_and_metadata(self):
        """Verify registered tools, metadata, risk levels, and parameter schemas."""
        job_search = get_tool("search_jobs")
        assert job_search is not None
        assert job_search.risk_level == RiskLevel.READ_ONLY
        assert job_search.domain == "CAREER"

        job_apply = get_tool("submit_job_application")
        assert job_apply is not None
        assert job_apply.risk_level == RiskLevel.USER_APPROVAL
        assert job_apply.requires_approval is True

        delete_tool = get_tool("delete_file")
        assert delete_tool is not None
        assert delete_tool.risk_level == RiskLevel.BLOCKED

        all_tools = list_tools()
        assert len(all_tools) >= 8

    def test_unknown_tool_rejection(self):
        """Unknown tools must be safely rejected."""
        res = execute_tool("non_existent_tool", {}, is_boss=True)
        assert res.success is False
        assert "Unregistered tool" in res.error

    # ── 2. PLANNER TESTS ──

    def test_planner_job_search(self):
        """Planner decomposes job search request into structured steps."""
        plan = create_execution_plan("Find Java jobs above 6 LPA", "CAREER", None)
        assert plan.domain == "CAREER"
        assert len(plan.steps) == 1
        assert plan.steps[0].tool_name == "search_jobs"
        valid, msg = validate_plan(plan)
        assert valid is True

    def test_planner_job_apply(self):
        """Planner decomposes application request into prepare + submit steps with approval flag."""
        plan = create_execution_plan("Apply to the second one", "CAREER", None)
        assert plan.domain == "CAREER"
        assert len(plan.steps) == 2
        assert plan.steps[0].tool_name == "prepare_job_application"
        assert plan.steps[1].tool_name == "submit_job_application"
        assert plan.requires_user_approval is True
        valid, msg = validate_plan(plan)
        assert valid is True

    def test_planner_blocked_tool(self):
        """Planner marks blocked operations as invalid."""
        plan = create_execution_plan("Delete that file", "SYSTEM", None)
        valid, msg = validate_plan(plan)
        assert valid is False

    # ── 3. PERMISSION TIERS & GATING ──

    def test_read_only_auto_executes(self):
        """Level 0 Read-Only tools execute without requiring approval."""
        res = execute_tool("search_jobs", {"keyword": "Java", "min_salary": 6}, is_boss=True)
        assert res.success is True
        assert res.verified is True
        assert res.status == "executed"

    def test_preparation_executes_without_side_effects(self):
        """Level 1 Preparation tools draft payloads safely."""
        res = execute_tool("draft_email", {"to": "recruiter@test.com", "subject": "Hi"}, is_boss=True)
        assert res.success is True
        assert res.result["status"] == "drafted"

    def test_user_approval_required_for_side_effects(self):
        """Level 2 Tools generate pending approvals when unapproved."""
        res = execute_tool(
            "submit_job_application",
            {"job_id": "jpmc-sde", "company": "JPMorgan Chase", "role": "Software Engineer"},
            is_boss=True,
            user_approved=False
        )
        assert res.status == "needs_approval"
        assert res.action_id is not None
        assert "Ready to submit" in res.approval_prompt

    def test_guest_cannot_execute_approval_tools(self):
        """Public guests cannot execute high-risk operations even if approved."""
        res = execute_tool(
            "submit_job_application",
            {"job_id": "jpmc-sde", "company": "JPMorgan Chase"},
            is_boss=False,
            user_approved=True
        )
        assert res.success is False
        assert res.status == "blocked"

    # ── 4. VERIFICATION & IDEMPOTENCY ──

    def test_independent_verification_on_submission(self):
        """Application submission must be verified independently against the database."""
        res = execute_tool(
            "submit_job_application",
            {"job_id": "jpmc-sde", "company": "JPMorgan Chase", "role": "Software Engineer"},
            is_boss=True,
            user_approved=True
        )
        assert res.success is True
        assert res.verified is True
        assert "verified independently" in res.verification_note.lower()

    def test_idempotency_prevents_duplicate_actions(self):
        """Duplicate executions within the time window must be blocked."""
        args = {"to": "duplicate_test@test.com", "subject": "Test Subj"}
        # First execution
        res1 = execute_tool("send_email", args, is_boss=True, user_approved=True)
        assert res1.success is True

        # Second execution with same parameters
        res2 = execute_tool("send_email", args, is_boss=True, user_approved=True)
        assert res2.status == "duplicate_prevented"
        assert res2.success is False

    def test_audit_logger_secret_redaction(self):
        """Secret tokens and passwords must be redacted in audit logging."""
        dirty = {"user": "prem", "api_key": "sk-secret123", "password": "supersecretpassword", "job": "SDE"}
        clean = sanitize_payload(dirty)
        assert clean["api_key"] == "[REDACTED_SECRET]"
        assert clean["password"] == "[REDACTED_SECRET]"
        assert clean["job"] == "SDE"

    # ── 5. END-TO-END CONVERSATIONAL APPROVAL FLOWS ──

    def test_career_apply_and_approve_flow(self):
        """Turn 1: 'Apply to the second one' -> asks approval; Turn 2: 'Yes' -> submits & verifies."""
        # Turn 1: Apply to second one
        r1 = respond("Apply to the second one.")
        assert "ready to submit" in r1["reply"].lower() or "jpmorgan" in r1["reply"].lower()
        ctx = get_context()
        assert ctx.active_pending_action is not None
        assert ctx.active_pending_action["tool_name"] == "submit_job_application"

        # Turn 2: Confirm submission
        r2 = respond("Yes.")
        assert "submitted and verified" in r2["reply"].lower()
        assert get_context().active_pending_action is None

    def test_career_apply_and_cancel_flow(self):
        """Turn 1: 'Apply to the second one' -> asks approval; Turn 2: 'Cancel' -> clears proposal."""
        r1 = respond("Apply to the second one.")
        assert get_context().active_pending_action is not None

        r2 = respond("Cancel.")
        assert "canceled" in r2["reply"].lower()
        assert get_context().active_pending_action is None

    def test_email_draft_and_send_flow(self):
        """Turn 1: 'Draft an email to the recruiter' -> drafts; Turn 2: 'Send it' -> sends & verifies."""
        r1 = respond("Draft an email to the recruiter.")
        assert "drafted the email" in r1["reply"].lower() or "ready to send" in r1["reply"].lower()
        assert get_context().active_pending_action is not None

        r2 = respond("Send it.")
        assert "email sent and verified" in r2["reply"].lower()
        assert get_context().active_pending_action is None

    def test_trading_order_approval_flow(self):
        """Turn 1: 'Buy 10 shares of Apple' -> asks approval; Turn 2: 'Confirm' -> executes order."""
        r1 = respond("Buy 10 shares of Apple.")
        assert "confirm execution" in r1["reply"].lower() or "10 shares of aapl" in r1["reply"].lower()
        assert get_context().active_pending_action is not None

        r2 = respond("Confirm.")
        assert "executed and filled" in r2["reply"].lower()
        assert get_context().active_pending_action is None

    def test_weather_autonomous_read(self):
        """Weather request runs autonomously without approval."""
        r = respond("What's the weather?")
        assert "weather" in r["reply"].lower() or "°c" in r["reply"].lower()

    def test_open_terminal_system_control(self):
        """App launch command executes cleanly."""
        r = respond("Open Terminal.")
        assert "opening terminal" in r["reply"].lower()
        assert r["action"] == "open_app"

    def test_file_deletion_blocked(self):
        """Dangerous file deletion request is blocked."""
        r = respond("Delete that file.")
        assert "disabled by security policy" in r["reply"].lower()
