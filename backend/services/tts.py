"""services/tts.py — Text-to-Speech synthesis with Edge-TTS, TTFA streaming, and sentence chunking."""

import asyncio
import time
from pathlib import Path
import uuid
import edge_tts
import re
import json
from collections import OrderedDict
import threading
from typing import Tuple, List, AsyncGenerator, Optional
from services.metrics import timed as _timed

SETTINGS_FILE = Path(__file__).parent.parent / 'data' / 'settings.json'

_CACHE_LOCK = threading.Lock()
_AUDIO_LRU_CACHE = OrderedDict()  # key: (text_clean, voice) -> bytes
_MAX_CACHE_SIZE = 128


def get_configured_voices():
    """Reads configured voices from settings.json with safe fallbacks."""
    default_en = 'en-IN-NeerjaNeural'
    default_hi = 'hi-IN-SwaraNeural'
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                v = data.get('voice', {})
                return v.get('english', default_en), v.get('hindi', default_hi)
    except Exception:
        pass
    return default_en, default_hi


VOICE_ENGLISH, VOICE_HINDI = get_configured_voices()

_active_tts_cancellations = set()


def cancel_current_synthesis(session_id: str):
    """Mark a synthesis session cancelled on user barge-in."""
    if session_id:
        _active_tts_cancellations.add(session_id)


def is_synthesis_cancelled(session_id: str) -> bool:
    return bool(session_id and session_id in _active_tts_cancellations)


def clear_synthesis_cancellation(session_id: str):
    _active_tts_cancellations.discard(session_id)


def split_speech_text(text: str) -> List[str]:
    """Split response into natural speech sentences for early chunk synthesis.

    Example: "Display locked, Prem. Everything is secure." -> ["Display locked, Prem.", "Everything is secure."]
    """
    clean = (text or "").strip()
    if not clean:
        return []

    # Split by sentence terminators (. ! ?)
    sentences = re.split(r'(?<=[.!?])\s+', clean)
    filtered = [s.strip() for s in sentences if s and s.strip()]
    return filtered if filtered else [clean]




def _clean_old_mp3s(output_dir: Path, keep_last: int = 10):
    """Deletes old temporary MP3 files to prevent disk accumulation."""
    try:
        files = sorted(output_dir.glob('*.mp3'), key=lambda p: p.stat().st_mtime)
        if len(files) > keep_last:
            for old_file in files[:-keep_last]:
                try:
                    old_file.unlink()
                except Exception:
                    pass
    except Exception:
        pass


@_timed("tts")
async def generate_speech_with_ttfa(
    text: str,
    output_dir: Path,
    voice: str = None,
    session_id: Optional[str] = None
) -> Tuple[Path, float, float]:
    """Generate audio via Edge-TTS while measuring TTFA (Time To First Audio) and Total latency."""
    output_dir.mkdir(parents=True, exist_ok=True)
    _clean_old_mp3s(output_dir, keep_last=10)

    filename = f'{uuid.uuid4().hex}.mp3'
    target_file = output_dir / filename

    if not voice:
        selected_voice = VOICE_HINDI if re.search(r'[\u0900-\u097F]', text) else VOICE_ENGLISH
    else:
        selected_voice = voice

    communicate = edge_tts.Communicate(text, selected_voice)

    t0 = time.perf_counter()
    ttfa_ms = 0.0
    first_chunk_received = False

    with target_file.open('wb') as audio_file:
        async for chunk in communicate.stream():
            if is_synthesis_cancelled(session_id):
                clear_synthesis_cancellation(session_id)
                raise asyncio.CancelledError("TTS synthesis cancelled on barge-in")

            if chunk.get('type') == 'audio':
                if not first_chunk_received:
                    ttfa_ms = (time.perf_counter() - t0) * 1000.0
                    first_chunk_received = True
                audio_file.write(chunk['data'])

    total_ms = (time.perf_counter() - t0) * 1000.0
    if not first_chunk_received:
        ttfa_ms = total_ms

    clear_synthesis_cancellation(session_id)
    return target_file, round(ttfa_ms, 2), round(total_ms, 2)


async def generate_speech(text: str, output_dir: Path, voice: str = None) -> Path:
    """Standard generate_speech returning Path for backward compatibility."""
    target_file, _, _ = await generate_speech_with_ttfa(text, output_dir, voice)
    return target_file


async def stream_speech_chunks(
    text: str,
    output_dir: Path,
    voice: str = None,
    session_id: Optional[str] = None
) -> AsyncGenerator[dict, None]:
    """Stream audio chunks per sentence for immediate playback (overlapping generation)."""
    sentences = split_speech_text(text)
    total_sentences = len(sentences)

    for idx, sentence in enumerate(sentences):
        if is_synthesis_cancelled(session_id):
            clear_synthesis_cancellation(session_id)
            break

        path, chunk_ttfa, chunk_total = await generate_speech_with_ttfa(
            sentence, output_dir, voice, session_id=session_id
        )

        yield {
            "chunk_index": idx,
            "total_chunks": total_sentences,
            "is_final": (idx == total_sentences - 1),
            "text": sentence,
            "audio_file": path,
            "audio_url": f"/temp_audio/{path.name}",
            "ttfa_ms": chunk_ttfa,
            "chunk_duration_ms": chunk_total,
        }


async def stream_raw_speech(
    text: str,
    voice: str = None,
    session_id: Optional[str] = None
) -> AsyncGenerator[bytes, None]:
    """Yield raw MP3 audio chunks in real-time as they stream from Edge-TTS (or memory cache)."""
    clean = (text or "").strip()
    if not clean:
        return

    if not voice:
        selected_voice = VOICE_HINDI if re.search(r'[\u0900-\u097F]', clean) else VOICE_ENGLISH
    else:
        selected_voice = voice

    cache_key = (clean, selected_voice)
    with _CACHE_LOCK:
        if cache_key in _AUDIO_LRU_CACHE:
            cached_data = _AUDIO_LRU_CACHE[cache_key]
            _AUDIO_LRU_CACHE.move_to_end(cache_key)
            for i in range(0, len(cached_data), 8192):
                yield cached_data[i:i+8192]
            return

    communicate = edge_tts.Communicate(clean, selected_voice)
    collected_bytes = bytearray()

    try:
        async for chunk in communicate.stream():
            if is_synthesis_cancelled(session_id):
                clear_synthesis_cancellation(session_id)
                break

            if chunk.get('type') == 'audio':
                data = chunk['data']
                collected_bytes.extend(data)
                yield data
    except Exception as err:
        print(f"[TTS Stream] Error: {err}")

    # Cache short responses (< 250 chars) for instant sub-millisecond repeat access
    if len(clean) <= 250 and collected_bytes:
        with _CACHE_LOCK:
            _AUDIO_LRU_CACHE[cache_key] = bytes(collected_bytes)
            if len(_AUDIO_LRU_CACHE) > _MAX_CACHE_SIZE:
                _AUDIO_LRU_CACHE.popitem(last=False)


async def cleanup_temp_audio(audio_dir: Path, max_age_seconds: int = 300):
    while True:
        try:
            now = time.time()
            for file_path in audio_dir.glob('*.mp3'):
                try:
                    if now - file_path.stat().st_mtime > max_age_seconds:
                        file_path.unlink()
                except Exception:
                    pass
        except Exception:
            pass
        await asyncio.sleep(120)
