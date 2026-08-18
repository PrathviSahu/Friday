"""services.agent — F.R.I.D.A.Y. Safe Autonomous Execution & Tool-Use Engine."""

from services.agent.tool_registry import (
    register_tool,
    get_tool,
    list_tools,
    RiskLevel,
    ToolDefinition
)
from services.agent.planner import (
    create_execution_plan,
    validate_plan,
    ExecutionPlan,
    PlanStep
)
from services.agent.permission_engine import (
    check_tool_permission,
    create_pending_approval,
    get_pending_approval,
    consume_pending_approval,
    clear_pending_approvals,
    PendingApproval
)
from services.agent.executor import (
    execute_tool,
    ToolExecutionResult
)
from services.agent.verification import (
    verify_tool_execution
)
from services.agent.audit_logger import (
    log_audit_record,
    check_idempotency,
    record_idempotency
)

__all__ = [
    "register_tool",
    "get_tool",
    "list_tools",
    "RiskLevel",
    "ToolDefinition",
    "create_execution_plan",
    "validate_plan",
    "ExecutionPlan",
    "PlanStep",
    "check_tool_permission",
    "create_pending_approval",
    "get_pending_approval",
    "consume_pending_approval",
    "clear_pending_approvals",
    "PendingApproval",
    "execute_tool",
    "ToolExecutionResult",
    "verify_tool_execution",
    "log_audit_record",
    "check_idempotency",
    "record_idempotency",
]
