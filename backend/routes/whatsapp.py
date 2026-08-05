"""routes/whatsapp.py — WhatsApp Agent endpoints (experimental driver).

Read gated by `whatsapp.read`, send gated by `whatsapp.send` (both
default 'ask') + a server-side draft created via /draft — the same
approval-first pattern as email and calendar.

Also includes WhatsApp Desktop (native macOS app) endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth import require_boss
from services import whatsapp_agent
from services.system_control import send_whatsapp_desktop
from services.permissions import require_permission

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])


class DraftRequest(BaseModel):
    phone: str
    message: str


class SendRequest(BaseModel):
    draft_id: str


class DesktopSendRequest(BaseModel):
    phone: str
    message: str


def _unavailable(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


@router.get("/status", dependencies=[Depends(require_boss)])
def whatsapp_status_endpoint():
    """Driver state + pairing hint (no permission needed)."""
    return whatsapp_agent.get_status()


@router.get("/qr", dependencies=[Depends(require_boss)])
def whatsapp_qr_endpoint():
    """Current pairing QR as a PNG data URL (poll while pairing)."""
    try:
        return whatsapp_agent.get_qr()
    except whatsapp_agent.WhatsAppUnavailableError as exc:
        raise _unavailable(exc) from exc


@router.get("/chats", dependencies=[Depends(require_boss), Depends(require_permission("whatsapp.read"))])
def whatsapp_chats_endpoint(limit: int = Query(20, ge=1, le=50)):
    try:
        return {"chats": whatsapp_agent.get_chats(limit=limit)}
    except whatsapp_agent.WhatsAppUnavailableError as exc:
        raise _unavailable(exc) from exc


@router.get("/search", dependencies=[Depends(require_boss), Depends(require_permission("whatsapp.read"))])
def whatsapp_search_endpoint(q: str = Query(..., min_length=1)):
    try:
        return {"results": whatsapp_agent.search_messages(q)}
    except whatsapp_agent.WhatsAppUnavailableError as exc:
        raise _unavailable(exc) from exc


@router.post("/draft", dependencies=[Depends(require_boss), Depends(require_permission("whatsapp.read"))])
def whatsapp_draft_endpoint(req: DraftRequest):
    """Create a server-side pending message draft + preview (no send)."""
    try:
        draft = whatsapp_agent.create_draft(req.phone, req.message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except whatsapp_agent.WhatsAppUnavailableError as exc:
        raise _unavailable(exc) from exc
    return {
        "draft_id": draft["id"],
        "preview": {"phone": draft["phone"], "message": draft["message"]},
        "expires_in_seconds": whatsapp_agent.DRAFT_TTL_SECONDS,
    }


@router.post("/send", dependencies=[Depends(require_boss), Depends(require_permission("whatsapp.send"))])
def whatsapp_send_endpoint(req: SendRequest):
    """Send a draft created via /draft (approval-first flow)."""
    try:
        result = whatsapp_agent.send_draft(req.draft_id)
    except whatsapp_agent.WhatsAppUnavailableError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok", **result}


@router.post("/cancel", dependencies=[Depends(require_boss)])
def whatsapp_cancel_endpoint(req: SendRequest):
    ok = whatsapp_agent.cancel_draft(req.draft_id)
    return {"status": "ok" if ok else "not_found"}


# ── WhatsApp Desktop (native macOS app) ─────────────────────────────────

@router.post("/desktop-send", dependencies=[Depends(require_boss), Depends(require_permission("whatsapp.send"))])
def whatsapp_desktop_send_endpoint(req: DesktopSendRequest):
    """Send a message via the WhatsApp Desktop app on macOS (native, no Playwright)."""
    result = send_whatsapp_desktop(req.phone, req.message)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed"))
    return result
