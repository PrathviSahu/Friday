"""routes/automation.py — Permission Center, Automation Engine, Notifications, Briefing."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_boss
from services import permissions
from services.automation import (
    list_automations, create_automation, update_automation,
    delete_automation, run_action,
)
from services.notifications import get_notifications, mark_read, unread_count
from services.briefing import generate_daily_briefing

router = APIRouter(prefix="/api", tags=["automation"])


# ── Permission Center ─────────────────────────────────────────────────────────

class PermissionUpdate(BaseModel):
    capability: str
    mode: str  # enabled | ask | disabled


class ApprovalRequest(BaseModel):
    capability: str
    seconds: int = 300


@router.get("/permissions")
def get_permissions_endpoint():
    """List all capabilities with their effective mode."""
    return {"permissions": permissions.get_permissions(),
            "audit": permissions.get_audit_log(limit=15)}


@router.put("/permissions", dependencies=[Depends(require_boss)])
def set_permission_endpoint(req: PermissionUpdate):
    """Update a capability's mode (owner only)."""
    ok = permissions.set_mode(req.capability, req.mode)
    if not ok:
        raise HTTPException(400, "Invalid capability or mode.")
    return {"status": "ok", "permissions": permissions.get_permissions()}


@router.post("/permissions/approve", dependencies=[Depends(require_boss)])
def grant_approval_endpoint(req: ApprovalRequest):
    """Grant a short-lived one-time approval for an 'ask' capability."""
    ok = permissions.grant_approval(req.capability, req.seconds)
    if not ok:
        raise HTTPException(400, "Unknown capability.")
    return {"status": "ok", "capability": req.capability,
            "valid_for_seconds": req.seconds}


@router.post("/permissions/revoke", dependencies=[Depends(require_boss)])
def revoke_approval_endpoint(req: ApprovalRequest):
    permissions.revoke_approval(req.capability)
    return {"status": "ok", "capability": req.capability}


# ── Automations ───────────────────────────────────────────────────────────────

class AutomationCreate(BaseModel):
    name: str
    trigger_type: str  # interval | daily
    action: str        # briefing | job_scan | market_summary
    interval_seconds: int = 0
    daily_time: str = ""
    params: dict = {}
    enabled: bool = True


class AutomationUpdate(BaseModel):
    name: str = None
    trigger_type: str = None
    interval_seconds: int = None
    daily_time: str = None
    action: str = None
    params: dict = None
    enabled: bool = None


@router.get("/automations", dependencies=[Depends(require_boss)])
def get_automations():
    return {"automations": list_automations()}


@router.post("/automations", dependencies=[Depends(require_boss)])
def add_automation(req: AutomationCreate):
    try:
        aid = create_automation(
            req.name, req.trigger_type, req.action,
            interval_seconds=req.interval_seconds,
            daily_time=req.daily_time, params=req.params, enabled=req.enabled,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "ok", "automation_id": aid}


@router.put("/automations/{automation_id}", dependencies=[Depends(require_boss)])
def edit_automation(automation_id: int, req: AutomationUpdate):
    fields = {k: v for k, v in req.model_dump().items() if v is not None}
    ok = update_automation(automation_id, **fields)
    if not ok:
        raise HTTPException(404, "Automation not found")
    return {"status": "ok"}


@router.delete("/automations/{automation_id}", dependencies=[Depends(require_boss)])
def remove_automation(automation_id: int):
    ok = delete_automation(automation_id)
    if not ok:
        raise HTTPException(404, "Automation not found")
    return {"status": "ok"}


@router.post("/automations/{automation_id}/run", dependencies=[Depends(require_boss)])
def run_automation_now(automation_id: int):
    for a in list_automations():
        if a["id"] == automation_id:
            import json
            summary = run_action(a["action"], json.loads(a.get("params") or "{}"))
            return {"status": "ok", "summary": summary}
    raise HTTPException(404, "Automation not found")


# ── Notifications ─────────────────────────────────────────────────────────────

@router.get("/notifications")
def get_notifications_endpoint(unread_only: bool = False, limit: int = 50):
    items = get_notifications(limit=limit, unread_only=unread_only)
    return {"notifications": items, "unread_count": unread_count()}


@router.post("/notifications/{notification_id}/read", dependencies=[Depends(require_boss)])
def read_notification(notification_id: int):
    ok = mark_read(notification_id)
    if not ok:
        raise HTTPException(404, "Notification not found")
    return {"status": "ok"}


# ── Briefing ──────────────────────────────────────────────────────────────────

@router.get("/briefing")
def briefing_endpoint():
    """Generate the smart daily briefing on demand."""
    return generate_daily_briefing()
