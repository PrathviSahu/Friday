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
    send_whatsapp_desktop,
    open_whatsapp_desktop,
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
    from services.metrics import timed, set_last
    spec = _REGISTRY.get(name)
    if not spec:
        return f"Unknown function '{name}'."
    set_last(tool=name)
    try:
        with timed("tool", meta=name):
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
    # Also store as a searchable life-memory triple (Boss --key--> value)
    try:
        from services.life_memory import save_memory
        save_memory("Boss", key.replace("_", " "), value, category="fact")
    except Exception:
        pass
    return f"Remembered: {key} = {value}."


def _h_log_learning(args) -> str:
    from services.learning import log_session
    title = (args.get("title") or "Practice session").strip()
    category = (args.get("category") or "general").strip()
    minutes = int(args.get("minutes") or 30)
    solved = int(args.get("solved") or 0)
    log_session(title, category, minutes, solved)
    return f"Logged '{title}' — {minutes} minutes, {solved} problem(s) solved. Keep the streak alive, Boss!"


def _h_search_memories(args) -> str:
    from services.life_memory import answer_memory_query
    query = (args.get("query") or "").strip()
    if not query:
        return "Tell me what you'd like me to recall."
    return answer_memory_query(query)


def _h_remember_idea(args) -> str:
    from services.knowledge import add_note, auto_categorize
    title = (args.get("title") or "Idea").strip()
    content = (args.get("content") or args.get("idea") or "").strip()
    ntype = args.get("note_type") or auto_categorize(f"{title} {content}")
    nid = add_note(title, content, ntype, tags=args.get("tags"))
    return f"Captured as a {ntype.replace('_', ' ')} note: '{title}'."


def _h_search_notes(args) -> str:
    from services.knowledge import answer_notes_query
    query = (args.get("query") or "").strip()
    if not query:
        return "Tell me what you'd like me to find in your notes."
    return answer_notes_query(query)


def _h_log_milestone(args) -> str:
    from services.timeline import add_event
    event = (args.get("event") or "").strip()
    if not event:
        return "Please tell me what milestone to record."
    add_event(event, category=args.get("category") or "milestone",
              event_date=args.get("date"), detail=args.get("detail") or "")
    return f"Logged on your timeline: {event}."


def _h_update_goal(args) -> str:
    from services.goals import list_goals, increment_goal, create_goal
    title = (args.get("title") or "").strip()
    amount = float(args.get("amount") or 1)
    for g in list_goals():
        if title.lower() in g["title"].lower():
            updated = increment_goal(g["id"], amount)
            return f"Updated '{g['title']}' to {updated['current_value']}/{g['target_value']} {g['unit']}."
    # no match → create
    gid = create_goal(title or "New goal", category=args.get("category") or "personal",
                      target_value=float(args.get("target") or 100))
    return f"Created goal '{title}' — track progress by asking me to update it."


def _h_technical_analysis(args) -> str:
    from services.technical_analysis import analyze_symbol
    symbol = (args.get("symbol") or "FX:EURUSD").strip()
    interval = str(args.get("interval") or "15")
    result = analyze_symbol(symbol, interval)
    return result.get("summary") or result.get("error", "Analysis unavailable.")


# ── Email Agent handlers ─────────────────────────────────────────────────

# Set whenever send_email creates a draft, so brain_v2 can surface the
# email_confirm action (the frontend then drives the approval flow).
_pending_email_draft = None


def get_pending_email_draft() -> dict | None:
    """Return and clear the most recently created email draft (for confirm flow)."""
    global _pending_email_draft
    draft = _pending_email_draft
    _pending_email_draft = None
    return draft


def _h_check_email(args) -> str:
    from services import email_agent
    if not email_agent.is_configured():
        return ("Email isn't configured yet, Boss. Add FRIDAY_EMAIL_HOST, "
                "FRIDAY_EMAIL_USER and FRIDAY_EMAIL_PASS to backend/.env to enable it.")
    try:
        s = email_agent.summarize_inbox(limit=20)
    except Exception as err:
        return f"I couldn't reach your inbox: {err}"
    lines = [f"You have {s['unread_count']} unread emails."]
    if s["priority"]:
        top = "; ".join(f"{m['from_name']} — {m['subject'][:48]}" for m in s["priority"][:3])
        lines.append(f"Priority: {top}.")
    if s["by_sender"]:
        senders = ", ".join(f"{m['name']} ({m['count']})" for m in s["by_sender"][:4])
        lines.append(f"Top senders: {senders}.")
    return " ".join(lines)


def _h_search_email(args) -> str:
    from services import email_agent
    query = (args.get("query") or "").strip()
    if not query:
        return "What should I search your email for?"
    if not email_agent.is_configured():
        return "Email isn't configured yet, Boss."
    try:
        results = email_agent.search_emails(query, limit=5)
    except Exception as err:
        return f"I couldn't search your inbox: {err}"
    if not results:
        return f"No emails matched '{query}'."
    lines = [f"Found {len(results)} email(s) matching '{query}':"]
    for m in results:
        lines.append(f"- {m['from_name']}: {m['subject'][:60]}")
    return " ".join(lines)


def _h_send_email(args) -> str:
    from services import email_agent
    to = (args.get("to") or "").strip()
    subject = (args.get("subject") or "").strip()
    body = (args.get("body") or "").strip()
    if not email_agent.is_configured():
        return "Email isn't configured yet, Boss."
    try:
        draft = email_agent.create_draft(to, subject, body)
    except ValueError as err:
        return str(err)
    global _pending_email_draft
    _pending_email_draft = draft
    return (f"Draft ready for {draft['to']} — subject: {draft['subject'] or '(none)'}. "
            "I won't send it until you confirm.")


# ── Calendar Agent handlers ──────────────────────────────────────────────

_pending_calendar_draft = None


def get_pending_calendar_draft() -> dict | None:
    """Return and clear the most recently created calendar draft."""
    global _pending_calendar_draft
    draft = _pending_calendar_draft
    _pending_calendar_draft = None
    return draft


def _h_check_calendar(args) -> str:
    from services import calendar_agent
    if not calendar_agent.is_configured():
        return ("Calendar isn't connected yet, Boss. Add a Google OAuth client as "
                "backend/credentials.json with the Calendar API enabled.")
    try:
        events = calendar_agent.get_today()
    except Exception as err:
        return f"I couldn't reach your calendar: {err}"
    return calendar_agent.format_events_for_speech(events, "today")


def _h_search_calendar(args) -> str:
    from services import calendar_agent
    query = (args.get("query") or "").strip()
    if not query:
        return "What should I search your calendar for?"
    if not calendar_agent.is_configured():
        return "Calendar isn't connected yet, Boss."
    try:
        events = calendar_agent.search_events(query)
    except Exception as err:
        return f"I couldn't search your calendar: {err}"
    if not events:
        return f"No events matched '{query}'."
    lines = [f"Found {len(events)} event(s):"]
    for e in events[:5]:
        lines.append(f"- {calendar_agent._pretty_time(e['start'])}: {e['summary']}")
    return " ".join(lines)


def _h_create_calendar_event(args) -> str:
    from services import calendar_agent
    if not calendar_agent.is_configured():
        return "Calendar isn't connected yet, Boss."
    try:
        draft = calendar_agent.create_draft(
            args.get("summary") or "", args.get("start") or "",
            args.get("end") or "", args.get("description") or "",
        )
    except ValueError as err:
        return str(err)
    global _pending_calendar_draft
    _pending_calendar_draft = draft
    return (f"Event ready — {calendar_agent.format_event_preview(draft)}. "
            "I won't create it until you confirm.")


# ── Meeting Assistant handlers ───────────────────────────────────────────

def _h_meeting_action_items(args) -> str:
    from services import meeting_agent
    items = meeting_agent.get_action_items()
    if not items:
        return "No action items from your meetings yet."
    lines = [f"{len(items)} action item(s) from your meetings:"]
    for it in items[:5]:
        owner = f" ({it['owner']})" if it.get("owner") else ""
        lines.append(f"- {it['text']}{owner}")
    return " ".join(lines)


def _h_search_meetings(args) -> str:
    from services import meeting_agent
    query = (args.get("query") or "").strip()
    if not query:
        return "What should I search your meetings for?"
    results = meeting_agent.search_meetings(query, limit=5)
    if not results:
        return f"No meetings matched '{query}'."
    lines = [f"Found {len(results)} meeting(s):"]
    for m in results:
        lines.append(f"- {m['title']} — {m['summary'][:80]}")
    return " ".join(lines)


def _h_last_meeting(args) -> str:
    from services import meeting_agent
    meetings = meeting_agent.list_meetings(limit=1)
    if not meetings:
        return "No meetings recorded yet, Boss."
    return meeting_agent.format_meeting_for_speech(meetings[0])


# ── WhatsApp Agent handlers (experimental driver) ────────────────────────

_pending_whatsapp_draft = None


def get_pending_whatsapp_draft() -> dict | None:
    """Return and clear the most recently created WhatsApp draft."""
    global _pending_whatsapp_draft
    draft = _pending_whatsapp_draft
    _pending_whatsapp_draft = None
    return draft


def _h_check_whatsapp(args) -> str:
    from services import whatsapp_agent
    if not whatsapp_agent.ENABLED:
        return ("WhatsApp is disabled, Boss — set FRIDAY_WHATSAPP_ENABLED=1 in "
                "backend/.env to enable the experimental driver.")
    try:
        s = whatsapp_agent.summarize()
    except whatsapp_agent.WhatsAppUnavailableError as err:
        return f"WhatsApp isn't connected yet: {err}"
    if not s.get("unread_count"):
        return "No unread WhatsApp messages."
    lines = [f"You have {s['unread_count']} unread WhatsApp messages."]
    for c in s.get("chats", [])[:3]:
        lines.append(f"- {c['name']} ({c['unread']})")
    return " ".join(lines)


def _h_search_whatsapp(args) -> str:
    from services import whatsapp_agent
    query = (args.get("query") or "").strip()
    if not query:
        return "What should I search your WhatsApp for?"
    if not whatsapp_agent.ENABLED:
        return "WhatsApp is disabled, Boss."
    try:
        results = whatsapp_agent.search_messages(query, limit=5)
    except whatsapp_agent.WhatsAppUnavailableError as err:
        return f"Couldn't search WhatsApp: {err}"
    if not results:
        return f"Nothing matched '{query}' in WhatsApp."
    return "Found: " + ", ".join(f"{c['name']} ({c['unread']} unread)" for c in results)


def _h_send_whatsapp(args) -> str:
    from services import whatsapp_agent
    if not whatsapp_agent.ENABLED:
        return ("WhatsApp is disabled, Boss — set FRIDAY_WHATSAPP_ENABLED=1 in "
                "backend/.env to enable the experimental driver.")
    try:
        draft = whatsapp_agent.create_draft(
            args.get("phone") or "", args.get("message") or ""
        )
    except ValueError as err:
        return str(err)
    global _pending_whatsapp_draft
    _pending_whatsapp_draft = draft
    return (f"Message ready for +{draft['phone']}: \"{draft['message'][:80]}\". "
            "I won't send it until you confirm.")


# ── WhatsApp Desktop (native macOS app) handlers ───────────────────────

_pending_whatsapp_desktop_draft = None

def get_pending_whatsapp_desktop_draft() -> dict | None:
    """Return and clear the most recently created WhatsApp Desktop draft."""
    global _pending_whatsapp_desktop_draft
    draft = _pending_whatsapp_desktop_draft
    _pending_whatsapp_desktop_draft = None
    return draft

def _h_send_whatsapp_desktop(args) -> str:
    """Draft a WhatsApp message to be sent via the WhatsApp Desktop app on macOS."""
    phone = (args.get("phone") or "").strip()
    message = (args.get("message") or "").strip()
    if not phone:
        return "I need a phone number with country code to send a WhatsApp message."
    if not message:
        return "What would you like the message to say?"

    # Store as a pending draft — the frontend will show an approval card.
    # Only after the user confirms do we actually open WhatsApp Desktop and send.
    import re as _re
    digits = _re.sub(r'\D', '', phone)
    if len(digits) < 10 or len(digits) > 15:
        return "That phone number doesn't look right — use country code + number, e.g. 919876543210."

    global _pending_whatsapp_desktop_draft
    _pending_whatsapp_desktop_draft = {"phone": digits, "message": message[:1000]}
    return (f"Message ready for +{digits}: \"{message[:80]}\". "
            "I'll send it through WhatsApp Desktop on your Mac once you confirm.")

def _h_open_whatsapp_desktop(args) -> str:
    """Open the WhatsApp Desktop app on macOS, optionally with a specific chat."""
    phone = (args.get("phone") or "").strip()
    ok = open_whatsapp_desktop(phone)
    if ok:
        if phone:
            return f"Opening WhatsApp chat with +{phone}."
        return "Opening WhatsApp Desktop."
    return "I couldn't open WhatsApp Desktop — is it installed?"


# ── Document AI handlers ─────────────────────────────────────────────────

def _h_search_documents(args) -> str:
    from services import document_agent
    query = (args.get("query") or "").strip()
    results = document_agent.search_documents(query) if query else document_agent.list_documents(limit=5)
    if not results:
        return "No documents found, Boss."
    lines = [f"Found {len(results)} document(s):"]
    lines += [f"- {d['title']} ({d['ext']})" for d in results[:5]]
    return " ".join(lines)


def _h_ask_document(args) -> str:
    from services import document_agent
    query = (args.get("document") or "").strip()
    question = (args.get("question") or "").strip()
    if not question:
        return "What would you like to ask about the document?"
    doc = document_agent.find_document_by_keyword(query) if query else None
    if not doc:
        return "I couldn't find a matching document, Boss."
    try:
        return document_agent.ask_document(doc["id"], question)
    except document_agent.DocumentUnavailableError as err:
        return f"I couldn't answer that: {err}"


def _h_summarize_document(args) -> str:
    from services import document_agent
    query = (args.get("document") or "").strip()
    doc = document_agent.find_document_by_keyword(query) if query else None
    if not doc:
        return "I couldn't find a matching document, Boss."
    try:
        return document_agent.summarize_document(doc["id"])
    except document_agent.DocumentUnavailableError as err:
        return f"I couldn't summarize that: {err}"


# ── Coding AI handler ────────────────────────────────────────────────────

def _h_coding_review(args) -> str:
    from services import coding_agent
    code = (args.get("code") or "").strip()
    language = (args.get("language") or "").strip()
    if not code:
        return "No code provided to review, Boss."
    try:
        return coding_agent.review_code(code, language)[:600]
    except coding_agent.CodingUnavailableError as err:
        return f"I couldn't review that: {err}"


# ── Company Intelligence handler ─────────────────────────────────────────

def _h_company_intel(args) -> str:
    from services import company_intelligence
    name = (args.get("company") or "").strip()
    if not name:
        return "Which company should I research, Boss?"
    try:
        intel = company_intelligence.get_company_intel(name)
        return company_intelligence.format_for_speech(intel)
    except company_intelligence.CompanyIntelUnavailableError as err:
        return f"I couldn't research that company: {err}"


# ═══════════════════════════════════════════════════════════════════════════════
# Registrations (41 functions)
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


register_function(
    name="log_learning",
    description="Record a learning / practice session (DSA, Java, AWS, interview prep, etc.) for the Learning Coach.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "What you practiced"},
            "category": {"type": "string", "enum": ["dsa", "java", "system_design", "aws", "interview_prep", "general"]},
            "minutes": {"type": "integer", "description": "Minutes spent"},
            "solved": {"type": "integer", "description": "Problems solved"},
        },
        "required": ["title"],
    },
    handler=_h_log_learning,
)

register_function(
    name="search_memories",
    description="Search FRIDAY's long-term life memory (facts about the user: preferences, people, dates, rules).",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "What to recall, e.g. 'salary preference' or 'birthday'"}},
        "required": ["query"],
    },
    handler=_h_search_memories,
)


register_function(
    name="remember_idea",
    description="Capture an idea or note into FRIDAY's second brain (auto-categorized).",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short title"},
            "content": {"type": "string", "description": "The idea or note content"},
            "note_type": {"type": "string", "enum": ["meeting", "idea", "research", "code_snippet", "interview", "decision", "book", "youtube", "general"]},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["title"],
    },
    handler=_h_remember_idea,
)

register_function(
    name="search_notes",
    description="Search FRIDAY's second brain knowledge base for notes, ideas, or project memory.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "What to find, e.g. 'Kafka architecture idea'"}},
        "required": ["query"],
    },
    handler=_h_search_notes,
)

register_function(
    name="log_milestone",
    description="Record a milestone on FRIDAY's memory timeline (certifications, projects finished, skills learned).",
    parameters={
        "type": "object",
        "properties": {
            "event": {"type": "string", "description": "The milestone, e.g. 'Finished AI Attendance System'"},
            "category": {"type": "string", "enum": ["career", "learning", "project", "skill", "milestone", "personal"]},
            "date": {"type": "string", "description": "ISO date (YYYY-MM-DD), defaults to today"},
        },
        "required": ["event"],
    },
    handler=_h_log_milestone,
)

register_function(
    name="update_goal",
    description="Create or update progress on a goal (e.g. '8 LPA job', 'solve 100 DSA problems').",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Goal title"},
            "amount": {"type": "number", "description": "How much progress to add (default 1)"},
            "category": {"type": "string"},
            "target": {"type": "number", "description": "Target value when creating a new goal"},
        },
        "required": ["title"],
    },
    handler=_h_update_goal,
)

register_function(
    name="check_email",
    description="Check the user's email inbox: unread count, priority emails and top senders.",
    parameters={"type": "object", "properties": {}},
    handler=_h_check_email,
)

register_function(
    name="search_email",
    description="Search the user's email inbox by subject or sender.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "Search term"}},
        "required": ["query"],
    },
    handler=_h_search_email,
)

register_function(
    name="send_email",
    description=(
        "Draft an email to a recipient. NEVER sends anything: it only creates a "
        "preview and the user must explicitly confirm before it is sent."
    ),
    parameters={
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address"},
            "subject": {"type": "string", "description": "Email subject"},
            "body": {"type": "string", "description": "Email body text"},
        },
        "required": ["to", "subject", "body"],
    },
    handler=_h_send_email,
)

register_function(
    name="check_calendar",
    description="Check the user's calendar: today's events with times.",
    parameters={"type": "object", "properties": {}},
    handler=_h_check_calendar,
)

register_function(
    name="search_calendar",
    description="Search the user's calendar events by title/keyword.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "Search term"}},
        "required": ["query"],
    },
    handler=_h_search_calendar,
)

register_function(
    name="create_calendar_event",
    description=(
        "Create a calendar event. NEVER creates anything: it only makes a preview "
        "and the user must explicitly confirm. Use 24h ISO dates like 2026-08-06T15:00:00."
    ),
    parameters={
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Event title"},
            "start": {"type": "string", "description": "Start, YYYY-MM-DDTHH:MM:SS (24h)"},
            "end": {"type": "string", "description": "End, YYYY-MM-DDTHH:MM:SS (24h)"},
            "description": {"type": "string", "description": "Optional details"},
        },
        "required": ["summary", "start"],
    },
    handler=_h_create_calendar_event,
)

register_function(
    name="meeting_action_items",
    description="Get outstanding action items extracted from the user's meetings.",
    parameters={"type": "object", "properties": {}},
    handler=_h_meeting_action_items,
)

register_function(
    name="search_meetings",
    description="Search the user's recorded meetings by title, summary or transcript.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "Search term"}},
        "required": ["query"],
    },
    handler=_h_search_meetings,
)

register_function(
    name="last_meeting",
    description="Summarize the user's most recent meeting, including its action items.",
    parameters={"type": "object", "properties": {}},
    handler=_h_last_meeting,
)

register_function(
    name="check_whatsapp",
    description="Check the user's WhatsApp: unread messages and unread chat names.",
    parameters={"type": "object", "properties": {}},
    handler=_h_check_whatsapp,
)

register_function(
    name="search_whatsapp",
    description="Search the user's WhatsApp chats by contact name.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "Contact name to find"}},
        "required": ["query"],
    },
    handler=_h_search_whatsapp,
)

register_function(
    name="send_whatsapp",
    description=(
        "Draft a WhatsApp message to a phone number (with country code, digits only). "
        "NEVER sends anything: it only creates a preview and the user must confirm."
    ),
    parameters={
        "type": "object",
        "properties": {
            "phone": {"type": "string", "description": "Phone with country code, digits only, e.g. 919876543210"},
            "message": {"type": "string", "description": "Message text"},
        },
        "required": ["phone", "message"],
    },
    handler=_h_send_whatsapp,
)

register_function(
    name="send_whatsapp_desktop",
    description=(
        "Draft a WhatsApp message to send via the WhatsApp Desktop app installed on the Mac. "
        "Uses the native WhatsApp app (not WhatsApp Web). NEVER sends anything directly: "
        "it only creates a preview and the user must confirm before sending."
    ),
    parameters={
        "type": "object",
        "properties": {
            "phone": {"type": "string", "description": "Phone with country code, digits only, e.g. 919876543210"},
            "message": {"type": "string", "description": "Message text to send"},
        },
        "required": ["phone", "message"],
    },
    handler=_h_send_whatsapp_desktop,
)

register_function(
    name="open_whatsapp_desktop",
    description="Open the WhatsApp Desktop app on macOS. Can optionally open a specific chat by phone number.",
    parameters={
        "type": "object",
        "properties": {
            "phone": {"type": "string", "description": "Optional phone number to open a specific chat"},
        },
    },
    handler=_h_open_whatsapp_desktop,
)

register_function(
    name="search_documents",
    description="Search the user's uploaded documents (PDF/DOCX/PPTX/XLSX/TXT) by keyword.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "Search term"}},
        "required": ["query"],
    },
    handler=_h_search_documents,
)

register_function(
    name="ask_document",
    description="Ask a question about an uploaded document (find it by title/keyword first).",
    parameters={
        "type": "object",
        "properties": {
            "document": {"type": "string", "description": "Title or keyword identifying the document"},
            "question": {"type": "string", "description": "The question to answer from the document"},
        },
        "required": ["document", "question"],
    },
    handler=_h_ask_document,
)

register_function(
    name="summarize_document",
    description="Summarize an uploaded document (find it by title/keyword first).",
    parameters={
        "type": "object",
        "properties": {"document": {"type": "string", "description": "Title or keyword identifying the document"}},
        "required": ["document"],
    },
    handler=_h_summarize_document,
)

register_function(
    name="company_intel",
    description="Research a company: overview, hiring signals, your application history, interview prep.",
    parameters={
        "type": "object",
        "properties": {"company": {"type": "string", "description": "Company name, e.g. Goldman Sachs"}},
        "required": ["company"],
    },
    handler=_h_company_intel,
)

register_function(
    name="review_code",
    description="Review pasted code: bugs, security, performance, style. Requires the code text.",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "The code to review"},
            "language": {"type": "string", "description": "Optional language hint"},
        },
        "required": ["code"],
    },
    handler=lambda args: _h_coding_review(args),
)


# ── Phase 2.3: Ambient Context tools ──────────────────────────────────────────

def _h_get_context(args: dict) -> str:
    from services import context_engine
    return context_engine.describe()


def _h_set_focus_mode(args: dict) -> str:
    from services import context_engine
    minutes = int(args.get("minutes") or 60)
    result = context_engine.set_focus(minutes)
    if result.get("status") != "ok":
        return f"I couldn't enable focus mode: {result.get('message')}."
    return (f"Focus mode on for {minutes} minutes, Prem. I'll hold all "
            "suggestions and non-critical notifications until then.")


register_function(
    name="get_context",
    description="Get FRIDAY's live situational awareness: time of day, market status, next meeting, unread emails, focus mode.",
    parameters={"type": "object", "properties": {}},
    handler=_h_get_context,
)

register_function(
    name="set_focus_mode",
    description="Enable focus/do-not-disturb mode for N minutes — mutes proactive suggestions and forces approval-first on autonomy.",
    parameters={
        "type": "object",
        "properties": {"minutes": {"type": "integer", "description": "Focus duration, 5–480 (default 60)"}},
    },
    handler=_h_set_focus_mode,
)


# ── Phase 2.4: Voice Macro tools ──────────────────────────────────────────────

register_function(
    name="create_macro",
    description="Create a voice macro: when the user says a trigger phrase, run a sequence of tool steps. Use when Prem says 'when I say X, do A then B'.",
    parameters={
        "type": "object",
        "properties": {
            "trigger": {"type": "string", "description": "The trigger phrase, e.g. 'start my morning'"},
            "steps": {
                "type": "array",
                "description": "Ordered tool steps",
                "items": {
                    "type": "object",
                    "properties": {
                        "tool": {"type": "string", "description": "Registered tool name, e.g. 'open_trading'"},
                        "params": {"type": "object", "description": "Tool arguments (optional)"},
                    },
                    "required": ["tool"],
                },
            },
        },
        "required": ["trigger", "steps"],
    },
    handler=lambda args: __import__("services.macros", fromlist=["handle_create_macro"]).handle_create_macro(args),
)

register_function(
    name="delete_macro",
    description="Delete a previously created voice macro by its trigger phrase.",
    parameters={
        "type": "object",
        "properties": {"trigger": {"type": "string", "description": "The macro's trigger phrase"}},
        "required": ["trigger"],
    },
    handler=lambda args: __import__("services.macros", fromlist=["handle_delete_macro"]).handle_delete_macro(args),
)
