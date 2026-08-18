"""services/agent/executor.py — Centralized Agent Tool Executor.

Orchestrates:
1. Tool validation and parameter checks.
2. Idempotency checks to prevent duplicate external side effects.
3. 4-Tier Permission gating (generates pending approvals if needed).
4. Safe execution with exception shielding.
5. Independent result verification.
6. Structured audit logging with secret redaction.
"""

import time
import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel

from services.agent.tool_registry import get_tool, get_tool_handler, ToolDefinition, RiskLevel
from services.agent.permission_engine import check_tool_permission, create_pending_approval
from services.agent.verification import verify_tool_execution
from services.agent.audit_logger import check_idempotency, record_idempotency, log_audit_record


class ToolExecutionResult(BaseModel):
    success: bool
    verified: bool
    status: str                         # "executed", "needs_approval", "blocked", "failed", "duplicate_prevented"
    tool_name: str
    result: Optional[Dict[str, Any]] = None
    preview_text: Optional[str] = None
    action_id: Optional[str] = None
    approval_prompt: Optional[str] = None
    verification_note: Optional[str] = None
    error: Optional[str] = None


def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    user_request: str = "",
    domain: str = "GENERAL",
    is_boss: bool = True,
    user_approved: bool = False
) -> ToolExecutionResult:
    """Central entrypoint to safely execute any registered agent tool."""
    execution_id = f"EXEC-{tool_name.upper()}-{uuid.uuid4().hex[:12]}"
    tool_def = get_tool(tool_name)
    if not tool_def:
        return ToolExecutionResult(
            success=False,
            verified=False,
            status="failed",
            tool_name=tool_name,
            error=f"Unregistered tool: '{tool_name}'."
        )

    # 1. Idempotency Check for external operations (Level 2)
    idempotency_key = f"{tool_name}:{str(sorted(arguments.items()))}"
    if tool_def.risk_level == RiskLevel.USER_APPROVAL and user_approved:
        if check_idempotency(idempotency_key):
            log_audit_record(
                execution_id=execution_id,
                user_request=user_request,
                domain=domain,
                tool_name=tool_name,
                arguments=arguments,
                permission_level=tool_def.risk_level.value,
                approval_required=True,
                approved=True,
                success=False,
                verified=False,
                error_code="DUPLICATE_PREVENTED"
            )
            return ToolExecutionResult(
                success=False,
                verified=True,
                status="duplicate_prevented",
                tool_name=tool_name,
                error="Action was already executed recently. Duplicate execution prevented for safety."
            )

    # 2. Permission Check
    allowed, perm_reason = check_tool_permission(tool_def, is_boss, user_approved)
    if not allowed:
        if tool_def.risk_level == RiskLevel.USER_APPROVAL and not user_approved:
            # Generate preview and pending approval
            action_id = f"ACT-{abs(hash(idempotency_key)) % 100000}"
            preview_text = f"Action: {tool_name} with target parameters: {arguments}"
            
            # Format domain-specific approval prompts
            if tool_name == "submit_job_application":
                comp = arguments.get("company", "Employer")
                role = arguments.get("role", "Software Engineer")
                approval_prompt = f"Boss, I've prepared your application packet for {role} at {comp}. Ready to submit?"
                preview_text = f"Candidate: Prem Sahu | Target: {comp} ({role}) | Resume: Resume_v3"
            elif tool_name == "send_email":
                to = arguments.get("to", "recipient")
                subj = arguments.get("subject", "No subject")
                approval_prompt = f"Boss, I've drafted the email to {to} ('{subj}'). Shall I send it?"
                preview_text = f"To: {to}\nSubject: {subj}"
            elif tool_name == "create_calendar_event":
                title = arguments.get("title", "Event")
                st = arguments.get("start_time", "Scheduled Time")
                tz = arguments.get("timezone", "Asia/Kolkata")
                approval_prompt = f"Prem, I've prepared the calendar event '{title}' for {st} ({tz}). Ready to create it?"
                preview_text = f"Title: {title}\nTime: {st} ({tz})"
            elif tool_name == "execute_trade_order":
                sym = arguments.get("symbol", "Asset")
                sh = arguments.get("shares", 1)
                side = arguments.get("side", "BUY")
                approval_prompt = f"Ready to submit {side} order for {sh} shares of {sym} at market price. Confirm execution?"
                preview_text = f"Order: {side} {sh} {sym} @ Market"
            else:
                approval_prompt = f"Execute {tool_name} with the provided parameters?"

            create_pending_approval(action_id, tool_name, arguments, preview_text)
            
            return ToolExecutionResult(
                success=True,
                verified=False,
                status="needs_approval",
                tool_name=tool_name,
                action_id=action_id,
                preview_text=preview_text,
                approval_prompt=approval_prompt
            )
        
        # Strictly Blocked / Unauthorized
        log_audit_record(
            execution_id=execution_id,
            user_request=user_request,
            domain=domain,
            tool_name=tool_name,
            arguments=arguments,
            permission_level=tool_def.risk_level.value,
            approval_required=True,
            approved=False,
            success=False,
            verified=False,
            error_code="PERMISSION_DENIED"
        )
        return ToolExecutionResult(
            success=False,
            verified=False,
            status="blocked",
            tool_name=tool_name,
            error=perm_reason
        )

    # 3. Tool Execution
    handler = get_tool_handler(tool_name)
    if not handler:
        return ToolExecutionResult(
            success=False,
            verified=False,
            status="failed",
            tool_name=tool_name,
            error="Missing tool execution handler."
        )

    try:
        raw_result = handler(arguments)
        if not isinstance(raw_result, dict):
            raw_result = {"output": raw_result}

        # 4. Verification Check
        verified, verif_note = verify_tool_execution(tool_name, arguments, raw_result)

        # 5. Record Idempotency
        if tool_def.risk_level == RiskLevel.USER_APPROVAL and verified:
            record_idempotency(idempotency_key)

        # 6. Audit Log
        log_audit_record(
            execution_id=execution_id,
            user_request=user_request,
            domain=domain,
            tool_name=tool_name,
            arguments=arguments,
            permission_level=tool_def.risk_level.value,
            approval_required=tool_def.requires_approval,
            approved=user_approved,
            success=True,
            verified=verified,
            verification_note=verif_note
        )

        return ToolExecutionResult(
            success=True,
            verified=verified,
            status="executed",
            tool_name=tool_name,
            result=raw_result,
            verification_note=verif_note
        )

    except Exception as e:
        log_audit_record(
            execution_id=execution_id,
            user_request=user_request,
            domain=domain,
            tool_name=tool_name,
            arguments=arguments,
            permission_level=tool_def.risk_level.value,
            approval_required=tool_def.requires_approval,
            approved=user_approved,
            success=False,
            verified=False,
            error_code=str(e)
        )
        return ToolExecutionResult(
            success=False,
            verified=False,
            status="failed",
            tool_name=tool_name,
            error=f"Execution error: {e}"
        )
