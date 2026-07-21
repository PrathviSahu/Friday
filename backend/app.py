from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from backend/.env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os

from services.brain import respond, get_proactive_suggestion
from services.tts import generate_speech
from services.voice_auth import is_guest_permitted, set_guest_permission
from services.memory import get_all_memories, save_fact
from services.system_control import get_spotify_current_track
from services.todos import get_todos, add_todo, toggle_todo, delete_todo, clear_done, update_todo_text
from services.system_stats import get_system_stats
from services.weather import get_weather
from services.web_search import search_web_instant
from services.reminders import add_reminder, get_active_reminders

# Ensure temp_audio directory exists
AUDIO_DIR = Path('temp_audio')
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="FRIDAY AI Core", version="2.0.0")

# Enable CORS for frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount('/temp_audio', StaticFiles(directory='temp_audio'), name='temp_audio')


class ChatTextRequest(BaseModel):
    text: str
    is_boss: bool = True
    silence_tts: bool = False


class TTSRequest(BaseModel):
    text: str


class PermissionRequest(BaseModel):
    allow: bool


class SaveMemoryRequest(BaseModel):
    key: str
    value: str


class SearchRequest(BaseModel):
    query: str


class ReminderRequest(BaseModel):
    message: str
    seconds: int


class TodoCreateRequest(BaseModel):
    text: str
    priority: str = "normal"  # "high" | "normal" | "low"


class TodoTextRequest(BaseModel):
    text: str


@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "F.R.I.D.A.Y. AI Core v2.0",
        "guest_permitted": is_guest_permitted()
    }


@app.post("/api/chat/text")
def chat_text_endpoint(req: ChatTextRequest):
    """Text-based chat endpoint for FRIDAY AI brain with memory learning"""
    try:
        res = respond(req.text, is_boss=req.is_boss, silence_tts=req.silence_tts)
        return res
    except Exception as e:
        print(f"[Error] Chat endpoint error: {e}")
        return {
            "reply": "I'm experiencing a temporary neural link issue, Boss. Please check the backend API configuration.",
            "action": "none"
        }


@app.get("/api/memory")
def get_memories_endpoint():
    """Retrieve all stored long-term memories"""
    return {"status": "ok", "memories": get_all_memories()}


@app.post("/api/memory")
def save_memory_endpoint(req: SaveMemoryRequest):
    """Manually add or edit a memory fact"""
    save_fact(req.key, req.value)
    return {"status": "ok", "memories": get_all_memories()}


@app.post("/api/permission")
def set_permission_endpoint(req: PermissionRequest):
    """Grant or revoke guest voice permission"""
    set_guest_permission(req.allow)
    return {"status": "ok", "guest_permitted": is_guest_permitted()}


@app.get("/api/spotify/current-track")
def get_spotify_track_endpoint():
    """Retrieve details of currently playing track on Spotify"""
    return get_spotify_current_track()


@app.get("/api/proactive")
def proactive_endpoint():
    """Return a time-aware proactive suggestion FRIDAY can speak spontaneously."""
    return get_proactive_suggestion()


@app.get("/api/system/stats")
def system_stats_endpoint():
    """Return live CPU, RAM, Disk, and Battery stats."""
    return get_system_stats()


@app.get("/api/weather")
def weather_endpoint():
    """Return live weather data."""
    return get_weather()


@app.post("/api/search")
def web_search_endpoint(req: SearchRequest):
    """Search DuckDuckGo instant answer snippets."""
    return search_web_instant(req.query)


@app.get("/api/reminders")
def get_reminders_endpoint():
    """Get active timers and reminders."""
    return {"reminders": get_active_reminders()}


@app.post("/api/reminders")
def add_reminder_endpoint(req: ReminderRequest):
    """Set a timer/reminder."""
    item = add_reminder(req.message, req.seconds)
    return {"status": "ok", "reminder": item}


# ── Todo endpoints ──────────────────────────────────────────

@app.get("/api/todos")
def get_todos_endpoint():
    """Get all todos"""
    return {"todos": get_todos()}


@app.post("/api/todos")
def create_todo_endpoint(req: TodoCreateRequest):
    """Add a new todo"""
    item = add_todo(req.text, req.priority)
    return {"status": "ok", "todo": item}


@app.patch("/api/todos/{todo_id}/toggle")
def toggle_todo_endpoint(todo_id: str):
    """Toggle a todo's done state"""
    item = toggle_todo(todo_id)
    if not item:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"status": "ok", "todo": item}


@app.patch("/api/todos/{todo_id}/text")
def update_todo_endpoint(todo_id: str, req: TodoTextRequest):
    """Edit todo text"""
    item = update_todo_text(todo_id, req.text)
    if not item:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"status": "ok", "todo": item}


@app.delete("/api/todos/done")
def clear_done_endpoint():
    """Remove all completed todos"""
    count = clear_done()
    return {"status": "ok", "removed": count}


@app.delete("/api/todos/{todo_id}")
def delete_todo_endpoint(todo_id: str):
    """Delete a todo by id"""
    ok = delete_todo(todo_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"status": "ok"}


@app.post("/api/tts")
async def tts_endpoint(req: TTSRequest):
    """Generate British female voice audio using Edge-TTS"""
    try:
        file_path = await generate_speech(req.text, AUDIO_DIR)
        # Verify generated audio file exists on disk before returning URL
        if not file_path.exists() or file_path.stat().st_size == 0:
            raise HTTPException(status_code=500, detail="Generated audio file is missing or empty")
        return {"audio_url": f"http://localhost:8000/temp_audio/{file_path.name}"}
    except Exception as e:
        print(f"[Error] TTS generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)