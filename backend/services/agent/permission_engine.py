"""services/agent/permission_engine.py — Granular 4-Tier Permission & Action Approval Engine.

Enforces execution security policies:
- LEVEL 0: READ_ONLY (Allowed without confirmation)
- LEVEL 1: PREPARATION (Allowed without external side effects)
- LEVEL 2: USER_APPROVAL (Must be explicitly confirmed by Boss for single-use execution)
- LEVEL 3: AUTOMATED (Pre-configured low-risk background routines)
- BLOCKED: Strictly forbidden
"""

import time
import threading
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from services.agent.tool_registry import ToolDefinition, RiskLevel


@dataclass
class PendingApproval:
    action_id: str
    tool_name: str
    arguments: Dict[str, Any]
    preview_text: str
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 300)  # 5 minute TTL
    consumed: bool = False


_pending_approvals: Dict[str, PendingApproval] = {}
_perm_lock = threading.RLock()


def create_pending_approval(
    action_id: str,
    tool_name: str,
    arguments: Dict[str, Any],
    preview_text: str
) -> PendingApproval:
    """Register a pending high-risk action requiring user approval."""
    with _perm_lock:
        approval = PendingApproval(
            action_id=action_id,
            tool_name=tool_name,
            arguments=arguments,
            preview_text=preview_text
        )
        _pending_approvals[action_id] = approval
        return approval


def get_pending_approval(action_id: str) -> Optional[PendingApproval]:
    """Retrieve an active pending approval if not expired or consumed."""
    with _perm_lock:
        approval = _pending_approvals.get(action_id)
        if not approval:
            return None
        if time.time() > approval.expires_at or approval.consumed:
            return None
        return approval


def consume_pending_approval(action_id: str) -> bool:
    """Consume a single-use approval token upon successful execution."""
    with _perm_lock:
        approval = _pending_approvals.get(action_id)
        if not approval or approval.consumed or time.time() > approval.expires_at:
            return False
        approval.consumed = True
        return True


def clear_pending_approvals():
    """Clear all pending approval states."""
    with _perm_lock:
        _pending_approvals.clear()


def check_tool_permission(
    tool: ToolDefinition,
    is_boss: bool,
    user_approved: bool = False
) -> Tuple[bool, str]:
    """Evaluates whether a tool execution is permitted.
    
    Returns (is_allowed, reason).
    """
    if tool.risk_level == RiskLevel.BLOCKED:
        return False, "Action is strictly blocked by system security policy."

    # Public guests are restricted to READ_ONLY and safe PREPARATION
    if not is_boss:
        if tool.risk_level in [RiskLevel.USER_APPROVAL, RiskLevel.BLOCKED]:
            return False, "Public guest mode cannot execute external side effects. Boss authentication required."

    if tool.risk_level in [RiskLevel.READ_ONLY, RiskLevel.LOW_RISK_SYSTEM_ACTION, RiskLevel.PREPARATION, RiskLevel.AUTOMATED]:
        return True, "Execution permitted under standard tier."

    if tool.risk_level == RiskLevel.USER_APPROVAL:
        if user_approved:
            return True, "Execution authorized via explicit user approval."
        return False, "Action requires explicit user approval before execution."

    return False, "Unknown risk tier."
