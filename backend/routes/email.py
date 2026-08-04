"""routes/email.py — Email Agent endpoints (read-only + approval-first send).

Every sensitive operation is gated by the existing permission system:
  - reading   → require_permission('email.read')    (mode: ask)
  - sending   → require_permission('email.send')    (mode: ask) + the message
                must exist as a server-side draft created via /draft
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth import require_boss
from ratelimit import is_rate_limited
from services import email_agent, permissions
from services.permissions import require_permission

router = APIRouter(prefix="/api/email", tags=["email"])


class DraftRequest(BaseModel):
    to: str
    subject: str = ""
    body: str = ""


class SendRequest(BaseModel):
    draft_id: str


def _handle_unavailable(exc: Exception):
    return HTTPException(status_code=503, detail=str(exc))


@router.get("/unread", dependencies=[Depends(require_boss), Depends(require_permission("email.read"))])
def email_unread_endpoint(limit: int = Query(15, ge=1, le=50)):
    """Recent unread emails (does NOT mark them read)."""
    try:
        return {"unread": email_agent.get_unread(limit=limit)}
    except email_agent.EmailUnavailableError as exc:
        raise _handle_unavailable(exc) from exc


@router.get("/summary", dependencies=[Depends(require_boss), Depends(require_permission("email.read"))])
def email_summary_endpoint():
    """Aggregated inbox summary (count, top senders, priority items)."""
    try:
        return {"summary": email_agent.summarize_inbox()}
    except email_agent.EmailUnavailableError as exc:
        raise _handle_unavailable(exc) from exc


@router.get("/search", dependencies=[Depends(require_boss), Depends(require_permission("email.read"))])
def email_search_endpoint(q: str = Query(..., min_length=1)):
    """Search inbox by subject/from."""
    try:
        return {"results": email_agent.search_emails(q, limit=10)}
    except email_agent.EmailUnavailableError as exc:
        raise _handle_unavailable(exc) from exc


@router.post("/draft", dependencies=[Depends(require_boss), Depends(require_permission("email.read"))])
def email_draft_endpoint(req: DraftRequest):
    """Create a server-side pending draft and return a preview for approval."""
    try:
        draft = email_agent.create_draft(req.to, req.subject, req.body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except email_agent.EmailUnavailableError as exc:
        raise _handle_unavailable(exc) from exc
    return {
        "draft_id": draft["id"],
        "preview": {
            "to": draft["to"],
            "subject": draft["subject"],
            "body": draft["body"],
        },
        "expires_in_seconds": email_agent.DRAFT_TTL_SECONDS,
    }


@router.post("/send", dependencies=[Depends(require_boss), Depends(require_permission("email.send"))])
def email_send_endpoint(req: SendRequest):
    """Send a draft created via /draft (approval-first flow)."""
    try:
        result = email_agent.send_draft(req.draft_id)
    except email_agent.EmailUnavailableError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    permissions._audit("email.send", "allowed", f"sent to {result['to']}")
    return {"status": "ok", **result}


@router.post("/cancel", dependencies=[Depends(require_boss)])
def email_cancel_endpoint(req: SendRequest):
    """Discard a pending draft without sending."""
    ok = email_agent.cancel_draft(req.draft_id)
    return {"status": "ok" if ok else "not_found"}
