"""routes/devtools.py — Developer Mode (v3.2): overview, memory viewer,
log tail, safe config inspection, and an in-process API tester."""

import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_boss
from services.devtools import get_log_tail, get_uptime_seconds

router = APIRouter(prefix="/api", tags=["devtools"])

VERSION = "3.2.0"


class ApiTestRequest(BaseModel):
    method: str = "GET"
    path: str = "/api/system/stats"
    body: dict = None


@router.get("/dev/overview", dependencies=[Depends(require_boss)])
def dev_overview():
    """Counts of everything FRIDAY knows + uptime."""
    from services.learning_engine import get_all_memories
    from services.life_memory import list_memories
    from services.automation import list_automations
    from services.notifications import unread_count, get_notifications
    from services.todos import get_todos

    counts = {
        "facts": len(get_all_memories()),
        "life_memories": len(list_memories(limit=1000)),
        "automations": len(list_automations()),
        "notifications_unread": unread_count(),
        "notifications_total": len(get_notifications(limit=1000)),
        "todos_pending": len([t for t in get_todos() if not t.get("done")]),
        "uptime_seconds": get_uptime_seconds(),
    }
    try:
        from services.career_db import get_dashboard_stats
        s = get_dashboard_stats() or {}
        counts["applications"] = s.get("application_count", 0)
    except Exception:
        pass
    return counts


@router.get("/dev/memory", dependencies=[Depends(require_boss)])
def dev_memory():
    """Facts + life-memory triples + recent conversations (owner only)."""
    from services.memory import get_all_memories
    from services.learning_engine import get_recent_conversation
    from services.life_memory import list_memories
    return {
        "facts": get_all_memories(),
        "life_memories": list_memories(limit=100),
        "recent_conversations": get_recent_conversation(10),
    }


@router.get("/dev/logs", dependencies=[Depends(require_boss)])
def dev_logs(lines: int = 200):
    """Tail recent backend logs (owner only)."""
    lines = max(10, min(int(lines), 2000))
    return {"logs": get_log_tail(lines)}


@router.get("/dev/config", dependencies=[Depends(require_boss)])
def dev_config():
    """Safe config inspection: which keys are set (booleans only, never values)
    + permission modes (owner only)."""
    import os
    keys = ["GROQ_API_KEY", "GEMINI_API_KEY", "SPOTIFY_CLIENT_ID",
            "SPOTIFY_CLIENT_SECRET", "FRIDAY_API_TOKEN", "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_OWNER_ID", "FRIDAY_VAULT_KEY"]
    stubs = {"your_key_here", "your_spotify_client_id",
             "your_spotify_client_secret", "generated_by_spotify_auth_setup_py"}
    env = {}
    for k in keys:
        v = os.getenv(k, "").strip()
        env[k] = bool(v) and v not in stubs
    from services.permissions import get_permissions
    perms = {p["capability"]: p["mode"] for p in get_permissions()}
    return {
        "version": VERSION,
        "env": env,
        "permissions": perms,
        "cors_origins": ["http://localhost:5173", "http://127.0.0.1:5173",
                         "http://localhost:3000", "http://127.0.0.1:3000"],
    }


@router.post("/dev/test", dependencies=[Depends(require_boss)])
async def dev_api_test(req: ApiTestRequest):
    """In-process API tester: run any GET/POST/PUT/PATCH/DELETE against the app."""
    import httpx
    from app import app  # lazy import avoids circularity

    method = req.method.upper()
    if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        raise HTTPException(400, "Unsupported method")
    if not req.path.startswith("/"):
        raise HTTPException(400, "path must start with '/'")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        try:
            resp = await client.request(method, req.path, json=req.body, timeout=30)
        except Exception as e:
            return {"status": 0, "data": f"Request failed: {e}"}
    try:
        data = resp.json()
    except Exception:
        data = resp.text[:2000]
    return {"status": resp.status_code, "data": data}
