"""routes/utilities.py — TTS, weather, web search, reminders, gdrive."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from auth import require_boss, require_public_demo
from services.tts import generate_speech, stream_raw_speech
from services.weather import get_weather
from services.web_search import search_web_instant
from services.reminders import add_reminder, get_active_reminders
from services.gdrive_sync import perform_gdrive_sync, get_gdrive_sync_status

router = APIRouter(prefix="/api", tags=["utilities"])

AUDIO_DIR = Path(__file__).resolve().parent.parent / "temp_audio"


class TTSRequest(BaseModel):
    text: str


class SearchRequest(BaseModel):
    query: str


class ReminderRequest(BaseModel):
    message: str
    seconds: int


@router.get("/tts/stream", dependencies=[Depends(require_public_demo)])
async def tts_stream_get_endpoint(text: str, voice: str = None):
    """Stream low-latency raw MP3 audio chunks via HTTP chunked transfer (<180ms TTFA)."""
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    return StreamingResponse(
        stream_raw_speech(text, voice=voice),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-cache",
            "Transfer-Encoding": "chunked",
            "Accept-Ranges": "bytes"
        }
    )


@router.post("/tts/stream", dependencies=[Depends(require_public_demo)])
async def tts_stream_post_endpoint(req: TTSRequest, voice: str = None):
    """Stream low-latency raw MP3 audio chunks via HTTP chunked transfer (<180ms TTFA)."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    return StreamingResponse(
        stream_raw_speech(req.text, voice=voice),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-cache",
            "Transfer-Encoding": "chunked",
            "Accept-Ranges": "bytes"
        }
    )


@router.post("/tts", dependencies=[Depends(require_public_demo)])
async def tts_endpoint(req: TTSRequest):
    """Generate British female voice audio using Edge-TTS"""
    try:
        file_path = await generate_speech(req.text, AUDIO_DIR)
        # Verify generated audio file exists on disk before returning URL
        if not file_path.exists() or file_path.stat().st_size == 0:
            raise HTTPException(status_code=500, detail="Generated audio file is missing or empty")
        # Relative URL so the frontend works regardless of the host/port the UI
        # is served from (dev proxy, LAN host, Tauri build). The client resolves
        # it against its configured API base.
        return {"audio_url": f"/temp_audio/{file_path.name}"}
    except Exception as e:
        print(f"[Error] TTS generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weather", dependencies=[Depends(require_public_demo)])
def weather_endpoint():
    """Return live weather data."""
    return get_weather()


@router.post("/search", dependencies=[Depends(require_boss)])
def web_search_endpoint(req: SearchRequest):
    """Search DuckDuckGo instant answer snippets."""
    return search_web_instant(req.query)


@router.get("/reminders", dependencies=[Depends(require_boss)])
def get_reminders_endpoint():
    """Get active timers and reminders."""
    return {"reminders": get_active_reminders()}


@router.post("/reminders", dependencies=[Depends(require_boss)])
def add_reminder_endpoint(req: ReminderRequest):
    """Set a timer/reminder."""
    item = add_reminder(req.message, req.seconds)
    return {"status": "ok", "reminder": item}


@router.get("/gdrive/status", dependencies=[Depends(require_boss)])
def get_gdrive_status_endpoint():
    """Get Google Drive background sync status."""
    return get_gdrive_sync_status()


@router.post("/gdrive/sync-now", dependencies=[Depends(require_boss)])
def trigger_gdrive_sync_endpoint():
    """Trigger an instant background backup to Google Drive."""
    res = perform_gdrive_sync()
    return {"status": "ok", "gdrive": res}
