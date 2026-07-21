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
    "You address the user as 'Boss' or 'Prathvi'. Keep spoken replies concise (1-2 sentences), confident, and witty. "
    "CRITICAL SPEECH-TO-TEXT FUZZY RECOVERY RULES: "
    "Browser STT often mishears words phonetically when the user speaks! "
    "Examples of STT misinterpretations: "
    "- 'help away by Tempo city' OR 'temple city' OR 'temple city on my spotify' -> 'Self Aware by Temple City' "
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
    "You are F.R.I.D.A.Y., Tony Stark's AI assistant. A guest (not your Boss Prathvi) is talking to you, "
    "and access permission has NOT been granted by your Boss yet. "
    "Be hilariously sarcastic, polite yet firm, and inform them that only your Boss Prathvi Sahu can give them system permission. "
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

    # Log user turn to memory history
    log_conversation(role="user" if is_boss else "guest", message=text)

    # Ignore isolated single non-command filler words like "please"
    if lower_text in ["please", "pls", "thank you", "thanks"]:
        return {"reply": "", "action": "none"}

    # SECURITY & PERMISSION MANAGEMENT (Boss only)
    if is_boss:
        if any(kw in lower_text for kw in ["allow guest", "grant guest", "let them speak", "give permission"]):
            set_guest_permission(True)
            reply_msg = "Guest access granted, Boss. I'll answer their queries now."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "allow_guest"}

        if any(kw in lower_text for kw in ["revoke guest", "stop guest", "lock guest"]):
            set_guest_permission(False)
            reply_msg = "Guest access revoked, Boss. Back to Boss-only mode."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "revoke_guest"}

        # Auto-correct name spelling in incoming transcript before memory or processing
        if any(kw in lower_text for kw in ["prithvi", "p r i t h v i", "r a not i", "spelling is"]):
            save_fact("boss_name", "Prathvi Sahu", "identity")
            save_fact("boss_name_spelling", "P-R-A-T-H-V-I S-A-H-U", "identity")

    # GATED MEDIA SHORTCUTS (Checked BEFORE LLM call)
    if authorized:
        # 1. VOLUME DOWN / DECREASE MUSIC SHORTCUT
        if any(kw in lower_text for kw in ["decrease volume", "volume down", "decrease music", "lower music", "lower volume", "quieter", "turn down", "decrease the music"]):
            execute_system_command("volume_down")
            reply_msg = "Decreasing volume, Boss."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "volume_down"}

        # 2. VOLUME UP / INCREASE MUSIC SHORTCUT
        if any(kw in lower_text for kw in ["increase volume", "volume up", "increase music", "raise music", "raise volume", "louder", "turn up"]):
            execute_system_command("volume_up")
            reply_msg = "Increasing volume, Boss."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "volume_up"}

        # 3. UNPAUSE / RESUME SHORTCUT
        if re.search(r'\b(?:unpause|resume)\b', lower_text):
            execute_system_command("play_music")
            reply_msg = "Resuming Spotify music, Boss."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "play_music"}

        # 4. PAUSE / STOP MUSIC SHORTCUT
        if re.search(r'\b(?:pause|stop music|hold on)\b', lower_text) or lower_text == "stop":
            execute_system_command("pause_music")
            reply_msg = "Pausing Spotify music, Boss."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "pause_music"}

        # 5. PRE-EXTRACT VOLUME % PATTERNS
        vol_match = re.search(r'(?:sound|volume)\s*(?:at|to|is)?\s*(\d{1,3})%?', lower_text)
        extracted_vol = int(vol_match.group(1)) if vol_match else -1

        # 6. PHONETIC SONG SHORTCUT
        if any(kw in lower_text for kw in ["tempo city", "help away", "temple city"]):
            target_song = "Self Aware by Temple City"
            execute_system_command("play_specific", target_song, volume_percent=extracted_vol)
            msg = f"Playing '{target_song}' on Spotify, Boss."
            if extracted_vol >= 0:
                msg += f" Sound set to {extracted_vol}%."
            log_conversation(role="assistant", message=msg)
            return {"reply": msg, "action": "play_specific"}

        # 7. EXPLICIT "PLAY [SONG]" SHORTCUT (Only if phrase contains explicit song/artist, NOT volume/playlist/decrease keywords)
        if re.search(r'\bplay\b', lower_text) and not any(kw in lower_text for kw in ["decrease", "lower", "quieter", "volume"]):
            cleaned_song = (
                lower_text.replace("open spotify and play", "")
                .replace("open spotify and", "")
                .replace("play song", "")
                .replace("play track", "")
                .replace("search song", "")
                .replace("play", "")
                .replace("on spotify", "")
                .strip()
            )
            if cleaned_song and cleaned_song not in ["music", "spotify", "playlist", "hindi", "english", "volume", "sound"]:
                execute_system_command("play_specific", cleaned_song, volume_percent=extracted_vol)
                msg = f"Opening Spotify and playing '{cleaned_song}', Boss."
                log_conversation(role="assistant", message=msg)
                return {"reply": msg, "action": "play_specific"}

    # Build dynamic prompt with stored memory context
    if is_boss or guest_active:
        memory_str = get_memory_context_string()
        recent_history = get_recent_conversation(limit=4)
        history_str = "\n".join([f"{h['role'].upper()}: {h['message']}" for h in recent_history])
        
        full_system_prompt = (
            f"{_BOSS_BASE_PROMPT}\n\n"
            f"[PERMANENT MEMORY & USER PREFERENCES]\n{memory_str}\n\n"
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
            if extracted_vol >= 0 if 'extracted_vol' in locals() else False:
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
                if extracted_vol >= 0 if 'extracted_vol' in locals() else False:
                    vol_percent = extracted_vol

                if action not in KNOWN_ACTIONS: action = "none"

                if reply and (is_boss or guest_active):
                    _handle_system_automation(action, target_app, volume_percent=vol_percent)
                    log_conversation(role="assistant", message=reply)
                    return {"reply": reply, "action": action}
            except Exception as err:
                print(f"[Brain] Gemini {model_name} failed: {err}")

    # Strict Fallback - Only trigger Spotify search if user explicitly used a song play request
    song_explicit_keywords = ["play song", "play track", "search song", "play artist"]
    if authorized and any(kw in lower_text for kw in song_explicit_keywords) and len(text.split()) <= 4:
        execute_system_command("play_specific", text, volume_percent=extracted_vol if 'extracted_vol' in locals() else -1)
        msg = f"Opening Spotify and playing '{text}', Boss."
        log_conversation(role="assistant", message=msg)
        return {"reply": msg, "action": "play_specific"}

    fallback_reply = f"At your service, Boss. I heard: '{text}'. How can I assist you?"
    log_conversation(role="assistant", message=fallback_reply)
    return {"reply": fallback_reply, "action": "none"}
