"""services/brain/handlers/__init__.py — Unified fast-path handler chain."""

from typing import Optional
from services.brain.handlers.security_handler import handle_security_and_permissions
from services.brain.handlers.navigation_handler import handle_navigation
from services.brain.handlers.agents_handler import handle_agents
from services.brain.handlers.hardware_handler import handle_hardware
from services.brain.handlers.utilities_handler import handle_utilities
from services.brain.handlers.media_handler import handle_media, clean_song_query


def dispatch_fast_path_handlers(
    lower_text: str,
    is_boss: bool,
    extracted_vol: int,
    silence_tts: bool,
    raw_text: str,
    last_action_context: dict
) -> Optional[dict]:
    """Runs through registered fast-path handlers in strict priority order (<15ms response)."""
    # 1. Navigation shortcuts
    nav_res = handle_navigation(lower_text, is_boss)
    if nav_res:
        return nav_res

    # 2. Specialized Agents bridge (Meetings, WhatsApp, Docs, Calendar, Email)
    agent_res = handle_agents(lower_text, is_boss)
    if agent_res:
        return agent_res

    # 3. macOS Hardware & Display controls
    hw_res = handle_hardware(lower_text, is_boss)
    if hw_res:
        return hw_res

    # 4. Utilities & Productivity (Weather, Reminders, Tasks, History, Time, Quant Chart)
    util_res = handle_utilities(lower_text, is_boss, raw_text)
    if util_res:
        return util_res

    # 5. Media & Spotify controls
    media_res = handle_media(lower_text, is_boss, extracted_vol, silence_tts, last_action_context)
    if media_res:
        return media_res

    return None
