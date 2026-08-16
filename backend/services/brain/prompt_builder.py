"""services/brain/prompt_builder.py — Dynamic prompt assembly and proactive check-in generator."""

import os
import time
from services.memory import (
    save_fact,
    get_memory_context_string,
    log_conversation,
    get_recent_conversation
)
from services.system_control import get_spotify_current_track
from services.todos import get_todos
from services.reminders import check_due_reminders
from services.learning_engine import (
    get_proactive_habit_suggestion,
    BREVITY_INSTRUCTIONS
)
from services.brain.constants import (
    _BOSS_BASE_PROMPT,
    _GUEST_SYSTEM_PROMPT,
    KNOWN_ACTIONS
)
from services.brain.clients import _get_groq_client, _extract_json


def build_system_prompt(text: str, is_boss: bool, guest_active: bool, brevity_mode: str) -> str:
    """Assembles rich context (memories, live track, time, todos, RAG embeddings) for the LLM."""
    if is_boss:
        memory_str = get_memory_context_string()
        recent_history = get_recent_conversation(limit=4)
        history_str = "\n".join([f"{h['role'].upper()}: {h['message']}" for h in recent_history])

        # Semantic memory (Gemini embeddings RAG)
        try:
            from services.embeddings import semantic_context
            semantic_str = semantic_context(text, k=3)
        except Exception:
            semantic_str = ""

        # Live system context
        track = get_spotify_current_track()
        track_context = f"'{track.get('title')}' by {track.get('artist')} ({track.get('state')})" if track.get("title") else "Nothing playing."
        local_time_str = time.strftime("%I:%M %p")
        hour = int(time.strftime("%H"))

        if track.get("title"):
            save_fact("last_played_track", track.get("title"), "spotify")
            save_fact("last_played_artist", track.get("artist", ""), "spotify")

        try:
            todos = get_todos()
            pending = [t["text"] for t in todos if not t["done"]][:5]
            todo_context = f"{len(pending)} pending: " + ", ".join(pending) if pending else "No pending tasks."
        except Exception:
            todo_context = "Unable to fetch tasks."

        if 5 <= hour < 12:
            time_label = "morning"
        elif 12 <= hour < 17:
            time_label = "afternoon"
        elif 17 <= hour < 20:
            time_label = "evening"
        else:
            time_label = "night"

        return (
            f"{_BOSS_BASE_PROMPT}\n\n"
            f"[LIVE SYSTEM CONTEXT]\n"
            f"- Current Local Time: {local_time_str} ({time_label})\n"
            f"- Spotify: {track_context}\n"
            f"- Pending Tasks: {todo_context}\n"
            f"- App State: FRIDAY Dashboard Console Level 4 Active\n"
            f"PROACTIVE RULE: If Prem greets you (hello/hi/hey/kya haal hai) and it is {time_label}, "
            f"be context-aware: mention the time of day, current track if playing, or suggest something relevant. "
            f"At night/evening, optionally suggest a chill or devotional playlist.\n\n"
            f"[RESPONSE LENGTH INSTRUCTION] {BREVITY_INSTRUCTIONS.get(brevity_mode, '')}\n\n"
            f"[PERMANENT MEMORY & USER PREFERENCES]\n{memory_str}\n\n"
            f"[RECENT CONVERSATION HISTORY]\n{history_str}"
            + (f"\n\n[SEMANTICALLY RELEVANT MEMORIES]\n{semantic_str}" if semantic_str else "")
        )

    elif guest_active:
        recent_history = get_recent_conversation(limit=4)
        history_str = "\n".join([f"{h['role'].upper()}: {h['message']}" for h in recent_history])
        return (
            f"{_BOSS_BASE_PROMPT}\n\n"
            f"[NOTE: Permitted guest speaking — execute allowed media/app requests, but DO NOT reveal or save personal memories.]\n\n"
            f"[RECENT CONVERSATION HISTORY]\n{history_str}"
        )
    else:
        return _GUEST_SYSTEM_PROMPT


def get_proactive_suggestion() -> dict:
    """
    Generate a time-aware proactive suggestion or check due timers/reminders.
    Returns: { 'should_speak': bool, 'message': str, 'action': str }
    """
    # 🚨 First Priority: Check if any timers/reminders are due
    due = check_due_reminders()
    if due:
        rem = due[0]
        msg = f"Prem, reminder: {rem['message']}!"
        log_conversation(role="assistant", message=f"[REMINDER] {msg}")
        return {"should_speak": True, "message": msg, "action": "none"}

    # 🧠 Second Priority: Habit-based proactive suggestion from learning engine
    habit = get_proactive_habit_suggestion()
    if habit:
        log_conversation(role="assistant", message=f"[HABIT SUGGESTION] {habit['prompt']}")
        return {"should_speak": True, "message": habit["prompt"], "action": habit["action"]}

    hour = int(time.strftime("%H"))
    local_time_str = time.strftime("%I:%M %p")

    if 5 <= hour < 9:
        time_label = "early morning"
    elif 9 <= hour < 12:
        time_label = "morning"
    elif 12 <= hour < 14:
        time_label = "afternoon"
    elif 14 <= hour < 17:
        time_label = "late afternoon"
    elif 17 <= hour < 20:
        time_label = "evening"
    elif 20 <= hour < 23:
        time_label = "night"
    else:
        return {"should_speak": False, "message": "", "action": "none"}

    track = get_spotify_current_track()
    track_title = track.get("title", "")
    is_playing = track.get("playing", False)

    try:
        todos = get_todos()
        pending = [t["text"] for t in todos if not t["done"]]
    except Exception:
        pending = []

    memory_str = get_memory_context_string()

    proactive_prompt = (
        "You are F.R.I.D.A.Y., Tony Stark's AI assistant. You are proactively checking in on Prem — "
        "NOT responding to a question. Speak naturally in 1 short sentence, like a thoughtful assistant. "
        "Based on the context below, decide if there is something useful to say. "
        "If nothing useful, return should_speak=false.\n\n"
        f"Context:\n"
        f"- Current time: {local_time_str} ({time_label})\n"
        f"- Spotify: {'Playing: ' + track_title if is_playing else 'Nothing playing'}\n"
        f"- Pending tasks: {', '.join(pending[:3]) if pending else 'None'}\n"
        f"- Memory: {memory_str[:300]}\n\n"
        "Rules:\n"
        "- Morning (9 AM): Wish Prem good morning, mention pending tasks if any.\n"
        "- Afternoon (1 PM): Gently remind about lunch or any pending tasks.\n"
        "- Evening (6 PM): Suggest playing a chill playlist if nothing is playing.\n"
        "- Night (9 PM+): Suggest Radha Krishna bhajan or chill music, or say goodnight if tasks are done.\n"
        "- If Spotify is already playing a good track, say something appreciative about it.\n"
        "- Use witty Hinglish if appropriate, or plain English.\n"
        "- DO NOT announce if there is truly nothing interesting to say.\n\n"
        "Respond with ONLY a valid JSON object:\n"
        '{"should_speak": true/false, "message": "<1 sentence spoken message>", "action": "<play_hindi_playlist|play_english_playlist|play_krishna_playlist|none>"}'
    )

    groq_client = _get_groq_client()
    if groq_client:
        try:
            completion = groq_client.chat.completions.create(
                model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                messages=[{"role": "user", "content": proactive_prompt}],
                response_format={"type": "json_object"},
                temperature=0.6,
                max_tokens=150,
            )
            data = _extract_json(completion.choices[0].message.content or "")
            should_speak = bool(data.get("should_speak", False))
            message = str(data.get("message", "")).strip()
            action = str(data.get("action", "none")).strip()
            if action not in KNOWN_ACTIONS:
                action = "none"
            if should_speak and message:
                log_conversation(role="assistant", message=f"[PROACTIVE] {message}")
            return {"should_speak": should_speak, "message": message, "action": action}
        except Exception as err:
            print(f"[Proactive] LLM call failed: {err}")

    return {"should_speak": False, "message": "", "action": "none"}
