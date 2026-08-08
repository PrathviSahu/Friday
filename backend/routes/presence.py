"""routes/presence.py — Cross-Device Presence API (Phase 2.5).

JSON contracts per next_phase_2_architecture.md §5:
  POST   /api/presence/register         — register a device (pwa / telegram)
  GET    /api/presence/devices          — list registered devices
  DELETE /api/presence/devices/{id}     — unregister
  GET    /api/presence/pending          — pending approvals (polled by the SW)
  POST   /api/presence/ask              — create + push an approval
  POST   /api/presence/decision         — resolve one (approve/deny)
  GET    /api/presence/vapid-key        — public key for push subscription

Security: every route is owner-gated; decisions only RESOLVE approvals (they
grant the specific capability they were created for) — devices can never mint
or modify capabilities.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_boss
from services import presence

router = APIRouter(prefix="/api/presence", tags=["presence"])


class RegisterRequest(BaseModel):
    device_kind: str
    token: str
    label: str = ""


class AskRequest(BaseModel):
    capability: str
    description: str = ""
    action: dict | None = None


class DecisionRequest(BaseModel):
    approval_token: str
    decision: str  # 'approve' | 'deny'


@router.post("/register", dependencies=[Depends(require_boss)])
def register_device_endpoint(req: RegisterRequest):
    result = presence.register_device(req.device_kind, req.token, req.label)
    if result["status"] != "ok":
        raise HTTPException(400, result["message"])
    return result


@router.get("/devices", dependencies=[Depends(require_boss)])
def list_devices_endpoint():
    return {"status": "ok", "devices": presence.list_devices()}


@router.delete("/devices/{device_id}", dependencies=[Depends(require_boss)])
def remove_device_endpoint(device_id: int):
    result = presence.remove_device(device_id=device_id)
    if result["status"] != "ok":
        raise HTTPException(404, result["message"])
    return result


@router.get("/pending", dependencies=[Depends(require_boss)])
def list_pending_endpoint():
    return {"status": "ok", "pending": presence.list_pending()}


@router.post("/ask", dependencies=[Depends(require_boss)])
def create_approval_endpoint(req: AskRequest):
    result = presence.create_approval(req.capability, req.description, req.action)
    if result["status"] != "ok":
        raise HTTPException(400, result["message"])
    return result


@router.post("/decision", dependencies=[Depends(require_boss)])
def resolve_decision_endpoint(req: DecisionRequest):
    result = presence.resolve_decision(req.approval_token, req.decision)
    if result.get("status") != "ok":
        return {"status": "error", "message": result.get("message")}
    return result


@router.get("/vapid-key", dependencies=[Depends(require_boss)])
def vapid_key_endpoint():
    import os
    return {"status": "ok", "public_key": os.getenv("VAPID_PUBLIC_KEY", "")}
