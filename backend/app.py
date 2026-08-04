"""F.R.I.D.A.Y. AI Core — application wiring (v3).

app.py is intentionally thin: it assembles the FastAPI app, wires the route
modules (backend/routes/*), and owns the lifespan (env validation, background
task startup/shutdown). All route logic lives in the route modules.
"""

from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from backend/.env first — services read these at import.
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from routes.chat import router as chat_router
from routes.email import router as email_router
from routes.calendar import router as calendar_router
from routes.meetings import router as meetings_router
from routes.whatsapp import router as whatsapp_router
from routes.documents import router as documents_router
from routes.company import router as company_router
from routes.coding import router as coding_router
from routes.system import router as system_router
from routes.spotify import router as spotify_router
from routes.todos import router as todos_router
from routes.utilities import router as utilities_router
from routes.watchlist import router as watchlist_router, seed_watchlist
from routes.trading import router as trading_router
from routes.automation import router as automation_router
from routes.agents import router as agents_router
from routes.learning import router as learning_router
from routes.life_memory import router as life_memory_router
from routes.devtools import router as devtools_router
from routes.knowledge import router as knowledge_router
from routers.career import router as career_router

from services.market_data import start_market_pollers, stop_market_pollers
from services.indian_market_data import start_indian_poller, stop_indian_poller
from services.gdrive_sync import (
    start_background_gdrive_sync,
    stop_background_gdrive_sync,
)
from services.automation import start_automation_runner, stop_automation_runner
from services.tts import cleanup_temp_audio
from services.voice_auth import is_guest_permitted

# ── Required environment variable validation ───────────────────────────────────
REQUIRED_ENV_VARS = [
    ("GROQ_API_KEY",          "LLM voice responses will fail — brain is offline"),
    ("GEMINI_API_KEY",        "Gemini fallback will be unavailable"),
    ("SPOTIFY_CLIENT_ID",     "Spotify control will be unavailable"),
    ("SPOTIFY_CLIENT_SECRET", "Spotify control will be unavailable"),
    ("FRIDAY_API_TOKEN",      "non-localhost API access will be rejected (401)"),
]

OPTIONAL_ENV_VARS = [
    ("TELEGRAM_BOT_TOKEN", "Telegram bot interface will be unavailable"),
    ("TELEGRAM_OWNER_ID",  "Telegram bot rejects everyone (access denied)"),
    ("FRIDAY_VAULT_KEY",   "Career vault falls back to auto-generated .vault_key"),
]


def _validate_env() -> None:
    """Warn loudly about missing / stubbed keys at startup (no silent failures)."""
    missing_required = []
    for var, consequence in REQUIRED_ENV_VARS:
        val = os.getenv(var, "").strip()
        if not val or val in ("your_key_here", "your_spotify_client_id",
                              "your_spotify_client_secret",
                              "generated_by_spotify_auth_setup_py"):
            missing_required.append((var, consequence))
    if missing_required:
        print("\n🚨 FRIDAY STARTUP — Missing Required API Keys:")
        for var, consequence in missing_required:
            print(f"  ❌ {var}: {consequence}")
        print("   → Copy backend/.env.example → backend/.env and fill in your API keys.\n")

    missing_optional = []
    for var, consequence in OPTIONAL_ENV_VARS:
        if not os.getenv(var, "").strip():
            missing_optional.append((var, consequence))
    if missing_optional:
        print("⚠️  FRIDAY STARTUP — Optional keys not set:")
        for var, consequence in missing_optional:
            print(f"   • {var}: {consequence}")
        print()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: validate env, seed data, launch background tasks.

    Shutdown: stop background threads / tasks so tests and reloads are clean.
    """
    _validate_env()

    # Seed default watchlist (only if the table is empty)
    seed_watchlist()

    # Background market-data pollers (previously spawned at module import —
    # that made testing impossible and created zombie threads).
    start_market_pollers()
    start_indian_poller()

    # Google Drive background sync (DB snapshot backup)
    start_background_gdrive_sync(interval_seconds=300)

    # Automation Engine — scheduled workflows (briefing, job scans, ...)
    start_automation_runner()

    # Temp audio cleanup: delete stale generated MP3s every 2 minutes
    audio_dir = Path(__file__).parent / "temp_audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    cleanup_task = asyncio.create_task(cleanup_temp_audio(audio_dir))

    yield

    # ── Shutdown ──
    stop_market_pollers()
    stop_indian_poller()
    stop_background_gdrive_sync()
    stop_automation_runner()
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="FRIDAY AI Core", version="3.3.0", lifespan=lifespan)

# Enable CORS — frontend origins only (no self-referential backend origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

# Generated TTS audio (ensure the dir exists before mounting)
Path(__file__).parent.joinpath("temp_audio").mkdir(parents=True, exist_ok=True)
app.mount('/temp_audio', StaticFiles(directory=Path(__file__).parent / "temp_audio"), name='temp_audio')

# Route modules (v3 modular split)
app.include_router(chat_router)
app.include_router(email_router)
app.include_router(calendar_router)
app.include_router(meetings_router)
app.include_router(whatsapp_router)
app.include_router(documents_router)
app.include_router(company_router)
app.include_router(coding_router)
app.include_router(system_router)
app.include_router(spotify_router)
app.include_router(todos_router)
app.include_router(utilities_router)
app.include_router(watchlist_router)
app.include_router(trading_router)
app.include_router(automation_router)
app.include_router(agents_router)
app.include_router(learning_router)
app.include_router(life_memory_router)
app.include_router(devtools_router)
app.include_router(knowledge_router)
app.include_router(career_router)


@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "F.R.I.D.A.Y. AI Core v3.3.0",
        "guest_permitted": is_guest_permitted(),
    }


if __name__ == "__main__":
    # proxy_headers=False: never trust X-Forwarded-For / X-Real-IP from
    # clients. Otherwise any remote caller could spoof `X-Forwarded-For:
    # 127.0.0.1` and bypass owner authentication (uvicorn rewrites
    # request.client from those headers by default). FRIDAY is a direct local
    # service — the Vite dev proxy connects from 127.0.0.1 anyway.
    uvicorn.run(app, host="0.0.0.0", port=8000, proxy_headers=False)
