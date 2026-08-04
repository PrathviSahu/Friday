"""routes/calendar.py — Calendar Agent endpoints.

Read gated by `calendar.read`, create gated by `calendar.write` + a
server-side draft created via /draft (approval-first, same as email).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth import require_boss
from services import calendar_agent
from services.permissions import require_permission

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


class EventDraftRequest(BaseModel):
    summary: str
    start: str
    end: str = ""
    description: str = ""


class CreateRequest(BaseModel):
    draft_id: str


def _unavailable(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


@router.get("/status", dependencies=[Depends(require_boss)])
def calendar_status_endpoint():
    """Connection status + setup hint (no permission needed)."""
    status = calendar_agent.get_status()
    return {
        **status,
        "configured": calendar_agent.is_configured(),
        "hint": (
            "Create a Google Cloud OAuth client with the Calendar API enabled, "
            "save it as backend/credentials.json, and re-check this endpoint."
        ) if not calendar_agent.is_configured() else "",
    }


@router.get("/today", dependencies=[Depends(require_boss), Depends(require_permission("calendar.read"))])
def calendar_today_endpoint():
    try:
        return {"events": calendar_agent.get_today()}
    except calendar_agent.CalendarUnavailableError as exc:
        raise _unavailable(exc) from exc


@router.get("/upcoming", dependencies=[Depends(require_boss), Depends(require_permission("calendar.read"))])
def calendar_upcoming_endpoint(days: int = Query(7, ge=1, le=60), max_results: int = Query(20, ge=1, le=50)):
    try:
        return {"events": calendar_agent.get_upcoming(days=days, max_results=max_results)}
    except calendar_agent.CalendarUnavailableError as exc:
        raise _unavailable(exc) from exc


@router.get("/search", dependencies=[Depends(require_boss), Depends(require_permission("calendar.read"))])
def calendar_search_endpoint(q: str = Query(..., min_length=1)):
    try:
        return {"events": calendar_agent.search_events(q)}
    except calendar_agent.CalendarUnavailableError as exc:
        raise _unavailable(exc) from exc


@router.post("/draft", dependencies=[Depends(require_boss), Depends(require_permission("calendar.read"))])
def calendar_draft_endpoint(req: EventDraftRequest):
    """Create a server-side pending event draft + preview (no write yet)."""
    try:
        draft = calendar_agent.create_draft(req.summary, req.start, req.end, req.description)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "draft_id": draft["id"],
        "preview": {
            "summary": draft["summary"],
            "start": draft["start"],
            "end": draft["end"],
            "description": draft["description"],
        },
        "expires_in_seconds": calendar_agent.DRAFT_TTL_SECONDS,
    }


@router.post("/create", dependencies=[Depends(require_boss), Depends(require_permission("calendar.write"))])
def calendar_create_endpoint(req: CreateRequest):
    """Create an event from a draft created via /draft (approval-first)."""
    try:
        result = calendar_agent.create_from_draft(req.draft_id)
    except calendar_agent.CalendarUnavailableError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok", **result}


@router.post("/cancel", dependencies=[Depends(require_boss)])
def calendar_cancel_endpoint(req: CreateRequest):
    ok = calendar_agent.cancel_draft(req.draft_id)
    return {"status": "ok" if ok else "not_found"}
