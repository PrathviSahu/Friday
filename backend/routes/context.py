"""routes/context.py — Ambient Context Engine API (Phase 2.3).

JSON contracts per next_phase_2_architecture.md §5:
  GET  /api/context        — the live Context Vector
  POST /api/context/focus  — enable focus mode for N minutes
  POST /api/context/clear  — disable focus mode early

Owner-gated: situation awareness reads personal calendar/email signals.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_boss
from services import context_engine

router = APIRouter(prefix="/api/context", tags=["context"])


class FocusRequest(BaseModel):
    minutes: int = 60


@router.get("", dependencies=[Depends(require_boss)])
def get_context_endpoint():
    """{"time_of_day": ..., "market_open": ..., "calendar_pressure": ..., ...}"""
    return {"status": "ok", "context": context_engine.get_context()}


@router.post("/focus", dependencies=[Depends(require_boss)])
def set_focus_endpoint(req: FocusRequest):
    result = context_engine.set_focus(req.minutes)
    if result.get("status") != "ok":
        raise HTTPException(400, result.get("message", "invalid focus request"))
    return result


@router.post("/clear", dependencies=[Depends(require_boss)])
def clear_focus_endpoint():
    return context_engine.clear_focus()
