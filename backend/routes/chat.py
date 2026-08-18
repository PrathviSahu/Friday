"""routes/chat.py — AI brain, memory, permissions, proactive suggestions."""

import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from auth import require_boss, require_public_demo, is_boss_request
from ratelimit import is_rate_limited
from services.brain import respond, get_proactive_suggestion
from services.stt import transcribe_audio, STTUnavailableError
from services.voice_auth import is_guest_permitted, set_guest_permission
from services.memory import get_all_memories, save_fact

router = APIRouter(prefix="/api", tags=["chat"])

# Groq free tier caps uploads at 25 MB; 10 MB is plenty for a voice clip.
MAX_STT_AUDIO_BYTES = 10 * 1024 * 1024


class ChatTextRequest(BaseModel):
    text: str
    silence_tts: bool = False


class PermissionRequest(BaseModel):
    allow: bool


class SaveMemoryRequest(BaseModel):
    key: str
    value: str


class SpeechCorrectionRequest(BaseModel):
    original_text: str
    corrected_text: str


@router.post("/chat/text", dependencies=[Depends(require_public_demo)])
async def chat_text_endpoint(req: ChatTextRequest, request: Request):
    """Text-based chat endpoint for FRIDAY AI brain with memory learning.
    Rate limited: 30 requests / 60s per IP to protect Groq/Gemini API credits.
    Uses asyncio.to_thread() to prevent blocking the event loop during
    synchronous Groq/Gemini LLM calls.

    Owner identity is derived server-side (loopback or FRIDAY_API_TOKEN) —
    it is never accepted from the client body.
    """
    client_ip = request.client.host if request.client else "unknown"
    if is_rate_limited(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please slow down, Prem — even I need a breather!"
        )
    is_boss = is_boss_request(request)
    try:
        return await asyncio.to_thread(respond, req.text, is_boss, req.silence_tts)
    except Exception as e:
        import traceback
        print(f"[Error] Chat endpoint error: {e}")
        traceback.print_exc()
        return {
            "reply": "I apologize Prem, I had a momentary connection hiccup. Could you repeat that?",
            "action": "none"
        }


@router.get("/memory", dependencies=[Depends(require_boss)])
def get_memories_endpoint():
    """Retrieve all stored long-term memories"""
    return {"status": "ok", "memories": get_all_memories()}


@router.post("/memory", dependencies=[Depends(require_boss)])
def save_memory_endpoint(req: SaveMemoryRequest):
    """Manually add or edit a memory fact"""
    save_fact(req.key, req.value)
    return {"status": "ok", "memories": get_all_memories()}


@router.post("/memory/consolidate", dependencies=[Depends(require_boss)])
def consolidate_memory_endpoint():
    """Phase 2.2 — manually trigger one consolidation pass (owner only)."""
    from services import memory_consolidator
    return memory_consolidator.run()


@router.get("/memory/digest", dependencies=[Depends(require_boss)])
def memory_digest_endpoint():
    """Phase 2.2 — consolidated knowledge digest + pruned count."""
    from services import memory_consolidator
    return {"status": "ok", **memory_consolidator.get_digest()}


@router.post("/speech/correct", dependencies=[Depends(require_boss)])
def record_speech_correction(req: SpeechCorrectionRequest):
    """Record a user speech correction permanently in personal vocabulary memory."""
    from speech.personal_vocabulary import PersonalVocabularyEngine
    ok = PersonalVocabularyEngine().record_correction(req.original_text, req.corrected_text)
    return {"status": "ok" if ok else "error"}


@router.post("/speech/transcribe", dependencies=[Depends(require_public_demo)])
async def speech_transcribe_endpoint(request: Request, audio: UploadFile = File(...)):
    """Transcribe a voice clip with the best free-tier STT engine.

    Engine order: Groq Whisper `whisper-large-v3-turbo` (free tier) →
    Gemini 2.5 Flash audio (free tier). The transcript then passes through
    the personal vocabulary correction engine, so saved "No, I meant X"
    corrections apply to voice input too.

    Rate limited: 30 requests / 60s per IP (Groq's free tier allows 20 RPM;
    Gemini absorbs the overflow).
    """
    client_ip = request.client.host if request.client else "unknown"
    if is_rate_limited(client_ip, limit=30, window=60):
        raise HTTPException(
            status_code=429,
            detail="Too many transcriptions. Please slow down, Prem."
        )

    data = await audio.read()
    if len(data) > MAX_STT_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio clip too large (max 10 MB).")
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio clip.")

    filename = audio.filename or "clip.ogg"
    mime_type = audio.content_type or "audio/ogg"

    try:
        result = await asyncio.to_thread(transcribe_audio, data, filename, mime_type)
    except STTUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    transcript = (result.get("transcript") or "").strip()
    # Apply permanent personal corrections (user's "No, I meant X" fixes).
    if transcript:
        try:
            from speech.personal_vocabulary import PersonalVocabularyEngine
            corrected = PersonalVocabularyEngine().apply_corrections(transcript)
            transcript = corrected or transcript
        except Exception:
            pass  # vocabulary engine must never break transcription

    return {
        "transcript": transcript,
        "language": result.get("language", "auto"),
        "source": result.get("source", ""),
    }


@router.post("/permission", dependencies=[Depends(require_boss)])
def set_permission_endpoint(req: PermissionRequest):
    """Grant or revoke guest voice permission"""
    set_guest_permission(req.allow)
    return {"status": "ok", "guest_permitted": is_guest_permitted()}


@router.get("/proactive", dependencies=[Depends(require_boss)])
def proactive_endpoint():
    """Return a time-aware proactive suggestion FRIDAY can speak spontaneously."""
    return get_proactive_suggestion()
