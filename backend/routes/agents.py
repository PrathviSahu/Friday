"""routes/agents.py — Multi-Agent framework endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import require_boss
from services.agents import list_agents, handle_with_agent, route_to_agent

router = APIRouter(prefix="/api", tags=["agents"])


class AgentChatRequest(BaseModel):
    text: str


@router.get("/agents", dependencies=[Depends(require_boss)])
def get_agents():
    """List all registered FRIDAY agents and their tool counts."""
    return {"agents": list_agents()}


@router.post("/agent/chat", dependencies=[Depends(require_boss)])
def agent_chat(req: AgentChatRequest):
    """Route a request to the best-fit agent and run its filtered brain."""
    result = handle_with_agent(req.text, is_boss=True)
    return result


@router.get("/agent/route", dependencies=[Depends(require_boss)])
def agent_route(text: str = ""):
    """Show which agent would handle a given text (debug helper)."""
    return {"text": text, "agent": route_to_agent(text)}
