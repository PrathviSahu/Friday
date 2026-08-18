"""routes/knowledge.py — Second Brain, Memory Timeline, Goal Manager."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_boss
from services import knowledge, timeline, goals

router = APIRouter(prefix="/api", tags=["knowledge"])


# ── Second Brain (notes) ──────────────────────────────────────────────────────

class NoteCreate(BaseModel):
    title: str
    content: str = ""
    note_type: str = None
    tags: list = None
    project: str = None
    source_url: str = ""


@router.get("/knowledge", dependencies=[Depends(require_boss)])
def list_notes(note_type: str = None, project: str = None, limit: int = 100):
    return {"notes": knowledge.list_notes(note_type, project, limit),
            "types": knowledge.NOTE_TYPES}


@router.post("/knowledge", dependencies=[Depends(require_boss)])
def add_note(req: NoteCreate):
    """Add a note; type auto-categorized from text when omitted (idea capture)."""
    nid = knowledge.add_note(req.title, req.content, req.note_type,
                             req.tags, req.project, req.source_url)
    return {"status": "ok", "note_id": nid, "type": knowledge.auto_categorize(
        f"{req.title} {req.content}") if not req.note_type else req.note_type}


@router.get("/knowledge/search", dependencies=[Depends(require_boss)])
def search_notes(q: str = ""):
    """Search the second brain + natural-language recall answer."""
    matches = knowledge.search_notes(q, limit=8)
    return {"query": q, "matches": matches,
            "answer": knowledge.answer_notes_query(q)}


@router.delete("/knowledge/{note_id}", dependencies=[Depends(require_boss)])
def remove_note(note_id: int):
    ok = knowledge.delete_note(note_id)
    if not ok:
        raise HTTPException(404, "Note not found")
    return {"status": "ok"}


# ── Project Intelligence ──────────────────────────────────────────────────────

class ProjectSection(BaseModel):
    project: str
    section: str
    content: str


@router.get("/knowledge/projects", dependencies=[Depends(require_boss)])
def get_projects():
    return {"projects": knowledge.list_projects()}


@router.get("/knowledge/projects/{project}", dependencies=[Depends(require_boss)])
def get_project(project: str):
    return {"project": project, "sections": knowledge.get_project_memory(project)}


@router.put("/knowledge/projects/{project}/{section}", dependencies=[Depends(require_boss)])
def set_project_section(project: str, section: str, req: ProjectSection):
    ok = knowledge.set_project_section(project, section, req.content)
    if not ok:
        raise HTTPException(400, "Invalid project or section")
    return {"status": "ok", "project": project, "section": section}


# ── AI Memory Timeline ────────────────────────────────────────────────────────

class TimelineEventCreate(BaseModel):
    event: str
    category: str = "milestone"
    event_date: str = None
    detail: str = ""


@router.get("/timeline", dependencies=[Depends(require_boss)])
def get_timeline(category: str = None, since: str = None, until: str = None,
                 limit: int = 200):
    events = timeline.list_events(category, since, until, limit)
    return {"events": events, "auto_events": timeline.snapshot_from_existing()[:20]}


@router.post("/timeline", dependencies=[Depends(require_boss)])
def add_timeline_event(req: TimelineEventCreate):
    try:
        eid = timeline.add_event(req.event, req.category, req.event_date, req.detail)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "ok", "event_id": eid}


@router.get("/timeline/summary", dependencies=[Depends(require_boss)])
def timeline_summary(query: str = ""):
    """'What changed last month?' / 'progress this year' → summarized period."""
    since, until = timeline.period_for_query(query)
    return {"query": query, **timeline.summarize_period(since, until)}


@router.delete("/timeline/{event_id}", dependencies=[Depends(require_boss)])
def remove_timeline_event(event_id: int):
    ok = timeline.delete_event(event_id)
    if not ok:
        raise HTTPException(404, "Event not found")
    return {"status": "ok"}


# ── Goal Manager ──────────────────────────────────────────────────────────────

class GoalCreate(BaseModel):
    title: str
    category: str = "personal"
    target_value: float = 100
    unit: str = "%"
    deadline: str = ""
    skill_gaps: list = None
    resources: list = None


class GoalUpdate(BaseModel):
    title: str = None
    category: str = None
    target_value: float = None
    current_value: float = None
    unit: str = None
    deadline: str = None
    status: str = None
    skill_gaps: list = None
    resources: list = None
    notes: str = None


@router.get("/goals", dependencies=[Depends(require_boss)])
def get_goals(status: str = None):
    return {"goals": goals.list_goals(status),
            "suggested_skill_gaps": goals.suggest_skill_gaps()}


@router.post("/goals", dependencies=[Depends(require_boss)])
def add_goal(req: GoalCreate):
    try:
        gid = goals.create_goal(req.title, req.category, req.target_value,
                                req.unit, req.deadline, req.skill_gaps,
                                req.resources)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "ok", "goal_id": gid}


@router.patch("/goals/{goal_id}", dependencies=[Depends(require_boss)])
def edit_goal(goal_id: int, req: GoalUpdate):
    fields = {k: v for k, v in req.model_dump().items() if v is not None}
    ok = goals.update_goal(goal_id, **fields)
    if not ok:
        raise HTTPException(404, "Goal not found")
    return {"status": "ok"}


@router.post("/goals/{goal_id}/progress", dependencies=[Depends(require_boss)])
def add_goal_progress(goal_id: int, amount: float = 1):
    updated = goals.increment_goal(goal_id, amount)
    if not updated:
        raise HTTPException(404, "Goal not found")
    return {"status": "ok", "goal": updated}


@router.delete("/goals/{goal_id}", dependencies=[Depends(require_boss)])
def remove_goal(goal_id: int):
    ok = goals.delete_goal(goal_id)
    if not ok:
        raise HTTPException(404, "Goal not found")
    return {"status": "ok"}
