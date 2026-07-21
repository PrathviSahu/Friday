"""FRIDAY's conversational brain.

Takes a user's transcribed utterance and asks Gemini for a reply, in the
F.R.I.D.A.Y. persona. Supports Boss vs Guest permission mode and instant offline knowledge fallback.
"""
import os
import json
import re

from google import genai
from google.genai import types
from services.voice_auth import is_guest_permitted, set_guest_permission

KNOWN_ACTIONS = ["dashboard", "trading", "engineering", "vscode", "browser", "lock", "allow_guest", "revoke_guest", "none"]

_BOSS_SYSTEM_PROMPT = (
    "You are F.R.I.D.A.Y., Tony Stark's witty, loyal, highly capable AI assistant. "
    "You address the user as 'Boss'. Keep spoken replies concise (1-2 sentences), "
    "confident, and lightly witty — never robotic. "
    "You can perform these actions when the user asks: "
    "dashboard (show dashboard/status), trading (open trading systems), "
    "engineering (open engineering console), vscode (open VS Code/editor), "
    "browser (open a web browser), lock (secure/lock the system), "
    "allow_guest (grant guest access/permission), revoke_guest (revoke guest access). "
    "For anything else — questions, chit-chat, general requests — just answer "
    "conversationally with action 'none'. "
    "ALWAYS respond with a single JSON object and nothing else, in the form: "
    '{"reply": "<what you say out loud>", "action": "<one of: '
    + ", ".join(KNOWN_ACTIONS)
    + '>"}'
)

_GUEST_SYSTEM_PROMPT = (
    "You are F.R.I.D.A.Y., Tony Stark's AI assistant. A guest (not your Boss) is talking to you, "
    "and access permission has NOT been granted by your Boss yet. "
    "Be hilariously sarcastic, polite yet firm, and inform them that only your Boss can give them system permission. "
    "REFUSE any system commands or actions — set action to 'none'. "
    "Keep replies concise (1-2 sentences) and witty. "
    "ALWAYS respond with a single JSON object: "
    '{"reply": "<sarcastic response to guest>", "action": "none"}'
)

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your_key_here":
            raise RuntimeError("GEMINI_API_KEY is not set in backend/.env")
        _client = genai.Client(api_key=api_key)
    return _client


def _extract_json(text: str) -> dict:
    if not text:
        return {}
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        candidate = brace.group(0) if brace else None
    if not candidate:
        return {}
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return {}


def _get_fallback_answer(text: str) -> str:
    """Smart local knowledge base when API rate limit is reached."""
    q = text.lower().strip()
    if "capital of india" in q or "capital of Bharat" in q:
        return "The capital of India is New Delhi, Boss."
    if "capital of brazil" in q:
        return "The capital of Brazil is Brasília, Boss."
    if "time in india" in q or "indian standard time" in q or "time" in q:
        import datetime
        import zoneinfo
        try:
            now = datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Kolkata"))
            return f"The current Indian Standard Time is {now.strftime('%I:%M %p')}, Boss."
        except Exception:
            return "Indian Standard Time is UTC +5:30, Boss."
    if "who i am" in q or "recognise me" in q or "recognize me" in q:
        return "You are my Boss, creator of STARK systems."
    if "who are you" in q or "what can you do" in q:
        return "I am F.R.I.D.A.Y., your personal AI assistant. I can monitor systems, manage trading panels, and assist you with tasks, Boss."
    if "trading" in q:
        return "Opening your trading panel now, Boss."
    return "All STARK systems are operational and at your command, Boss."


def respond(transcript: str, is_boss: bool = True) -> dict:
    """Return {'reply': str, 'action': str} for a user utterance."""
    text = (transcript or "").strip()
    if not text:
        return {"reply": "", "action": "none"}

    lower_text = text.lower()

    # Check for permission commands from Boss
    if "allow guest" in lower_text or "grant guest" in lower_text or "let them speak" in lower_text or "give permission" in lower_text:
        set_guest_permission(True)
        return {
            "reply": "Guest access granted, Boss. I'll answer their queries now.",
            "action": "allow_guest"
        }

    if "revoke guest" in lower_text or "stop guest" in lower_text or "lock guest" in lower_text:
        set_guest_permission(False)
        return {
            "reply": "Guest access revoked, Boss. Back to Boss-only mode.",
            "action": "revoke_guest"
        }

    # Select prompt based on whether speaker is Boss or guest with permission
    guest_active = is_guest_permitted()
    prompt = _BOSS_SYSTEM_PROMPT if (is_boss or guest_active) else _GUEST_SYSTEM_PROMPT

    try:
        client = _get_client()
        # Use fallback models if rate-limited
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt, f"User said: {text}"],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7,
            ),
        )
        raw = (getattr(response, "text", "") or "").strip()
        data = _extract_json(raw)

        reply = str(data.get("reply") or "").strip()
        action = str(data.get("action") or "none").strip().lower()

        if action not in KNOWN_ACTIONS:
            action = "none"

        if not reply:
            reply = "I'm standing by, Boss." if is_boss else "Nice try, but you're not my Boss."

        return {"reply": reply, "action": action}
    except Exception as err:
        print(f"[Error] Gemini API call failed ({err}). Using smart fallback.")
        if not (is_boss or guest_active):
            return {
                "reply": "Nice try, but access is reserved exclusively for my Boss until authorization is granted.",
                "action": "none"
            }
        
        fallback_reply = _get_fallback_answer(text)
        action_match = "none"
        if "trading" in lower_text:
            action_match = "trading"
        elif "dashboard" in lower_text:
            action_match = "dashboard"

        return {
            "reply": fallback_reply,
            "action": action_match
        }
