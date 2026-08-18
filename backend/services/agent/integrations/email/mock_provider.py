"""services/agent/integrations/email/mock_provider.py — Mock Email Provider.

Provides an in-memory, deterministic email transport for automated testing,
local development, and safe dry-run execution.
"""

import time
import uuid
from typing import List, Optional, Dict, Any

from services.agent.integrations.email.provider import (
    EmailProvider,
    EmailConnectionStatus,
    ConnectionTestResult,
    EmailMessage,
    EmailDraft,
    SendResult,
    VerificationResult,
)


class MockEmailProvider(EmailProvider):
    """Deterministic in-memory email provider."""

    def __init__(self, initial_status: EmailConnectionStatus = EmailConnectionStatus.CONNECTED):
        self.status = initial_status
        self.messages: List[EmailMessage] = [
            EmailMessage(
                id="msg-101",
                thread_id="th-101",
                sender="recruiter@jpmorgan.com",
                sender_name="Sarah Jenkins (JPMorgan)",
                subject="Interview Follow-up: Software Engineer — Full Stack",
                timestamp=int(time.time() - 3600),
                preview="Hi Prem, we reviewed your Spring Boot & React projects and would love to schedule a technical round...",
                body="Hi Prem,\n\nWe reviewed your Spring Boot & React projects and would love to schedule a technical round next Tuesday.\n\nBest,\nSarah",
                is_unread=True,
                priority=True,
                provider="mock_mail"
            ),
            EmailMessage(
                id="msg-102",
                thread_id="th-102",
                sender="updates@linkedin.com",
                sender_name="LinkedIn Job Alerts",
                subject="5 New Java Spring Boot roles match your profile in Mumbai",
                timestamp=int(time.time() - 7200),
                preview="Zepto, Swiggy, and 3 other companies are hiring Java Engineers matching your profile...",
                body="Prem, check out these new job openings in Mumbai matching Java, Spring Boot, MySQL...",
                is_unread=True,
                priority=False,
                provider="mock_mail"
            ),
            EmailMessage(
                id="msg-103",
                thread_id="th-103",
                sender="careers@zeptodigitallabs.com",
                sender_name="ZDL Engineering Talent",
                subject="Application Acknowledged — SDE Trainee (Java/Spring Boot)",
                timestamp=int(time.time() - 86400),
                preview="Hi Prathvi, thanks for applying. Your profile has been forwarded to the hiring team...",
                body="Hi Prathvi,\n\nThanks for applying. Your profile has been forwarded to the engineering leads.\n\nRegards,\nZDL Recruiting",
                is_unread=False,
                priority=False,
                provider="mock_mail"
            ),
        ]
        self.drafts: Dict[str, EmailDraft] = {}
        self.sent_messages: Dict[str, SendResult] = {}

    def check_connection(self) -> EmailConnectionStatus:
        return self.status

    def test_connection(self) -> ConnectionTestResult:
        is_conn = (self.status == EmailConnectionStatus.CONNECTED)
        return ConnectionTestResult(
            status=self.status,
            imap_connected=is_conn,
            smtp_connected=is_conn,
            imap_detail="Mock IMAP service active." if is_conn else f"Mock status: {self.status.value}",
            smtp_detail="Mock SMTP service active." if is_conn else f"Mock status: {self.status.value}",
            tested_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )

    def set_connection_status(self, new_status: EmailConnectionStatus):
        self.status = new_status

    def get_messages(self, limit: int = 10, unread_only: bool = True) -> List[EmailMessage]:
        if self.status != EmailConnectionStatus.CONNECTED:
            return []
        msgs = [m for m in self.messages if (not unread_only or m.is_unread)]
        return sorted(msgs, key=lambda x: -x.timestamp)[:limit]

    def search_messages(self, query: str, limit: int = 10) -> List[EmailMessage]:
        if self.status != EmailConnectionStatus.CONNECTED:
            return []
        q = query.lower()
        matched = []
        for m in self.messages:
            if q in m.subject.lower() or q in m.sender.lower() or (m.sender_name and q in m.sender_name.lower()) or (m.preview and q in m.preview.lower()):
                matched.append(m)
        return sorted(matched, key=lambda x: -x.timestamp)[:limit]

    def create_draft(self, to: str, subject: str, body: str, attachments: Optional[List[str]] = None) -> EmailDraft:
        draft_id = f"draft-{uuid.uuid4().hex[:8]}"
        now = time.time()
        draft = EmailDraft(
            id=draft_id,
            to=to,
            subject=subject,
            body=body,
            attachments=attachments or [],
            created_at=now,
            expires_at=now + 900,  # 15 min TTL
            status="pending"
        )
        self.drafts[draft_id] = draft
        return draft

    def update_draft(self, draft_id: str, to: Optional[str] = None, subject: Optional[str] = None, body: Optional[str] = None) -> Optional[EmailDraft]:
        draft = self.drafts.get(draft_id)
        if not draft:
            return None
        if to is not None:
            draft.to = to
        if subject is not None:
            draft.subject = subject
        if body is not None:
            draft.body = body
        draft.created_at = time.time()
        draft.expires_at = time.time() + 900
        return draft

    def get_draft(self, draft_id: str) -> Optional[EmailDraft]:
        return self.drafts.get(draft_id)

    def send_message(self, to: str, subject: str, body: str, attachments: Optional[List[str]] = None, draft_id: Optional[str] = None) -> SendResult:
        if self.status != EmailConnectionStatus.CONNECTED:
            return SendResult(
                success=False,
                recipient=to,
                subject=subject,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                provider="mock_mail",
                status="failed",
                error=f"Provider unavailable: {self.status.value}"
            )

        msg_id = f"<msg-mock-{uuid.uuid4().hex[:10]}@friday.ai>"
        res = SendResult(
            success=True,
            message_id=msg_id,
            recipient=to,
            subject=subject,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            provider="mock_mail",
            status="accepted"
        )
        self.sent_messages[msg_id] = res

        if draft_id and draft_id in self.drafts:
            self.drafts[draft_id].status = "sent"

        return res

    def verify_message(self, provider_message_id: str) -> VerificationResult:
        if provider_message_id in self.sent_messages:
            return VerificationResult(
                verified=True,
                provider_message_id=provider_message_id,
                status="accepted",
                note="Email accepted by provider with valid message ID."
            )
        return VerificationResult(
            verified=False,
            provider_message_id=provider_message_id,
            status="not_found",
            note="Message ID was not found in provider dispatch ledger."
        )
