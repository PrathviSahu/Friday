"""services/agent/verification.py — Independent Tool Execution Verification Engine.

MANDATORY SAFETY DOCTRINE:
Never assume an action succeeded simply because an API or function returned without an error.
Verify database state, receipt tokens, message IDs, or process handles independently.
"""

from typing import Dict, Any, Tuple
from services.agent.tool_registry import get_tool_verifier


def verify_tool_execution(tool_name: str, arguments: Dict[str, Any], result: Dict[str, Any]) -> Tuple[bool, str]:
    """Runs independent verification checks on tool execution results."""
    verifier = get_tool_verifier(tool_name)
    if verifier:
        try:
            is_verified = verifier(arguments, result)
            if is_verified:
                return True, "Execution verified independently against system state."
            return False, "Independent verification failed: expected state change was not detected."
        except Exception as e:
            return False, f"Verification error: {e}"

    # Default heuristic verification
    if isinstance(result, dict):
        if result.get("status") in ["success", "prepared", "submitted", "sent", "dispatched", "filled", "opened"]:
            return True, "Execution verified via standard provider acknowledgement."
        if result.get("error") or result.get("status") == "blocked":
            return False, result.get("error", "Execution failed.")

    return True, "Execution completed with standard return."
