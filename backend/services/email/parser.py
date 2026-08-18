"""Email approval language parser.

Differentiates explicit send approval from ambiguous confirmations or broad authorization attempts.
"""

import re
from typing import Tuple


EXPLICIT_APPROVAL_PATTERNS = [
    r"^\s*yes[,\s]+send\s+it\.?\s*$",
    r"^\s*send\s+it\.?\s*$",
    r"^\s*confirm\.?\s*$",
    r"^\s*approve\s+and\s+send\.?\s*$",
    r"^\s*yes[,\s]+send\s+email\.?\s*$",
    r"^\s*confirm\s+send\.?\s*$",
    r"^\s*send\s+email\s+now\.?\s*$",
    r"^\s*yes[,\s]+approve\.?\s*$",
]

AMBIGUOUS_PATTERNS = [
    r"^\s*okay\s*$",
    r"^\s*ok\s*$",
    r"^\s*looks\s+good\s*$",
    r"^\s*that['’]?s\s+fine\s*$",
    r"^\s*cool\s*$",
    r"^\s*do\s+it\s*$",
    r"^\s*fine\s*$",
    r"^\s*sure\s*$",
    r"^\s*next\s*$",
]

BROAD_AUTHORIZATION_PATTERNS = [
    r"send\s+emails?\s+for\s+me",
    r"always\s+send\s+emails?",
    r"send\s+all\s+emails?",
    r"auto\s*send",
    r"you\s+can\s+send\s+emails?",
    r"future\s+emails?",
]


def evaluate_user_confirmation(user_input: str) -> Tuple[bool, str]:
    """Evaluate user confirmation input string.

    Returns:
        (is_approved: bool, reason: str)
    """
    if not user_input or not user_input.strip():
        return False, "Empty user input. Explicit send approval required."

    text = user_input.strip().lower()

    # 1. Check for broad authorization attempts (FORBIDDEN)
    for pattern in BROAD_AUTHORIZATION_PATTERNS:
        if re.search(pattern, text):
            return False, (
                "Broad or future email authorization is forbidden. "
                "Approval must be explicitly confirmed for each individual email proposal."
            )

    # 2. Check for explicit approval
    for pattern in EXPLICIT_APPROVAL_PATTERNS:
        if re.match(pattern, text):
            return True, "EXPLICIT_APPROVAL"

    # 3. Check for ambiguous confirmation
    for pattern in AMBIGUOUS_PATTERNS:
        if re.match(pattern, text):
            return False, (
                f"Ambiguous confirmation '{user_input}'. "
                "Explicit send confirmation required (e.g., 'Yes, send it.' or 'Approve and send')."
            )

    return False, (
        f"Input '{user_input}' is not a recognized explicit send confirmation. "
        "Please confirm with 'Yes, send it.' or 'Approve and send'."
    )


def is_explicit_send_approval(user_input: str) -> bool:
    """Return True if user_input is an explicit send confirmation."""
    is_approved, _ = evaluate_user_confirmation(user_input)
    return is_approved
