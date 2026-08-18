"""Email approval token lifecycle & validation module.

Manages single-use, time-limited, version-bound approval tokens for email send requests.
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List

from .draft import Draft, get_draft, compute_content_hash
from .config import is_live_execution_enabled


@dataclass
class PendingApproval:
    approval_id: str
    draft_id: str
    content_hash: str
    recipient: str
    subject: str
    body_version: int
    created_at: float
    expires_at: float
    consumed_at: Optional[float] = None
    status: str = "PENDING"  # PENDING, EXPIRED, INVALIDATED, CONSUMED

    def is_expired(self, now: Optional[float] = None) -> bool:
        current_time = now if now is not None else time.time()
        return current_time > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "draft_id": self.draft_id,
            "content_hash": self.content_hash,
            "recipient": self.recipient,
            "subject": self.subject,
            "body_version": self.body_version,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "consumed_at": self.consumed_at,
            "status": self.status,
        }


_approval_store: Dict[str, PendingApproval] = {}
_draft_approvals: Dict[str, List[str]] = {}  # draft_id -> list of approval_ids


def create_approval_token(draft: Draft, ttl_seconds: int = 300) -> PendingApproval:
    """Generate a single-use approval token scoped to a specific draft version and content hash.

    TTL is capped at 5 minutes (300 seconds) maximum.
    """
    actual_ttl = min(ttl_seconds, 300)
    now = time.time()
    expires_at = now + actual_ttl
    approval_id = f"appr_{uuid.uuid4().hex[:12]}"

    approval = PendingApproval(
        approval_id=approval_id,
        draft_id=draft.draft_id,
        content_hash=draft.content_hash,
        recipient=draft.recipient,
        subject=draft.subject,
        body_version=draft.version,
        created_at=now,
        expires_at=expires_at,
        consumed_at=None,
        status="PENDING",
    )

    _approval_store[approval_id] = approval
    if draft.draft_id not in _draft_approvals:
        _draft_approvals[draft.draft_id] = []
    _draft_approvals[draft.draft_id].append(approval_id)

    return approval


def get_approval(approval_id: str) -> Optional[PendingApproval]:
    """Retrieve an approval token by ID."""
    return _approval_store.get(approval_id)


def invalidate_approvals_for_draft(draft_id: str, reason: str = "draft_modified") -> List[str]:
    """Invalidate all pending approval tokens associated with a draft due to modification or cancellation."""
    invalidated_ids = []
    approval_ids = _draft_approvals.get(draft_id, [])
    for app_id in approval_ids:
        appr = _approval_store.get(app_id)
        if appr and appr.status == "PENDING":
            appr.status = "INVALIDATED"
            invalidated_ids.append(app_id)
    return invalidated_ids


def consume_approval_token(approval_id: str) -> bool:
    """Mark an approval token as CONSUMED immediately upon successful dispatch."""
    appr = _approval_store.get(approval_id)
    if appr and appr.status == "PENDING":
        appr.status = "CONSUMED"
        appr.consumed_at = time.time()
        return True
    return False


def validate_approval(
    approval_id: str,
    draft_id: str,
    session_user: str = "Prem",
    now: Optional[float] = None
) -> Tuple[bool, str, Optional[PendingApproval]]:
    """Validate approval against ALL 10 Step 3 Verification Checks.

    Returns (is_valid, failure_reason, approval_object).
    """
    current_time = now if now is not None else time.time()

    # Check 1: Token exists
    if not approval_id:
        return False, "Missing approval token.", None

    approval = _approval_store.get(approval_id)
    if not approval:
        return False, f"Approval token '{approval_id}' not found.", None

    # Check 2: Token has not expired
    if approval.is_expired(now=current_time):
        approval.status = "EXPIRED"
        return False, f"Approval token '{approval_id}' has expired (TTL: 5 mins).", approval

    # Check 3: Token has not already been consumed
    if approval.status == "CONSUMED":
        return False, f"Approval token '{approval_id}' has already been consumed.", approval

    # Check 4: Token is in PENDING state (not INVALIDATED or EXPIRED)
    if approval.status == "INVALIDATED":
        return False, f"The draft changed after the previous approval, so I need a new approval for the revised email.", approval

    if approval.status != "PENDING":
        return False, f"Approval token '{approval_id}' is in invalid state '{approval.status}'.", approval

    # Check 5: Draft exists
    draft = get_draft(draft_id)
    if not draft:
        return False, f"Draft '{draft_id}' associated with approval token does not exist.", approval

    # Check 6: Draft status is eligible
    if draft.status == "SENT":
        return False, f"Draft '{draft_id}' has already been SENT.", approval
    if draft.status == "CANCELLED":
        return False, f"Draft '{draft_id}' has been CANCELLED.", approval

    # Check 7: Draft content_hash EXACTLY matches approval content_hash
    if draft.content_hash != approval.content_hash:
        approval.status = "INVALIDATED"
        return False, "The draft changed after the previous approval, so I need a new approval for the revised email.", approval

    # Check 8: Recipient matches
    if draft.recipient != approval.recipient:
        approval.status = "INVALIDATED"
        return False, "Recipient mismatch: draft recipient does not match approval token.", approval

    # Check 9: Subject & Version match
    if draft.subject != approval.subject or draft.version != approval.body_version:
        approval.status = "INVALIDATED"
        return False, "The draft changed after the previous approval, so I need a new approval for the revised email.", approval

    # Check 10: Session authorization check (User MUST be authorized 'Prem' or 'boss')
    if not session_user or session_user.lower() not in ("prem", "boss", "owner"):
        return False, f"Unauthorized session user '{session_user}'. Only Prem can authorize sending email.", approval

    return True, "", approval


def clear_approval_store():
    """Clear in-memory approval store for tests."""
    _approval_store.clear()
    _draft_approvals.clear()
