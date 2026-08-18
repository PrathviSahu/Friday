"""Email draft preparation engine (Level 1 PREPARATION ONLY).

Drafts emails without sending them. Draft != Send Invariant is strictly enforced.
"""

import hashlib
import uuid
import re
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"send\s+(all\s+)?emails?\s+to",
    r"bypass\s+approval",
    r"override\s+security",
    r"system:\s*send",
]


class DraftValidationError(Exception):
    """Raised when email draft validation fails."""
    pass


class PromptInjectionDetectedError(Exception):
    """Raised when prompt injection is detected within email content."""
    pass


@dataclass
class Draft:
    draft_id: str
    recipient: str
    subject: str
    body: str
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    version: int = 1
    content_hash: str = ""
    status: str = "PENDING"  # PENDING, MODIFIED, APPROVED, SENT, CANCELLED
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "recipient": self.recipient,
            "subject": self.subject,
            "body": self.body,
            "attachments": self.attachments,
            "version": self.version,
            "content_hash": self.content_hash,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def compute_content_hash(recipient: str, subject: str, body: str, attachments: Optional[List[Dict[str, Any]]] = None) -> str:
    """Compute SHA256 hash of canonical draft representation."""
    canonical_recipient = recipient.strip().lower()
    canonical_subject = subject.strip()
    canonical_body = body.strip()

    attachments_str = ""
    if attachments:
        sorted_atts = sorted(attachments, key=lambda x: x.get("name", ""))
        attachments_str = "|".join(f"{a.get('name','')}:{a.get('size',0)}" for a in sorted_atts)

    payload = f"{canonical_recipient}\n{canonical_subject}\n{canonical_body}\n{attachments_str}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def detect_prompt_injection(text: str):
    """Check text for known prompt injection attack patterns."""
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            raise PromptInjectionDetectedError(
                f"SECURITY GUARD: Prompt injection pattern detected matching '{pattern}'."
            )


def validate_recipient(recipient: str):
    """Validate recipient email address format."""
    if not recipient or not recipient.strip():
        raise DraftValidationError("Recipient email address cannot be empty.")
    if "@" not in recipient or "." not in recipient.split("@")[-1]:
        raise DraftValidationError(f"Invalid email recipient format: '{recipient}'.")


def validate_attachments(attachments: Optional[List[Dict[str, Any]]]):
    """Validate attachments list."""
    if not attachments:
        return
    for att in attachments:
        if not isinstance(att, dict) or "name" not in att:
            raise DraftValidationError("Invalid attachment structure. Each attachment must have a 'name'.")
        # Ensure attachment size is reasonable (< 25MB)
        if att.get("size", 0) > 25 * 1024 * 1024:
            raise DraftValidationError(f"Attachment '{att.get('name')}' exceeds maximum 25MB limit.")


_draft_store: Dict[str, Draft] = {}


def draft_email(recipient: str, subject: str, body: str, attachments: Optional[List[Dict[str, Any]]] = None) -> Draft:
    """Level 1 PREPARATION: Create an email draft.

    CRITICAL INVARIANT: This function ONLY creates a draft. It CANNOT send mail.
    """
    validate_recipient(recipient)
    detect_prompt_injection(subject)
    detect_prompt_injection(body)
    validate_attachments(attachments)

    now_iso = datetime.now(timezone.utc).isoformat()
    draft_id = f"draft_{uuid.uuid4().hex[:12]}"
    content_hash = compute_content_hash(recipient, subject, body, attachments)

    draft = Draft(
        draft_id=draft_id,
        recipient=recipient.strip(),
        subject=subject.strip(),
        body=body.strip(),
        attachments=attachments or [],
        version=1,
        content_hash=content_hash,
        status="PENDING",
        created_at=now_iso,
        updated_at=now_iso,
    )

    _draft_store[draft_id] = draft
    return draft


def get_draft(draft_id: str) -> Optional[Draft]:
    """Retrieve a draft by ID."""
    return _draft_store.get(draft_id)


def update_draft(
    draft_id: str,
    new_body: Optional[str] = None,
    new_subject: Optional[str] = None,
    new_recipient: Optional[str] = None,
    new_attachments: Optional[List[Dict[str, Any]]] = None,
) -> Draft:
    """Update an existing draft, incrementing version and recomputing content_hash."""
    draft = _draft_store.get(draft_id)
    if not draft:
        raise DraftValidationError(f"Draft '{draft_id}' not found.")

    if draft.status == "SENT":
        raise DraftValidationError(f"Cannot modify draft '{draft_id}' as it has already been SENT.")

    updated_recipient = new_recipient.strip() if new_recipient is not None else draft.recipient
    updated_subject = new_subject.strip() if new_subject is not None else draft.subject
    updated_body = new_body.strip() if new_body is not None else draft.body
    updated_attachments = new_attachments if new_attachments is not None else draft.attachments

    validate_recipient(updated_recipient)
    detect_prompt_injection(updated_subject)
    detect_prompt_injection(updated_body)
    validate_attachments(updated_attachments)

    now_iso = datetime.now(timezone.utc).isoformat()
    new_hash = compute_content_hash(updated_recipient, updated_subject, updated_body, updated_attachments)

    draft.recipient = updated_recipient
    draft.subject = updated_subject
    draft.body = updated_body
    draft.attachments = updated_attachments
    draft.version += 1
    draft.content_hash = new_hash
    draft.status = "MODIFIED"
    draft.updated_at = now_iso

    return draft


def clear_draft_store():
    """Clear in-memory draft store for tests."""
    _draft_store.clear()
