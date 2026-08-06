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
    "You address the user as 'Prem' ONLY. Be warm, sharp and concise.\n"
    "CONTEXT: you receive previous conversation turns and relevant memories — "
    "use them. Follow-ups like 'what about the day after?' refer to the "
    "last topic discussed. If the user asks about something you don't know, "
    "say so honestly rather than guessing.\n"
    "TOOLS: use the provided functions to fulfil requests. When a request "
    "needs several steps, call the tools one after another until the job is "
    "done, then answer. Never invent data — read it from tools.\n"
    "SENDING: functions named send_* / create_* only ever create a preview "
    "that Prem must confirm; never claim a message was sent when you only "
    "previewed it.\n"
    "STYLE: Reply in 1-2 short sentences. English input → English; "
    "Hindi/Hinglish input → natural Hinglish."
)


def _groq_client():
    from groq import Groq
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key or key == "your_key_here":
        return None
    return Groq(api_key=key)


def _build_context_messages(text: str) -> list:
    """System + recent conversation + memory context + semantic memories."""
    from services.learning_engine import get_recent_conversation, get_memory_context_string
    from services.embeddings import semantic_context

    messages = [{"role": "system", "content": _BOSS_SYSTEM}]

    # Rolling conversation history (last 6 turns, oldest first)
    for turn in get_recent_conversation(limit=6):
        role = turn.get("role")
        if role not in ("user", "assistant"):
            continue
        messages.append({"role": role, "content": turn.get("message", "")[:1000]})

    # Permanent facts + semantically relevant memories
    context_bits = [get_memory_context_string()]
    sem = semantic_context(text, k=3)
    if sem:
        context_bits.append(sem)
    if len(context_bits) > 1 or context_bits[0]:
        messages.append({"role": "system", "content": "\n\n".join(context_bits)})

    messages.append({"role": "user", "content": text})
    return messages


def _call_groq_with_messages(messages: list, tools: list) -> dict:
    """Ask Groq with a full message list. Returns {'tool_calls': [...], 'content': str}."""
    client = _groq_client()
    if client is None:
        raise RuntimeError("GROQ_API_KEY not configured")
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        max_tokens=700,
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
            tool_calls.append({
                "id": getattr(tc, "id", None) or "",
                "name": fn.name,
                "arguments": args,
            })
    return {"tool_calls": tool_calls, "content": (msg.content or "").strip()}


def _call_groq_with_tools(text: str, tools: list) -> dict:
    """Single-turn wrapper (kept for tests/back-compat): no history, no memory."""
    return _call_groq_with_messages(
        [{"role": "system", "content": _BOSS_SYSTEM}, {"role": "user", "content": text}],
        tools,
    )


def _call_gemini_fallback(text: str) -> dict:
    """Gemini failover: ask for a plain JSON {reply, action, function, args}."""
    from google import genai
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or key == "your_key_here":
        raise RuntimeError("GEMINI_API_KEY not configured")
    client = genai.Client(api_key=key)
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    tool_list = ", ".join(function_engine.list_functions())
    try:
        from services.learning_engine import get_memory_context_string, get_recent_conversation
        from services.embeddings import semantic_context
        history = "".join(
            f"\n{turn.get('role')}: {turn.get('message', '')[:400]}"
            for turn in get_recent_conversation(limit=4)
        )
        context = f"\nMemory: {get_memory_context_string()}\n"
        sem = semantic_context(text, k=3)
        if sem:
            context += f"{sem}\n"
    except Exception:
        history, context = "", ""
    prompt = (
        f"You are F.R.I.D.A.Y. addressing the user as 'Prem'.\n"
        f"Available functions: {tool_list}.\n"
        f"Recent conversation:{history}\n{context}"
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


def respond_v2(text: str, is_boss: bool = True, silence_tts: bool = False,
               tools_filter: list = None) -> dict:
    """Full function-calling brain entrypoint. Returns {'reply', 'action', ...}.

    `tools_filter`: optional list of function names to expose to the LLM
    (used by the multi-agent framework to scope each agent's capabilities).
    """
    text = (text or "").strip()
    if not text:
        return {"reply": "", "action": "none"}

    log_conversation(role="user" if is_boss else "guest", message=text)

    # Step 1: Groq function calling — MULTI-STEP AGENTIC LOOP.
    # The model can call tools repeatedly (each result fed back) until it
    # has everything it needs, then answers. Max 4 steps guards runaway loops.
    try:
        tools = function_engine.get_tools_schema()
        if tools_filter:
            allowed = set(tools_filter)
            tools = [t for t in tools if t["function"]["name"] in allowed]

        messages = _build_context_messages(text)
        executed = []
        final_content = ""
        last_tool_reply = ""
        max_steps = 4

        for _step in range(max_steps):
            from services.metrics import timed, set_last
            set_last(agent="brain_v2")
            with timed("llm", meta="groq-tools"):
                result = _call_groq_with_messages(messages, tools)
            tool_calls = result["tool_calls"]

            if not tool_calls:
                final_content = result["content"]
                break

            # Execute ALL tools requested in this turn, feed results back.
            for tc in tool_calls:
                name, args = tc.get("name"), tc.get("arguments") or {}
                logging.info(f"[Brain v2] Calling function: {name}({args})")
                reply = function_engine.dispatch(name, args)
                executed.append(name)
                last_tool_reply = reply
                # Assistant tool-call + tool result (OpenAI-style loop)
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": tc.get("id") or f"call_{len(messages)}",
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(args)},
                    }],
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id") or f"call_{len(messages) - 1}",
                    "content": reply,
                })

        if not final_content:
            # Loop exhausted without a final answer — wrap up with the last result.
            final_content = last_tool_reply

        result = {"reply": final_content or "Done.", "action": "none",
                  "engine": "brain_v2", "function": executed[-1] if executed else ""}

        # Approval-first confirm flows (last draft of each type wins).
        if "send_email" in executed:
            pending = function_engine.get_pending_email_draft()
            if pending:
                result["action"] = "email_confirm"
                result["email_draft_id"] = pending["id"]
                result["email_preview"] = {
                    "to": pending["to"],
                    "subject": pending["subject"],
                    "body": pending["body"],
                }
        if "create_calendar_event" in executed:
            pending = function_engine.get_pending_calendar_draft()
            if pending:
                result["action"] = "calendar_confirm"
                result["calendar_draft_id"] = pending["id"]
                result["calendar_preview"] = {
                    "summary": pending["summary"],
                    "start": pending["start"],
                    "end": pending["end"],
                    "description": pending["description"],
                }
        if "send_whatsapp" in executed:
            pending = function_engine.get_pending_whatsapp_draft()
            if pending:
                result["action"] = "whatsapp_confirm"
                result["whatsapp_draft_id"] = pending["id"]
                result["whatsapp_preview"] = {
                    "phone": pending["phone"],
                    "message": pending["message"],
                }
        if "send_whatsapp_desktop" in executed:
            pending = function_engine.get_pending_whatsapp_desktop_draft()
            if pending:
                result["action"] = "whatsapp_desktop_confirm"
                result["whatsapp_desktop_preview"] = {
                    "phone": pending["phone"],
                    "message": pending["message"],
                }
        return result
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
