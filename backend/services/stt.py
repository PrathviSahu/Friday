"""services/stt.py — server-side speech-to-text engine for FRIDAY.

Engine selection (best free tier first):

1. Groq Whisper `whisper-large-v3-turbo` — free tier: 20 RPM, 2,000
   requests/day, ~7,200 audio-seconds/hour, 28,800 audio-seconds/day,
   25 MB per upload. Extremely fast on LPUs (a short voice clip returns in
   ~1s) and multilingual — it transcribes English, Hindi and Hinglish
   natively, which the browser Web Speech API (en-US only) cannot.

2. Google Gemini Flash (audio understanding) — resilient multi-model fallback
   (gemini-3.5-flash-lite, gemini-3.5-flash, gemini-3.6-flash, gemini-2.5-flash)
   when Groq is rate-limited (429), unconfigured, or failing.

Both providers are already configured in FRIDAY (`GROQ_API_KEY` /
`GEMINI_API_KEY`), so this costs nothing extra on the free tiers.
"""

import os

GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")
GEMINI_STT_MODELS = [
    os.getenv("GEMINI_STT_MODEL", "gemini-3.5-flash-lite"),
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-2.5-flash",
]

_groq_client = None
_gemini_client = None


class STTUnavailableError(RuntimeError):
    """Raised when no STT provider can transcribe the audio."""


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if api_key and api_key != "your_key_here":
            from groq import Groq
            _groq_client = Groq(api_key=api_key)
    return _groq_client


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and api_key != "your_key_here":
            from google import genai
            _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


import re

WHISPER_SILENCE_HALLUCINATIONS = {
    "thank you.", "thank you", "thanks.", "thanks",
    "thanks for watching.", "thanks for watching!",
    "thanks for watching", "thank you for watching.",
    "thank you for watching", "subtitles by", "subtitles",
    "subtitles by the amara.org community", "you",
    "bye.", "bye", "bye bye", "goodbye.", "goodbye",
    "please subscribe", "subscribe", ".", "..", "...",
    "so", "yeah", "okay.", "okay"
}


def _clean_hallucinated_transcript(raw_text: str) -> str:
    cleaned = (raw_text or "").strip()
    if not cleaned:
        return ""
    cleaned = cleaned.strip('"\'')
    if cleaned.lower() in WHISPER_SILENCE_HALLUCINATIONS:
        return ""
    if re.match(r'^[\.\,\!\?\:\;\-\s]+$', cleaned):
        return ""
    return cleaned


def _transcribe_groq(audio_bytes: bytes, filename: str, mime_type: str) -> dict:
    """Transcribe via Groq Whisper (free tier). Raises on failure."""
    client = _get_groq_client()
    if client is None:
        raise STTUnavailableError("GROQ_API_KEY is not configured")

    def _call():
        return client.audio.transcriptions.create(
            model=GROQ_STT_MODEL,
            file=(filename, audio_bytes),
            prompt="F.R.I.D.A.Y., Prem, Spotify, play, pause, next, previous, song, gaana, chalao, band, volume, awaaz, badhao, kam, karo, trading, career, Hindi, English, playlist, song, please",
            language="en",
        )

    try:
        transcription = _call()
    except Exception as exc:
        try:
            transcription = client.audio.transcriptions.create(
                model=GROQ_STT_MODEL,
                file=(filename, audio_bytes),
                prompt="F.R.I.D.A.Y., Prem, Spotify, play, pause, next, previous, song, gaana chalao, volume, awaaz badhao",
            )
        except Exception:
            if getattr(exc, "status_code", None) == 429:
                import time
                time.sleep(2)
                transcription = _call()
            else:
                raise

    raw_text = getattr(transcription, "text", "") or ""
    clean_text = _clean_hallucinated_transcript(raw_text)

    return {
        "transcript": clean_text,
        "language": getattr(transcription, "language", None) or "en",
        "source": "groq",
    }


def _transcribe_gemini(audio_bytes: bytes, filename: str, mime_type: str) -> dict:
    """Transcribe via Gemini audio understanding with multi-model fallback."""
    client = _get_gemini_client()
    if client is None:
        raise STTUnavailableError("GEMINI_API_KEY is not configured")

    from google.genai import types

    last_err = None
    for model_name in GEMINI_STT_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    "Transcribe the speech in this audio exactly as spoken in standard English/Latin alphabet. "
                    "Do NOT use Devanagari or Hindi script. If Hindi/Hinglish words are spoken (like 'gaana chalao' or 'awaaz kam'), "
                    "transcribe them phonetically in English/Latin letters (e.g., 'gaana chalao', 'play punjabi song'). "
                    "Reply with the transcript only — no quotes, no commentary.",
                    types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                ],
            )
            text = ""
            try:
                for part in response.candidates[0].content.parts or []:
                    text += part.text or ""
            except (AttributeError, IndexError):
                text = ""

            if text.strip():
                return {
                    "transcript": text.strip(),
                    "language": "en",
                    "source": f"gemini:{model_name}",
                }
        except Exception as exc:
            last_err = exc
            continue

    raise STTUnavailableError(f"Gemini STT failed across models: {last_err}") from last_err


from services.metrics import timed as _timed


@_timed("stt")
def transcribe_audio(audio_bytes: bytes, filename: str = "clip.ogg",
                     mime_type: str = "audio/ogg") -> dict:
    """Transcribe audio with the best available free-tier engine.

    Returns ``{"transcript": str, "language": str, "source": "groq"|"gemini"}``.
    Raises :class:`STTUnavailableError` when no provider can transcribe.
    """
    if not audio_bytes:
        raise STTUnavailableError("No audio received")

    errors = []
    try:
        result = _transcribe_groq(audio_bytes, filename, mime_type)
        if result["transcript"]:
            return result
        errors.append("Groq returned an empty transcript")
    except Exception as exc:
        errors.append(f"Groq failed: {exc}")

    try:
        result = _transcribe_gemini(audio_bytes, filename, mime_type)
        if result["transcript"]:
            return result
        errors.append("Gemini returned an empty transcript")
    except Exception as exc:
        errors.append(f"Gemini failed: {exc}")

    raise STTUnavailableError("; ".join(errors))
