"""services/brain — FRIDAY's Adaptive Learning & Dual-Engine Modular AI Brain.

Decomposed into structured plugins and handlers:
- `constants.py`: Actions, system prompts, role boundaries
- `clients.py`: Singleton API clients (Groq Llama 3.3 70B & Gemini 2.5 Flash)
- `prompt_builder.py`: Context assembly (memories, live track, time, todos, brevity, embeddings RAG)
- `handlers/`: Deterministic fast-path handlers (<15ms)
    * `security_handler.py`: Permissions & guest delegation
    * `navigation_handler.py`: Trading, Career OS, Dashboard
    * `agents_handler.py`: Meetings, WhatsApp, Documents, Calendar, Email
    * `hardware_handler.py`: Display Brightness, Dark mode, Screen Lock, Screenshot
    * `utilities_handler.py`: Weather, Reminders, Tasks, History, Time
    * `media_handler.py`: Spotify playback, volume, playlists, track controls, song aliases
- `engine.py`: Core cognitive decision orchestrator
"""

from services.brain.constants import (
    KNOWN_ACTIONS,
    _BOSS_BASE_PROMPT,
    _GUEST_SYSTEM_PROMPT,
)
from services.brain.clients import (
    _get_groq_client,
    _get_gemini_client,
    _extract_json,
)
from services.brain.prompt_builder import (
    build_system_prompt,
    get_proactive_suggestion,
)
from services.brain.handlers.media_handler import (
    clean_song_query as _clean_song_query,
    clean_song_query,
)
from services.brain.engine import (
    respond,
    _handle_system_automation,
)

__all__ = [
    "respond",
    "get_proactive_suggestion",
    "_get_groq_client",
    "_get_gemini_client",
    "_extract_json",
    "_clean_song_query",
    "clean_song_query",
    "KNOWN_ACTIONS",
    "_BOSS_BASE_PROMPT",
    "_GUEST_SYSTEM_PROMPT",
    "_handle_system_automation",
    "build_system_prompt",
]
