"""services/agent/learning_loop.py — Agent Execution Learning Loop.

Captures tool execution outcomes and user feedback for continuous improvement
without polluting permanent conversational memory.
"""

from typing import Dict, Any, Optional
from services.learning_engine import save_fact


def record_execution_feedback(
    tool_name: str,
    arguments: Dict[str, Any],
    success: bool,
    user_feedback: Optional[str] = None
):
    """Processes user corrections or execution feedback into learning memory."""
    if not user_feedback:
        return

    lower = user_feedback.lower()
    if "don't apply to companies like this" in lower or "dislike company" in lower:
        comp = arguments.get("company")
        if comp:
            save_fact(f"disliked_company_{comp.lower()}", comp, "career_dislike")
    elif "prefer this resume" in lower:
        ver = arguments.get("resume_version")
        if ver:
            save_fact("preferred_resume_version", ver, "career_preference")
