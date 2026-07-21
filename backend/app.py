from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os
from pathlib import Path

from services.brain import respond, chat_with_audio
from services.tts import generate_speech

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


class TTSRequest(BaseModel):
    text: str


@app.get("/")
def read_root():
    return {"status": "online", "system": "F.R.I.D.A.Y. AI Core v2.0"}


@app.post("/api/chat/text")
def chat_text_endpoint(req: ChatTextRequest):
    """Text-based chat endpoint for FRIDAY AI brain"""
    try:
        res = respond(req.text)
        return res
    except Exception as e:
        print(f"[Error] Chat endpoint error: {e}")
        # Fallback response if API key is missing or model fails
        return {
            "reply": "I'm experiencing a temporary neural link issue, Boss. Please check the backend API configuration.",
            "action": "none"
        }


@app.post("/api/tts")
async def tts_endpoint(req: TTSRequest):
    """Generate British female voice audio using Edge-TTS"""
    try:
        file_path = await generate_speech(req.text, AUDIO_DIR)
        return {"audio_url": f"http://localhost:8000/temp_audio/{file_path.name}"}
    except Exception as e:
        print(f"[Error] TTS generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)