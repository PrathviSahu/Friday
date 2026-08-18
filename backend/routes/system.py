"""routes/system.py — macOS system control, display, app launch, telemetry."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import require_boss, require_public_demo
from services.permissions import require_permission
from services.system_control import open_app, close_app
from services.system_stats import get_system_stats
from services.mac_controls import (
    get_display_status,
    set_brightness,
    set_dark_mode,
    set_system_volume,
    set_system_mute,
    lock_display,
)

router = APIRouter(prefix="/api", tags=["system"])


class AppRequest(BaseModel):
    app: str


class BrightnessRequest(BaseModel):
    level: float


class DarkModeRequest(BaseModel):
    enabled: bool


class VolumeRequest(BaseModel):
    level: int


class MuteRequest(BaseModel):
    muted: bool


@router.post("/open-app", dependencies=[Depends(require_boss), Depends(require_permission('system.control'))])
def open_app_endpoint(req: AppRequest):
    """Open a macOS application."""
    ok = open_app(req.app)
    return {"status": "ok" if ok else "error", "app": req.app}


@router.post("/close-app", dependencies=[Depends(require_boss), Depends(require_permission('system.control'))])
def close_app_endpoint(req: AppRequest):
    """Close a macOS application."""
    ok = close_app(req.app)
    return {"status": "ok" if ok else "error", "app": req.app}


@router.get("/system/display", dependencies=[Depends(require_boss)])
def get_display_endpoint():
    """Return live brightness, dark mode, system volume, and mute status."""
    return get_display_status()


@router.post("/system/display/brightness", dependencies=[Depends(require_boss), Depends(require_permission('system.control'))])
def set_brightness_endpoint(req: BrightnessRequest):
    """Set main display brightness (0-100 or 0.0-1.0)."""
    ok = set_brightness(req.level)
    return {"status": "ok" if ok else "error", "brightness": req.level}


@router.post("/system/display/dark-mode", dependencies=[Depends(require_boss), Depends(require_permission('system.control'))])
def set_dark_mode_endpoint(req: DarkModeRequest):
    """Toggle macOS Dark Mode on or off."""
    ok = set_dark_mode(req.enabled)
    return {"status": "ok" if ok else "error", "dark_mode": req.enabled}


@router.post("/system/display/volume", dependencies=[Depends(require_boss), Depends(require_permission('system.control'))])
def set_volume_endpoint(req: VolumeRequest):
    """Set system output volume (0-100)."""
    ok = set_system_volume(req.level)
    return {"status": "ok" if ok else "error", "volume": req.level}


@router.post("/system/display/mute", dependencies=[Depends(require_boss), Depends(require_permission('system.control'))])
def set_mute_endpoint(req: MuteRequest):
    """Mute or unmute system audio output."""
    ok = set_system_mute(req.muted)
    return {"status": "ok" if ok else "error", "muted": req.muted}


@router.post("/system/display/lock", dependencies=[Depends(require_boss), Depends(require_permission('system.control'))])
def lock_display_endpoint():
    """Immediately lock display / trigger screen saver."""
    ok = lock_display()
    return {"status": "ok" if ok else "error"}


@router.get("/system/stats", dependencies=[Depends(require_public_demo)])
def system_stats_endpoint():
    """Return live CPU, RAM, Disk, and Battery stats."""
    return get_system_stats()
