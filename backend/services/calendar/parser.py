"""Calendar approval language parser.

Differentiates explicit event creation approval from ambiguous confirmations or broad authorization attempts.
"""

import re
from typing import Tuple


EXPLICIT_CALENDAR_APPROVAL_PATTERNS = [
    r"^\s*yes[,\s]+create\s+it\.?\s*$",
    r"^\s*create\s+it\.?\s*$",
    r"^\s*confirm\.?\s*$",
    r"^\s*approve\s+and\s+create\.?\s*$",
    r"^\s*yes[,\s]+schedule\s+it\.?\s*$",
    r"^\s*confirm\s+event\.?\s*$",
    r"^\s*add\s+to\s+calendar\.?\s*$",
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
    r"create\s+events?\s+for\s+me",
    r"always\s+create\s+events?",
    r"auto\s*create\s+events?",
    r"schedule\s+all\s+events?",
    r"you\s+can\s+create\s+events?",
]


def evaluate_calendar_confirmation(user_input: str) -> Tuple[bool, str]:
    """Evaluate user confirmation string for calendar creation.

    Returns:
        (is_approved: bool, reason: str)
    """
    if not user_input or not user_input.strip():
        return False, "Empty user input. Explicit event creation approval required."

    text = user_input.strip().lower()

    # 1. Check for broad authorization attempts (FORBIDDEN)
    for pattern in BROAD_AUTHORIZATION_PATTERNS:
        if re.search(pattern, text):
            return False, (
                "Broad or future calendar authorization is forbidden. "
                "Approval must be explicitly confirmed for each individual calendar event proposal."
            )

    # 2. Check for explicit approval
    for pattern in EXPLICIT_CALENDAR_APPROVAL_PATTERNS:
        if re.match(pattern, text):
            return True, "EXPLICIT_APPROVAL"

    # 3. Check for ambiguous confirmation
    for pattern in AMBIGUOUS_PATTERNS:
        if re.match(pattern, text):
            return False, (
                f"Ambiguous confirmation '{user_input}'. "
                "Explicit creation confirmation required (e.g., 'Yes, create it.' or 'Approve and create')."
            )

    return False, (
        f"Input '{user_input}' is not a recognized explicit calendar event creation confirmation. "
        "Please confirm with 'Yes, create it.' or 'Approve and create'."
    )


def is_explicit_calendar_approval(user_input: str) -> bool:
    """Return True if user_input is an explicit calendar creation confirmation."""
    is_approved, _ = evaluate_calendar_confirmation(user_input)
    return is_approved
