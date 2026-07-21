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

from services.brain import respond
from services.tts import generate_speech
from services.voice_auth import is_guest_permitted, set_guest_permission
from services.memory import get_all_memories, save_fact

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


class TTSRequest(BaseModel):
    text: str


class PermissionRequest(BaseModel):
    allow: bool


class SaveMemoryRequest(BaseModel):
    key: str
    value: str


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
        res = respond(req.text, is_boss=req.is_boss)
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