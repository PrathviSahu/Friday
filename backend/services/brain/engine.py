"""services/brain/engine.py — Core cognitive decision engine (Fast-path + Groq + Gemini failover)."""

import os
import re
import time
from google.genai import types

from services.voice_auth import is_guest_permitted
from services.memory import save_fact, log_conversation
from services.system_control import execute_system_command
from services.learning_engine import (
    detect_and_log_correction,
    extract_job_profile_from_text,
    compute_response_brevity,
)
from services.brain.constants import KNOWN_ACTIONS
from services.brain.clients import _get_groq_client, _get_gemini_client, _extract_json
from services.brain.prompt_builder import build_system_prompt
from services.brain.handlers.security_handler import handle_security_and_permissions
from services.brain.handlers import dispatch_fast_path_handlers

_last_action_context: dict = {"query": "", "target": ""}


def _handle_system_automation(action: str, target: str, volume_percent: int = -1) -> str:
    """Helper to dispatch system commands to macOS execution engine."""
    excluded = {
        "dashboard", "trading", "engineering", "vscode", "browser",
        "lock", "allow_guest", "revoke_guest", "remember", "none"
    }
    if action in KNOWN_ACTIONS and action not in excluded:
        return execute_system_command(action, target, volume_percent=volume_percent)
    return ""


def respond(transcript: str, is_boss: bool = True, silence_tts: bool = False) -> dict:
    """Return {'reply': str, 'action': str} for a user utterance using Groq Fuzzy Intent Corrector LLM + Gemini failover."""
    text = (transcript or "").strip()
    if not text:
        return {"reply": "", "action": "none"}

    # Apply permanent personal speech corrections
    try:
        from speech.personal_vocabulary import PersonalVocabularyEngine
        corrected = PersonalVocabularyEngine().apply_corrections(text)
        if corrected:
            text = corrected
    except Exception:
        pass

    lower_text = text.lower()
    guest_active = is_guest_permitted()
    authorized = is_boss or guest_active

    # Extract volume percentage if mentioned
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

    if is_boss:
        detect_and_log_correction(text, _last_action_context)
        extract_job_profile_from_text(text)

    # ⚡ Phase 2.4 — Voice Macro fast path (0ms)
    if authorized:
        try:
            from services import macros as _macros
            macro_result = _macros.match_and_maybe_run(text)
            if macro_result is not None:
                return macro_result
        except Exception:
            pass

    # Dynamic brevity calculation
    brevity_mode = compute_response_brevity(text)
    try:
        from services import context_engine
        brevity_mode = context_engine.cap_brevity(brevity_mode)
    except Exception:
        pass

    # Ignore isolated single non-command filler words
    if lower_text in ["please", "pls", "thank you", "thanks"]:
        return {"reply": "", "action": "none"}

    # 🔐 Security & Permission Handler (Prem only)
    sec_res = handle_security_and_permissions(lower_text, is_boss)
    if sec_res:
        return sec_res

    # ⚡ Deterministic Fast-Path Handlers (<15ms)
    if authorized:
        fast_res = dispatch_fast_path_handlers(
            lower_text=lower_text,
            is_boss=is_boss,
            extracted_vol=extracted_vol,
            silence_tts=silence_tts,
            raw_text=text,
            last_action_context=_last_action_context
        )
        if fast_res:
            return fast_res

    # Build dynamic contextual system prompt
    full_system_prompt = build_system_prompt(text, is_boss, guest_active, brevity_mode)

    # ⚡ STEP 1: Try Groq LLM Fuzzy Intent & Phonetic Corrector (~150ms)
    groq_client = _get_groq_client()
    if groq_client:
        try:
            start_time = time.time()
            from services.metrics import timed as _timed
            with _timed("llm", meta="groq-v1"):
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
                return {"reply": reply, "action": action, "silence_tts": silence_tts}
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

                if action not in KNOWN_ACTIONS:
                    action = "none"

                if reply and (is_boss or guest_active):
                    _handle_system_automation(action, target_app, volume_percent=vol_percent)
                    log_conversation(role="assistant", message=reply)
                    return {"reply": reply, "action": action, "silence_tts": silence_tts}
            except Exception as err:
                print(f"[Brain] Gemini {model_name} failed: {err}")

    # Strict Fallback - Only trigger Spotify search if user explicitly said 'play [song]'
    fallback_play_match = re.search(r'\bplay\b\s+(.*)', lower_text)
    if authorized and fallback_play_match:
        fallback_song = re.sub(r'\s*on spotify\s*$', '', fallback_play_match.group(1)).strip()
        if fallback_song and fallback_song not in ["music", "spotify", "playlist", "it", "this"]:
            execute_system_command("play_specific", fallback_song, volume_percent=extracted_vol)
            log_conversation(role="assistant", message="ok")
            return {"reply": "", "action": "play_specific", "silence_tts": True}

    fallback_reply = f"At your service, Prem. I heard: '{text}'. How can I assist you?"
    log_conversation(role="assistant", message=fallback_reply)
    return {"reply": fallback_reply, "action": "none", "silence_tts": silence_tts}
