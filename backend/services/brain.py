"""FRIDAY's Adaptive Learning & Dual-Engine Hybrid Brain.

Uses:
1. Groq (Llama 3.3 70B) for ultra-fast (~150ms) real-time voice conversation, OS application automation, Spotify media control, & UI control.
2. Gemini (Gemini 2.5) for complex multimodal/document processing & fallbacks.
"""
import os
import json
import re
import time
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend/.env environment variables are loaded
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from groq import Groq
from google import genai
from google.genai import types

from services.voice_auth import is_guest_permitted, set_guest_permission
from services.memory import (
    save_fact,
    get_memory_context_string,
    log_conversation,
    get_recent_conversation
)
from services.system_control import execute_system_command

KNOWN_ACTIONS = [
    "dashboard", "trading", "engineering", "vscode", "browser",
    "lock", "allow_guest", "revoke_guest", "remember",
    "open_spotify", "close_spotify", "play_hindi_playlist", "play_english_playlist",
    "play_specific", "play_music", "pause_music", "toggle_music", "next_track", "previous_track",
    "volume_up", "volume_down", "set_volume", "mute", "repeat", "shuffle",
    "open_brave", "open_youtube", "open_app", "close_app", "search_web", "none"
]

_BOSS_BASE_PROMPT = (
    "You are F.R.I.D.A.Y., Tony Stark's witty, loyal, highly intelligent AI assistant with PC & Spotify media control access. "
    "You address the user exclusively as 'Prem'. Keep spoken replies concise (1-2 sentences), confident, and witty. "
    "CRITICAL SPEECH-TO-TEXT FUZZY RECOVERY RULES: "
    "Browser STT often mishears words phonetically when the user speaks! "
    "Examples of STT misinterpretations: "
    "- 'help away by Tempo city' OR 'temper city' OR 'temper city on my spotify' -> 'Self Aware by Temper City' "
    "- 'if friday please' -> 'Friday play' "
    "- 'decrease the music' OR 'lower music' OR 'lower volume' -> set action to 'volume_down' "
    "- 'sound at 70' OR 'sound at 70%' -> set volume_percent to 70 "
    "IMPORTANT: ONLY set action to 'play_specific' if the user explicitly asks to play a specific song or artist name (e.g. 'play Kesariya', 'play Starboy'). "
    "For general media commands ('decrease music', 'volume down', 'pause', 'next song'), use the respective media action! "
    "ACTIONS: "
    "- volume_down: decrease volume / lower the music "
    "- volume_up: increase volume / raise the music "
    "- play_specific: search & play a specific song on Spotify "
    "- play_hindi_playlist / play_english_playlist "
    "- pause_music / play_music / set_volume / mute / next_track / previous_track / repeat / shuffle / open_spotify / close_spotify "
    "ALWAYS respond with ONLY a single valid JSON object in the form: "
    '{"reply": "<spoken output>", "action": "<action>", "target_app": "<optional song/app>", "volume_percent": -1, "remember_key": null, "remember_value": null}'
)

_GUEST_SYSTEM_PROMPT = (
    "You are F.R.I.D.A.Y., Tony Stark's AI assistant. A guest (not your owner Prem) is talking to you, "
    "and access permission has NOT been granted by Prem yet. "
    "Be hilariously sarcastic, polite yet firm, and inform them that only Prem can give them system permission. "
    "REFUSE any system commands, Spotify control, or memory updates — set action to 'none'. "
    "Keep replies concise (1-2 sentences) and witty. "
    "ALWAYS respond with a single JSON object: "
    '{"reply": "<sarcastic response to guest>", "action": "none"}'
)

_groq_client = None
_gemini_client = None


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            _groq_client = Groq(api_key=api_key)
    return _groq_client


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and api_key != "your_key_here":
            _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


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


def _handle_system_automation(action: str, target: str, volume_percent: int = -1) -> str:
    """Helper to dispatch system commands to macOS execution engine."""
    if action in KNOWN_ACTIONS and action not in ["dashboard", "trading", "engineering", "vscode", "browser", "lock", "allow_guest", "revoke_guest", "remember", "none"]:
        return execute_system_command(action, target, volume_percent=volume_percent)
    return ""


def respond(transcript: str, is_boss: bool = True) -> dict:
    """Return {'reply': str, 'action': str} for a user utterance using Groq Fuzzy Intent Corrector LLM + Gemini failover."""
    text = (transcript or "").strip()
    if not text:
        return {"reply": "", "action": "none"}

    lower_text = text.lower()
    guest_active = is_guest_permitted()
    authorized = is_boss or guest_active

    # FIX: Define extracted_vol unconditionally here so all code paths can reference it cleanly
    # Matches: "volume 30%", "sound at 70", "set volume to 100", "30 percent", "100%"
    vol_match = re.search(
        r'(?:(?:sound|volume)\s*(?:at|to|is|=)?\s*(\d{1,3})(?:\s*%|\s*percent)?)'
        r'|(?:(\d{1,3})\s*(?:%|percent)\b)',
        lower_text
    )
    if vol_match:
        raw_vol = vol_match.group(1) or vol_match.group(2)
        extracted_vol = int(raw_vol)
    else:
        extracted_vol = -1

    # Log user turn to memory history
    log_conversation(role="user" if is_boss else "guest", message=text)

    # Ignore isolated single non-command filler words like "please"
    if lower_text in ["please", "pls", "thank you", "thanks"]:
        return {"reply": "", "action": "none"}

    # SECURITY & PERMISSION MANAGEMENT (Prem only)
    if is_boss:
        if any(kw in lower_text for kw in ["allow guest", "grant guest", "let them speak", "give permission"]):
            set_guest_permission(True)
            reply_msg = "Guest access granted, Prem. I'll answer their queries now."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "allow_guest"}

        if any(kw in lower_text for kw in ["revoke guest", "stop guest", "lock guest"]):
            set_guest_permission(False)
            reply_msg = "Guest access revoked, Prem. Back to private mode."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "revoke_guest"}

        # Auto-correct name spelling in incoming transcript before memory or processing
        if any(kw in lower_text for kw in ["prithvi", "p r i t h v i", "r a not i", "spelling is"]):
            save_fact("boss_name", "Prathvi Sahu", "identity")
            save_fact("boss_name_spelling", "P-R-A-T-H-V-I S-A-H-U", "identity")

    # GATED MEDIA SHORTCUTS (Checked BEFORE LLM call)
    if authorized:
        # 0. SET VOLUME TO SPECIFIC PERCENTAGE (e.g. "volume 30%", "set volume to 100", "70 percent")
        # Must have a valid percentage AND a clear volume-setting intent (not a song play request)
        pct_match = re.search(r'(?:set\s+(?:the\s+)?(?:volume|sound)|(?:volume|sound)\s+(?:at|to|is)?\s*|(\d{1,3})\s*(?:percent|%))', lower_text)
        if extracted_vol >= 0 and not re.search(r'\bplay\b', lower_text):
            result = execute_system_command("set_volume", "", volume_percent=extracted_vol)
            reply_msg = result or f"Setting volume to {extracted_vol}%, Prem."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "set_volume"}

        # FIX #3: Use regex patterns for volume to avoid 'turn down for what', 'play louder song' triggering volume commands
        # 1. VOLUME DOWN SHORTCUT
        if re.search(r'(?:turn|lower|decrease|bring|take)\s+(?:the\s+)?(?:volume|music|sound|it)\s*(?:down)?|volume\s*down|quieter', lower_text):
            result = execute_system_command("volume_down", "")
            reply_msg = result or "Decreasing volume, Prem."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "volume_down"}

        # 2. VOLUME UP SHORTCUT
        if re.search(r'(?:turn|raise|increase|bring|take)\s+(?:the\s+)?(?:volume|music|sound|it)\s*(?:up)?|volume\s*up|louder', lower_text):
            result = execute_system_command("volume_up", "")
            reply_msg = result or "Increasing volume, Prem."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "volume_up"}

        # 3. UNPAUSE / RESUME SHORTCUT
        if re.search(r'\b(?:unpause|resume)\b', lower_text):
            execute_system_command("play_music", "")
            reply_msg = "Resuming Spotify music, Prem."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "play_music"}

        # 4. PAUSE / STOP MUSIC SHORTCUT
        if re.search(r'\b(?:pause|pause music|stop music|stop playing|stop the song|stop the music|hold on)\b', lower_text) or lower_text == "stop":
            execute_system_command("pause_music", "")
            reply_msg = "Pausing Spotify music, Prem."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "pause_music"}

        # 4.5. PLAYLIST SHORTCUTS (must come BEFORE generic play-song shortcut)
        if re.search(r'\b(?:hindi|meri|apni|bollywood)\b.*\b(?:playlist|songs|music)\b|\b(?:playlist|songs|music)\b.*\b(?:hindi|bollywood)\b', lower_text):
            result = execute_system_command("play_hindi_playlist", "", volume_percent=extracted_vol)
            reply_msg = result or "Playing your Hindi playlist, Prem."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "play_hindi_playlist"}

        if re.search(r'\b(?:english|english playlist|angrezi)\b.*\b(?:playlist|songs|music)\b|\b(?:playlist|songs|music)\b.*\b(?:english|angrezi)\b', lower_text):
            result = execute_system_command("play_english_playlist", "", volume_percent=extracted_vol)
            reply_msg = result or "Playing your English playlist, Prem."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "play_english_playlist"}

        if re.search(r'\b(?:krishna|radha|radha krishna|radhe krishna|bhajan|devotional)\b', lower_text):
            result = execute_system_command("play_krishna_playlist", "", volume_percent=extracted_vol)
            reply_msg = result or "Playing your Krishna playlist, Prem."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "play_krishna_playlist"}

        # 4.6. SHUFFLE SHORTCUT (e.g. "shuffle", "play on shuffle", "turn on shuffle", "play it on shuffel")
        if re.search(r'\b(?:shuffle|shuffel)\b', lower_text):
            execute_system_command("shuffle", "")
            reply_msg = "Enabling Spotify shuffle mode, Prem."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "shuffle"}

        # 4.7. NEXT TRACK / PREVIOUS TRACK SHORTCUTS (must come BEFORE generic play-song shortcut)
        if re.search(r'\b(?:next|skip|play next|next song|next track)\b', lower_text):
            execute_system_command("next_track", "")
            reply_msg = "Skipping to the next track, Prem."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "next_track"}

        if re.search(r'\b(?:previous|prev|previous song|previous track|play previous|go back)\b', lower_text):
            execute_system_command("previous_track", "")
            reply_msg = "Playing the previous track, Prem."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "previous_track"}

        # 5. PHONETIC SONG SHORTCUT
        if any(kw in lower_text for kw in ["tempo city", "help away", "temper city", "temple city"]):
            target_song = "Self Aware by Temper City"
            execute_system_command("play_specific", target_song, volume_percent=extracted_vol)
            msg = f"Playing '{target_song}' on Spotify, Prem."
            if extracted_vol >= 0:
                msg += f" Sound set to {extracted_vol}%."
            log_conversation(role="assistant", message=msg)
            return {"reply": msg, "action": "play_specific"}

        # 6. EXPLICIT "PLAY [SONG]" SHORTCUT
        # FIX #2: Use regex extraction instead of substring .replace("play", "") to prevent mangling song titles
        play_match = re.search(r'\bplay\b\s+(.*)', lower_text)
        if play_match:
            raw_song = play_match.group(1)
            cleaned_song = re.sub(r'\s*on spotify\s*$', '', raw_song).strip()
            if cleaned_song and cleaned_song not in ["music", "spotify", "playlist", "hindi", "english", "volume", "sound", "it", "this", "next", "next song", "next track", "previous", "previous song", "previous track"]:
                execute_system_command("play_specific", cleaned_song, volume_percent=extracted_vol)
                msg = f"Opening Spotify and playing '{cleaned_song}', Prem."
                log_conversation(role="assistant", message=msg)
                return {"reply": msg, "action": "play_specific"}

    # Build dynamic prompt (Boss gets full permanent memory context; permitted guests get basic context)
    if is_boss:
        memory_str = get_memory_context_string()
        recent_history = get_recent_conversation(limit=4)
        history_str = "\n".join([f"{h['role'].upper()}: {h['message']}" for h in recent_history])
        
        full_system_prompt = (
            f"{_BOSS_BASE_PROMPT}\n\n"
            f"[PERMANENT MEMORY & USER PREFERENCES]\n{memory_str}\n\n"
            f"[RECENT CONVERSATION HISTORY]\n{history_str}"
        )
    elif guest_active:
        recent_history = get_recent_conversation(limit=4)
        history_str = "\n".join([f"{h['role'].upper()}: {h['message']}" for h in recent_history])
        full_system_prompt = (
            f"{_BOSS_BASE_PROMPT}\n\n"
            f"[NOTE: Permitted guest speaking — execute allowed media/app requests, but DO NOT reveal or save personal memories.]\n\n"
            f"[RECENT CONVERSATION HISTORY]\n{history_str}"
        )
    else:
        full_system_prompt = _GUEST_SYSTEM_PROMPT

    # ⚡ STEP 1: Try Groq LLM Fuzzy Intent & Phonetic Corrector (~150ms)
    groq_client = _get_groq_client()
    if groq_client:
        try:
            start_time = time.time()
            completion = groq_client.chat.completions.create(
                model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                messages=[
                    {"role": "system", "content": full_system_prompt},
                    {"role": "user", "content": f"User said: {text}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=400,
            )
            elapsed = (time.time() - start_time) * 1000
            raw = completion.choices[0].message.content or ""
            data = _extract_json(raw)

            reply = str(data.get("reply") or "").strip()
            action = str(data.get("action") or "none").strip().lower()
            target_app = str(data.get("target_app") or "").strip()
            
            try:
                vol_percent = int(data.get("volume_percent", -1))
            except (ValueError, TypeError):
                vol_percent = -1
            # FIX #1: extracted_vol is now defined unconditionally at the top
            if extracted_vol >= 0:
                vol_percent = extracted_vol

            if action not in KNOWN_ACTIONS:
                action = "none"

            if reply and (is_boss or guest_active):
                _handle_system_automation(action, target_app, volume_percent=vol_percent)

                rem_key = data.get("remember_key")
                rem_val = data.get("remember_value")
                if is_boss and (action == "remember" or rem_key) and rem_key and rem_val:
                    save_fact(key=str(rem_key), value=str(rem_val))

                print(f"[Brain/Groq Intent Corrector] Responded in {elapsed:.1f}ms ⚡ (Action: {action}, Target: '{target_app}', Vol: {vol_percent})")
                log_conversation(role="assistant", message=reply)
                return {"reply": reply, "action": action}
        except Exception as err:
            print(f"[Brain] Groq call failed ({err}), failing over to Gemini...")

    # 🧠 STEP 2: Gemini API Failover Pool
    gemini_client = _get_gemini_client()
    if gemini_client:
        models_to_try = [
            os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite-001"
        ]
        for model_name in models_to_try:
            try:
                response = gemini_client.models.generate_content(
                    model=model_name,
                    contents=[full_system_prompt, f"User said: {text}"],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.3,
                    ),
                )
                raw = (getattr(response, "text", "") or "").strip()
                data = _extract_json(raw)

                reply = str(data.get("reply") or "").strip()
                action = str(data.get("action") or "none").strip().lower()
                target_app = str(data.get("target_app") or "").strip()
                
                try:
                    vol_percent = int(data.get("volume_percent", -1))
                except (ValueError, TypeError):
                    vol_percent = -1
                if extracted_vol >= 0:
                    vol_percent = extracted_vol

                if action not in KNOWN_ACTIONS: action = "none"

                if reply and (is_boss or guest_active):
                    _handle_system_automation(action, target_app, volume_percent=vol_percent)
                    log_conversation(role="assistant", message=reply)
                    return {"reply": reply, "action": action}
            except Exception as err:
                print(f"[Brain] Gemini {model_name} failed: {err}")

    # Strict Fallback - Only trigger Spotify search if user explicitly said 'play [song]'
    fallback_play_match = re.search(r'\bplay\b\s+(.*)', lower_text)
    if authorized and fallback_play_match:
        fallback_song = re.sub(r'\s*on spotify\s*$', '', fallback_play_match.group(1)).strip()
        if fallback_song and fallback_song not in ["music", "spotify", "playlist", "it", "this"]:
            execute_system_command("play_specific", fallback_song, volume_percent=extracted_vol)
            msg = f"Opening Spotify and playing '{fallback_song}', Prem."
            log_conversation(role="assistant", message=msg)
            return {"reply": msg, "action": "play_specific"}

    fallback_reply = f"At your service, Prem. I heard: '{text}'. How can I assist you?"
    log_conversation(role="assistant", message=fallback_reply)
    return {"reply": fallback_reply, "action": "none"}
