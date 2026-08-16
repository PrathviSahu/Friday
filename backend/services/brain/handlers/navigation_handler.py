"""services/brain/handlers/navigation_handler.py — Workspace & mode navigation (Trading, Career OS, Dashboard)."""

import re
from typing import Optional
from services.memory import log_conversation
from services.learning_engine import log_user_action


def handle_navigation(lower_text: str, is_boss: bool) -> Optional[dict]:
    """Handles routing to primary UI workspaces and consoles."""
    if re.search(r'\b(?:open|show|launch|start|enter|go\s+to)?\s*(?:the\s+)?(?:career|job\s*portal|portal|jobs|job\s*board|career\s*os|opportunities)\b', lower_text):
        log_user_action("career")
        reply_msg = "Opening Career Intelligence Center, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "career"}

    if re.search(r'\b(?:open|show|launch|start|enter)\s+(?:the\s+)?(?:trading|trading\s+panel|trading\s+dashboard|trading\s+workstation|charts)\b|\b(?:trading\s+mode|trading\s+workstation|open\s+charts)\b|\btrading\b', lower_text):
        log_user_action("trading")
        reply_msg = "Trading Workstation, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "trading"}

    if re.search(r'\b(?:exit\s+trading\s+mode|close\s+trading\s+panel|return\s+to\s+friday|go\s+back)\b', lower_text):
        reply_msg = "Back to dashboard."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "dashboard"}

    return None
