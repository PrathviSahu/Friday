"""routes/meetings.py — Meeting Assistant endpoints.

Create from uploaded audio (reuses the free-tier Groq Whisper STT engine)
or from a pasted transcript. Everything is stored locally and mirrored
into the Knowledge OS. Action items can be pushed to Todos.
"""

import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from auth import require_boss
from ratelimit import is_rate_limited
from services import meeting_agent
from services.permissions import require_permission

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


class TranscriptRequest(BaseModel):
    transcript: str
    title: str = ""


class ActionRequest(BaseModel):
    meeting_id: str


def _unavailable(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


@router.post("/process", dependencies=[Depends(require_boss), Depends(require_permission("meetings.create"))])
async def meetings_process_endpoint(req: TranscriptRequest, request: Request):
    """Process a pasted meeting transcript (no audio)."""
    client_ip = request.client.host if request.client else "unknown"
    if is_rate_limited(client_ip, limit=30, window=60):
        raise HTTPException(status_code=429, detail="Too many requests, Boss.")
    transcript = (req.transcript or "").strip()
    if not transcript:
        raise HTTPException(status_code=400, detail="Empty transcript.")
    if len(transcript) > 50000:
        raise HTTPException(status_code=413, detail="Transcript too long (max 50k chars).")

    try:
        meeting = await asyncio.to_thread(meeting_agent.process_meeting, transcript, "text")
    except meeting_agent.MeetingUnavailableError as exc:
        raise _unavailable(exc) from exc
    if req.title:
        meeting["title"] = req.title.strip()[:150]
    return {"status": "ok", "meeting": meeting}


@router.post("/transcribe", dependencies=[Depends(require_boss), Depends(require_permission("meetings.create"))])
async def meetings_transcribe_endpoint(request: Request, audio: UploadFile = File(...)):
    """Transcribe + process an uploaded meeting recording (Groq Whisper)."""
    client_ip = request.client.host if request.client else "unknown"
    if is_rate_limited(client_ip, limit=30, window=60):
        raise HTTPException(status_code=429, detail="Too many requests, Boss.")

    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio file.")
    if len(data) > meeting_agent.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Audio too large (max 25 MB).")

    filename = audio.filename or "meeting.ogg"
    mime_type = audio.content_type or "audio/ogg"

    try:
        meeting = await asyncio.to_thread(
            meeting_agent.process_meeting_audio, data, filename, mime_type
        )
    except meeting_agent.MeetingUnavailableError as exc:
        raise _unavailable(exc) from exc
    return {"status": "ok", "meeting": meeting}


@router.get("", dependencies=[Depends(require_boss), Depends(require_permission("meetings.read"))])
def meetings_list_endpoint(limit: int = 20):
    return {"meetings": meeting_agent.list_meetings(limit=limit)}


@router.get("/search", dependencies=[Depends(require_boss), Depends(require_permission("meetings.read"))])
def meetings_search_endpoint(q: str):
    return {"meetings": meeting_agent.search_meetings(q)}


@router.get("/action-items", dependencies=[Depends(require_boss), Depends(require_permission("meetings.read"))])
def meetings_action_items_endpoint():
    return {"action_items": meeting_agent.get_action_items()}


@router.get("/{meeting_id}", dependencies=[Depends(require_boss), Depends(require_permission("meetings.read"))])
def meetings_get_endpoint(meeting_id: str):
    meeting = meeting_agent.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return {"meeting": meeting}


@router.post("/{meeting_id}/todos", dependencies=[Depends(require_boss), Depends(require_permission("meetings.read"))])
def meetings_push_todos_endpoint(meeting_id: str):
    """Push a meeting's action items into the todo list."""
    try:
        result = meeting_agent.push_action_items_to_todos(meeting_id)
    except meeting_agent.MeetingUnavailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok", **result}
