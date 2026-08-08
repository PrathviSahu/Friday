"""routes/autonomy.py — Autonomy & Trust Engine API (Phase 2.1).

JSON contracts per next_phase_2_architecture.md §5:
  GET  /api/autonomy/status     — trust ledger + budget (HUD Autonomy panel)
  GET  /api/autonomy/journal    — "what FRIDAY did for me today"
  POST /api/autonomy/undo       — undo one journaled execution (300s window)
  POST /api/autonomy/revoke     — force an action back to 'confirm' tier

All endpoints are owner-gated: autonomous control is the most sensitive
surface in the system.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import require_boss
from services import autonomy_engine

router = APIRouter(prefix="/api/autonomy", tags=["autonomy"])


class UndoRequest(BaseModel):
    journal_id: int


class RevokeRequest(BaseModel):
    action_type: str


@router.get("/status", dependencies=[Depends(require_boss)])
def autonomy_status():
    """{"status": "ok", "actions": [...], "budget": {...}, "budget_remaining": int}"""
    data = autonomy_engine.get_status()
    return {"status": "ok", **data}


@router.get("/journal", dependencies=[Depends(require_boss)])
def autonomy_journal(date: str | None = None):
    """Journal entries for ?date=YYYY-MM-DD (default: today, local time)."""
    entries = autonomy_engine.get_journal(date)
    return {"status": "ok", "date": date, "entries": entries}


@router.post("/undo", dependencies=[Depends(require_boss)])
def autonomy_undo(req: UndoRequest):
    result = autonomy_engine.undo(req.journal_id)
    if result.get("status") != "ok":
        return {"status": "error", "undone": False, "message": result.get("message")}
    return result


@router.post("/revoke", dependencies=[Depends(require_boss)])
def autonomy_revoke(req: RevokeRequest):
    return autonomy_engine.revoke(req.action_type)
