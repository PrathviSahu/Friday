from pathlib import Path
import asyncio
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.services.tts import generate_speech, cleanup_temp_audio
from backend.services.formatter import format_response
from backend.services.market import get_klines, get_quotes, search_symbols

BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / 'temp_audio'
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title='F.R.I.D.A.Y. TTS Service',
    version='1.0.0',
    description='Backend TTS endpoint for F.R.I.D.A.Y. using Microsoft Edge Neural voice.',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

app.mount('/temp_audio', StaticFiles(directory=AUDIO_DIR), name='temp_audio')

class SpeakRequest(BaseModel):
    text: str


@app.on_event('startup')
async def startup_cleanup_task():
    asyncio.create_task(cleanup_temp_audio(AUDIO_DIR))


@app.post('/api/speak')
async def speak(request: Request, body: SpeakRequest):
    text = body.text.strip() if body.text else ''
    if not text:
        raise HTTPException(status_code=400, detail='Text is required for speech generation.')

    print('REQUEST:', text)

    try:
        # Apply response formatter to enforce FRIDAY personality rules
        formatted = format_response(text)
        file_path = await generate_speech(formatted, AUDIO_DIR)
        return {
            'url': f'http://127.0.0.1:8000/temp_audio/{file_path.name}',
            'file': file_path.name,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Unable to generate TTS audio: {exc}')


# ── Market data (Yahoo Finance proxy) ──────────────────────────────────────────
@app.get('/api/market/klines')
async def api_klines(symbol: str, interval: str = '5m'):
    try:
        return await get_klines(symbol, interval)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f'Market data unavailable: {exc}')


@app.get('/api/market/quote')
async def api_quote(symbols: str = ''):
    syms = [s.strip() for s in symbols.split(',') if s.strip()]
    try:
        return await get_quotes(syms)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f'Market data unavailable: {exc}')


@app.get('/api/market/search')
async def api_search(q: str = ''):
    try:
        return await search_symbols(q)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f'Market search unavailable: {exc}')
