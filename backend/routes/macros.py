"""routes/macros.py — Voice Macro & Workflow Composer API (Phase 2.4).

JSON contracts per next_phase_2_architecture.md §5:
  POST   /api/macros            — create (201) {"trigger_phrase", "steps"}
  GET    /api/macros            — list with recent run history
  DELETE /api/macros/{id}       — remove
  POST   /api/macros/{id}/run   — execute ({"force": true} = owner approval)

All owner-gated: macros execute real tool chains.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_boss
from services import macros

router = APIRouter(prefix="/api/macros", tags=["macros"])


class MacroCreate(BaseModel):
    trigger_phrase: str
    steps: list
    created_by: str = "hud"


class MacroRunRequest(BaseModel):
    force: bool = False


@router.post("", status_code=201, dependencies=[Depends(require_boss)])
def create_macro_endpoint(req: MacroCreate):
    try:
        return macros.create_macro(req.trigger_phrase, req.steps, req.created_by)
    except macros.MacroError as err:
        msg = str(err)
        code = 409 if "already exists" in msg else 400
        raise HTTPException(code, msg)


@router.get("", dependencies=[Depends(require_boss)])
def list_macros_endpoint():
    return {"status": "ok", "macros": macros.list_macros()}


@router.delete("/{macro_id}", dependencies=[Depends(require_boss)])
def delete_macro_endpoint(macro_id: int):
    result = macros.delete_macro(macro_id=macro_id)
    if result["status"] != "ok":
        raise HTTPException(404, result["message"])
    return result


@router.post("/{macro_id}/run", dependencies=[Depends(require_boss)])
def run_macro_endpoint(macro_id: int, req: MacroRunRequest):
    result = macros.run_macro(macro_id=macro_id, force=req.force)
    if result.get("message") == "macro not found":
        raise HTTPException(404, "macro not found")
    return result
