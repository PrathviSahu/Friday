import asyncio
import time
from pathlib import Path
import uuid

import edge_tts

import re

import json

SETTINGS_FILE = Path(__file__).parent.parent / 'data' / 'settings.json'

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


def _clean_old_mp3s(output_dir: Path, keep_last: int = 5):
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


from services.metrics import timed as _timed


@_timed("tts")
async def generate_speech(text: str, output_dir: Path, voice: str = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    _clean_old_mp3s(output_dir, keep_last=5)

    filename = f'{uuid.uuid4().hex}.mp3'
    target_file = output_dir / filename

    # Auto-detect voice if not explicitly provided: use Hindi neural voice if Devanagari characters present
    if not voice:
        if re.search(r'[\u0900-\u097F]', text):
            selected_voice = VOICE_HINDI
        else:
            selected_voice = VOICE_ENGLISH
    else:
        selected_voice = voice

    communicate = edge_tts.Communicate(text, selected_voice)
    # open file synchronously and write chunks as they arrive from the async stream
    with target_file.open('wb') as audio_file:
        async for chunk in communicate.stream():
            if chunk['type'] == 'audio':
                audio_file.write(chunk['data'])

    return target_file


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
