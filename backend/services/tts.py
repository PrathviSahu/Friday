import asyncio
from pathlib import Path
import uuid

import edge_tts

VOICE_NAME = 'en-GB-SoniaNeural'


async def generate_speech(text: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f'{uuid.uuid4().hex}.mp3'
    target_file = output_dir / filename

    communicate = edge_tts.Communicate(text, VOICE_NAME)
    # open file synchronously and write chunks as they arrive from the async stream
    with target_file.open('wb') as audio_file:
        async for chunk in communicate.stream():
            if chunk['type'] == 'audio':
                audio_file.write(chunk['data'])

    return target_file


async def cleanup_temp_audio(audio_dir: Path, max_age_seconds: int = 3600):
    while True:
        now = asyncio.get_event_loop().time()
        for file_path in audio_dir.glob('*.mp3'):
            try:
                age = now - file_path.stat().st_mtime
                if age > max_age_seconds:
                    file_path.unlink()
            except Exception:
                pass
        await asyncio.sleep(600)
