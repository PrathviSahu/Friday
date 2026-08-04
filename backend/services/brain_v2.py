"""brain_v2.py — Function Calling AI Brain (v3).

Replaces brain.py's 30-regex intent matching with true LLM function calling:

    User text
      → Groq (with all function schemas as tools) → tool_calls[]
          → dispatch to handler → reply
      → Gemini failover (structured JSON)
      → brain.respond() legacy fallback

The original brain.py remains fully functional as the fallback path.
"""

import json
import logging
import os

from services import function_engine
from services.brain import respond as legacy_respond
from services.memory import get_memory_context_string
from services.learning_engine import log_conversation

_BOSS_SYSTEM = (
    "You are F.R.I.D.A.Y., Tony Stark's witty, loyal AI assistant. "
    "You address the user as 'Prem' ONLY. Reply in 1-2 short sentences. "
    "Use the provided functions to fulfil requests — when you call a "
    "function, briefly acknowledge what you are doing. If no function fits, "
    "answer directly. Reply in English unless the user writes Hindi/Hinglish, "
    "in which case reply in natural Hinglish."
)


def _groq_client():
    from groq import Groq
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key or key == "your_key_here":
        return None
    return Groq(api_key=key)


def _call_groq_with_tools(text: str, tools: list) -> dict:
    """Ask Groq to choose functions. Returns {'tool_calls': [...], 'content': str}."""
    client = _groq_client()
    if client is None:
        raise RuntimeError("GROQ_API_KEY not configured")
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": _BOSS_SYSTEM},
            {"role": "user", "content": text},
        ],
        tools=tools,
        tool_choice="auto",
        max_tokens=600,
        temperature=0.3,
    )
    msg = resp.choices[0].message
    tool_calls = []
    if getattr(msg, "tool_calls", None):
        for tc in msg.tool_calls:
            fn = tc.function
            try:
                args = json.loads(fn.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append({"name": fn.name, "arguments": args})
    return {"tool_calls": tool_calls, "content": (msg.content or "").strip()}


def _call_gemini_fallback(text: str) -> dict:
    """Gemini failover: ask for a plain JSON {reply, action, function, args}."""
    from google import genai
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or key == "your_key_here":
        raise RuntimeError("GEMINI_API_KEY not configured")
    client = genai.Client(api_key=key)
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    tool_list = ", ".join(function_engine.list_functions())
    prompt = (
        f"You are F.R.I.D.A.Y. addressing the user as 'Prem'.\n"
        f"Available functions: {tool_list}.\n"
        f"User said: {text}\n"
        'Reply with ONLY JSON: {"reply": "...", "function": "<name or null>", "args": {...}}'
    )
    resp = client.models.generate_content(model=model, contents=prompt)
    raw = (getattr(resp, "text", "") or "").strip()
    # Strip code fences if present
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError(f"Gemini returned invalid JSON: {raw[:200]}")


def respond_v2(text: str, is_boss: bool = True, silence_tts: bool = False) -> dict:
    """Full function-calling brain entrypoint. Returns {'reply', 'action', ...}."""
    text = (text or "").strip()
    if not text:
        return {"reply": "", "action": "none"}

    log_conversation(role="user" if is_boss else "guest", message=text)

    # Step 1: Groq function calling
    try:
        tools = function_engine.get_tools_schema()
        result = _call_groq_with_tools(text, tools)
        tool_calls = result["tool_calls"]
        if tool_calls:
            # Execute the (first) chosen function and speak its result.
            tc = tool_calls[0]
            name, args = tc["name"], tc["arguments"]
            logging.info(f"[Brain v2] Calling function: {name}({args})")
            reply = function_engine.dispatch(name, args)
            return {"reply": reply, "action": "none", "engine": "brain_v2",
                    "function": name}
        if result["content"]:
            return {"reply": result["content"], "action": "none", "engine": "brain_v2"}
        raise RuntimeError("Groq returned no content and no tool calls")
    except Exception as e:
        logging.warning(f"[Brain v2] Groq tool path failed ({e}); trying Gemini...")

    # Step 2: Gemini structured failover
    try:
        parsed = _call_gemini_fallback(text)
        reply = parsed.get("reply") or "Done."
        fn_name = parsed.get("function")
        if fn_name and fn_name in function_engine.list_functions():
            reply = function_engine.dispatch(fn_name, parsed.get("args") or {})
            return {"reply": reply, "action": "none", "engine": "brain_v2",
                    "function": fn_name}
        return {"reply": reply, "action": "none", "engine": "brain_v2_gemini"}
    except Exception as e:
        logging.warning(f"[Brain v2] Gemini failover failed ({e}); falling back to legacy brain.")

    # Step 3: Legacy regex brain (always works, no API keys required for the
    # shortcut patterns; LLM paths inside may need keys).
    legacy = legacy_respond(text, is_boss, silence_tts)
    legacy["engine"] = "brain_v1"
    return legacy
