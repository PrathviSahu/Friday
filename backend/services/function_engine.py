"""function_engine.py — Function Calling AI Brain registry (v3).

Each capability is registered once with a name, description, JSON-schema
parameters, and a handler. The LLM (Groq/Gemini) receives the schemas as
tools, decides which to call, and the engine dispatches to the handler.

Adding a new capability = register one function. No more editing 30 regex
patterns in brain.py.
"""

import logging
from datetime import datetime
from typing import Callable, Dict, List, Optional

from services.system_control import (
    open_app,
    control_spotify,
    get_spotify_current_track,
    take_screenshot,
)
from services.todos import get_todos, add_todo
from services.reminders import add_reminder
from services.weather import get_weather
from services.web_search import search_web_instant
from services.voice_auth import set_guest_permission, is_guest_permitted
from services.learning_engine import save_fact
from services.mac_controls import (
    set_brightness,
    set_dark_mode,
    set_system_volume,
    set_system_mute,
    lock_display,
)

# name -> {"description", "parameters", "handler"}
_REGISTRY: Dict[str, dict] = {}


def register_function(name: str, description: str, parameters: dict,
                      handler: Callable) -> None:
    """Register a callable capability with an OpenAI-style JSON schema."""
    _REGISTRY[name] = {
        "description": description,
        "parameters": parameters,
        "handler": handler,
    }


def get_tools_schema() -> List[dict]:
    """Return the OpenAI-style tools array to pass to the LLM."""
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": spec["description"],
                "parameters": spec["parameters"],
            },
        }
        for name, spec in _REGISTRY.items()
    ]


def list_functions() -> List[str]:
    return sorted(_REGISTRY)


def dispatch(name: str, args: dict) -> str:
    """Execute a registered function and return its spoken reply text."""
    spec = _REGISTRY.get(name)
    if not spec:
        return f"Unknown function '{name}'."
    try:
        result = spec["handler"](args or {})
        return str(result) if result is not None else "Done."
    except Exception as err:
        logging.warning(f"[Function Engine] {name} failed: {err}")
        return f"I hit a problem running {name}. Please try again."


# ═══════════════════════════════════════════════════════════════════════════════
# Handlers (each returns a reply string)
# ═══════════════════════════════════════════════════════════════════════════════

def _h_get_time(args) -> str:
    return datetime.now().strftime("It is %I:%M %p on %A, %d %B %Y.")


def _h_get_weather(args) -> str:
    w = get_weather()
    try:
        return (f"Weather in {w.get('city', 'your area')}: {w.get('condition')}, "
                f"{w.get('temperature')}°C, feels like {w.get('feels_like')}°C, "
                f"humidity {w.get('humidity')}%.")
    except Exception:
        return f"Weather: {w}"


def _h_play_spotify(args) -> str:
    query = (args.get("query") or "").strip()
    if not query:
        return "Please tell me which song to play."
    control_spotify("play_specific", query)
    return f"Opening Spotify and playing '{query}', Prem."


def _h_control_spotify(args) -> str:
    action = (args.get("action") or "").strip()
    if action not in ("play", "pause", "next", "previous", "volume_up",
                      "volume_down", "shuffle", "repeat"):
        return f"Unsupported Spotify action: {action}."
    control_spotify(action)
    return f"Spotify: {action}."


def _h_get_spotify_info(args) -> str:
    info = get_spotify_current_track()
    if info.get("title"):
        return f"Now playing: {info['title']} by {info.get('artist', 'unknown')}."
    return "Nothing is playing on Spotify right now."


def _h_add_todo(args) -> str:
    text = (args.get("text") or "").strip()
    if not text:
        return "Please tell me what to add."
    add_todo(text, args.get("priority", "normal"))
    return f"Added '{text}' to your tasks."


def _h_get_todos(args) -> str:
    todos = get_todos()
    if not todos:
        return "Your task list is empty."
    pending = [t for t in todos if not t.get("done")]
    if not pending:
        return "All tasks are done. Great work, Prem!"
    lines = [f"{i + 1}. {t['text']}" for i, t in enumerate(pending[:8])]
    return "Pending tasks: " + " | ".join(lines)


def _h_set_reminder(args) -> str:
    message = (args.get("message") or "").strip()
    seconds = int(args.get("seconds") or 60)
    if not message:
        return "Please tell me what to remind you about."
    add_reminder(message, seconds)
    return f"Reminder set: '{message}' in {seconds} seconds."


def _h_open_app(args) -> str:
    app = (args.get("app") or "").strip()
    if not app:
        return "Please tell me which app to open."
    ok = open_app(app)
    return f"Opening {app}." if ok else f"I couldn't open {app}."


def _h_system_control(args) -> str:
    action = (args.get("action") or "").strip()
    value = args.get("value")
    try:
        if action == "brightness" and value is not None:
            set_brightness(float(value))
            return f"Brightness set to {value}."
        if action == "dark_mode":
            set_dark_mode(bool(value))
            return "Dark mode " + ("enabled." if value else "disabled.")
        if action == "volume" and value is not None:
            set_system_volume(int(value))
            return f"System volume set to {value}."
        if action == "mute":
            set_system_mute(bool(value))
            return "Muted." if value else "Unmuted."
        if action == "lock":
            lock_display()
            return "Locking your display, Prem."
    except Exception as err:
        return f"System control error: {err}"
    return "Unknown system control action."


def _h_search_web(args) -> str:
    query = (args.get("query") or "").strip()
    if not query:
        return "Please tell me what to search for."
    results = search_web_instant(query)
    snippets = results.get("results") or results.get("snippets") or []
    if not snippets:
        return f"No instant answers for '{query}'."
    first = snippets[0]
    return f"Here's what I found: {first.get('title', '')} — {first.get('snippet', '')}"


def _h_navigate_to(args) -> str:
    dest = (args.get("destination") or "").strip().lower()
    if dest in ("dashboard", "home"):
        return "Taking you to the dashboard."
    if dest in ("trading", "charts"):
        return "Opening the Trading Workstation."
    if dest in ("career", "jobs"):
        return "Opening the Career Intelligence Center."
    return f"Navigating to {dest}."


def _h_take_screenshot(args) -> str:
    path = take_screenshot()
    return f"Screenshot saved to {path}." if path else "Screenshot failed."


def _h_open_trading(args) -> str:
    return "Opening the Quantum Trading Workstation."


def _h_close_trading(args) -> str:
    return "Closing the Trading Workstation."


def _h_guest_permission(args) -> str:
    allow = bool(args.get("allow"))
    set_guest_permission(allow)
    return ("Guest access granted." if allow else "Guest access revoked.") + \
        f" Guests {'may' if allow else 'may not'} use FRIDAY."


def _h_remember_fact(args) -> str:
    key = (args.get("key") or "").strip()
    value = (args.get("value") or "").strip()
    if not key or not value:
        return "Please give me both a fact name and its value."
    save_fact(key, value)
    return f"Remembered: {key} = {value}."


def _h_technical_analysis(args) -> str:
    from services.technical_analysis import analyze_symbol
    symbol = (args.get("symbol") or "FX:EURUSD").strip()
    interval = str(args.get("interval") or "15")
    result = analyze_symbol(symbol, interval)
    return result.get("summary") or result.get("error", "Analysis unavailable.")


# ═══════════════════════════════════════════════════════════════════════════════
# Registrations (18 functions)
# ═══════════════════════════════════════════════════════════════════════════════

register_function(
    name="get_time",
    description="Get the current local date and time.",
    parameters={"type": "object", "properties": {}},
    handler=_h_get_time,
)

register_function(
    name="get_weather",
    description="Get the current weather for the user's location.",
    parameters={"type": "object", "properties": {}},
    handler=_h_get_weather,
)

register_function(
    name="play_spotify",
    description="Play a specific song or track on Spotify.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "Song name, artist, or search query"}},
        "required": ["query"],
    },
    handler=_h_play_spotify,
)

register_function(
    name="control_spotify",
    description="Control Spotify playback: play, pause, next, previous, volume up/down, shuffle, repeat.",
    parameters={
        "type": "object",
        "properties": {"action": {"type": "string", "enum": ["play", "pause", "next", "previous", "volume_up", "volume_down", "shuffle", "repeat"]}},
        "required": ["action"],
    },
    handler=_h_control_spotify,
)

register_function(
    name="get_spotify_info",
    description="Get the currently playing Spotify track and artist.",
    parameters={"type": "object", "properties": {}},
    handler=_h_get_spotify_info,
)

register_function(
    name="add_todo",
    description="Add a task to the user's todo list.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Task description"},
            "priority": {"type": "string", "enum": ["high", "normal", "low"], "description": "Task priority"},
        },
        "required": ["text"],
    },
    handler=_h_add_todo,
)

register_function(
    name="get_todos",
    description="List the user's pending tasks.",
    parameters={"type": "object", "properties": {}},
    handler=_h_get_todos,
)

register_function(
    name="set_reminder",
    description="Set a timer or reminder in N seconds.",
    parameters={
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Reminder text"},
            "seconds": {"type": "integer", "description": "Delay in seconds"},
        },
        "required": ["message", "seconds"],
    },
    handler=_h_set_reminder,
)

register_function(
    name="open_app",
    description="Open an application on macOS (Spotify, Chrome, VS Code, Finder, etc.).",
    parameters={
        "type": "object",
        "properties": {"app": {"type": "string", "description": "Application name"}},
        "required": ["app"],
    },
    handler=_h_open_app,
)

register_function(
    name="system_control",
    description="Control the macOS system: brightness, dark mode, volume, mute, lock display.",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["brightness", "dark_mode", "volume", "mute", "lock"]},
            "value": {"description": "Numeric level for brightness/volume, or boolean for dark_mode/mute"},
        },
        "required": ["action"],
    },
    handler=_h_system_control,
)

register_function(
    name="search_web",
    description="Search the web for instant answers to a query.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
    handler=_h_search_web,
)

register_function(
    name="navigate_to",
    description="Navigate the FRIDAY UI to a workspace: dashboard, trading, or career.",
    parameters={
        "type": "object",
        "properties": {"destination": {"type": "string", "enum": ["dashboard", "trading", "career"]}},
        "required": ["destination"],
    },
    handler=_h_navigate_to,
)

register_function(
    name="take_screenshot",
    description="Take a screenshot of the screen.",
    parameters={"type": "object", "properties": {}},
    handler=_h_take_screenshot,
)

register_function(
    name="open_trading",
    description="Open the Quantum Trading Workstation.",
    parameters={"type": "object", "properties": {}},
    handler=_h_open_trading,
)

register_function(
    name="close_trading",
    description="Close the Quantum Trading Workstation.",
    parameters={"type": "object", "properties": {}},
    handler=_h_close_trading,
)

register_function(
    name="guest_permission",
    description="Grant or revoke guest voice permission.",
    parameters={
        "type": "object",
        "properties": {"allow": {"type": "boolean"}},
        "required": ["allow"],
    },
    handler=_h_guest_permission,
)

register_function(
    name="remember_fact",
    description="Save a permanent fact or preference about the user.",
    parameters={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Fact name, e.g. favorite_color"},
            "value": {"type": "string", "description": "Fact value"},
        },
        "required": ["key", "value"],
    },
    handler=_h_remember_fact,
)

register_function(
    name="technical_analysis",
    description="Run real technical analysis on a trading symbol and return the summary.",
    parameters={
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "description": "TradingView-style symbol, e.g. FX:EURUSD, OANDA:XAUUSD, NASDAQ:AAPL"},
            "interval": {"type": "string", "enum": ["1", "5", "15", "30", "60", "240", "D", "W"]},
        },
        "required": ["symbol"],
    },
    handler=_h_technical_analysis,
)
