"""routes/learning.py — Personal Learning Coach endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_boss
from services.learning import get_dashboard, log_session

router = APIRouter(prefix="/api", tags=["learning"])


class LearningLogRequest(BaseModel):
    title: str
    category: str = "general"
    minutes: int = 30
    solved: int = 0


@router.get("/learning")
def learning_dashboard():
    """Coach dashboard: streak, today, weekly goals, last-7-days activity."""
    return get_dashboard()


@router.get("/learning/streak")
def learning_streak():
    from services.learning import _streak_data
    current, best, last = _streak_data()
    return {"current_streak": current, "best_streak": best,
            "last_activity_date": last}


@router.post("/learning/log", dependencies=[Depends(require_boss)])
def add_learning_log(req: LearningLogRequest):
    """Record a practice session (owner only)."""
    if req.minutes < 1:
        raise HTTPException(400, "minutes must be >= 1")
    log_id = log_session(req.title, req.category, req.minutes, req.solved)
    return {"status": "ok", "log_id": log_id, "dashboard": get_dashboard()}
