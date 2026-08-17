"""services/brain/handlers/media_handler.py — Spotify playback, volume, playlists, track controls & song aliases."""

import re
from typing import Optional
from services.memory import log_conversation
from services.system_control import (
    execute_system_command,
    get_spotify_current_track,
    add_current_track_to_playlist,
    close_app,
    is_spotify_running,
    wait_until_spotify_running
)
from services.learning_engine import log_user_action


def clean_song_query(query: str) -> str:
    """Strips wake words, filler phrases, and trailing app names from song search queries."""
    clean = query.strip()
    clean = re.sub(r'(?i)\b(friday|hey friday|ok friday|okay friday|please|could you|can you|play me|play song|gaana|chalao|bajao|song|track)\b', '', clean)
    clean = re.sub(r'(?i)\b(on|in|by|via)\s+spotify\b', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def handle_media(lower_text: str, is_boss: bool, extracted_vol: int, silence_tts: bool, last_action_context: dict) -> Optional[dict]:
    """Handles Spotify media control, track cycling, playlist selection, volume levels, and aliases."""
    # Ensure Spotify is running first if this is a playback or music control intent
    if re.search(r'\b(?:play|unpause|resume|next|previous|skip|spotify|gaana|music)\b', lower_text) and not re.search(r'\b(?:close|quit|band)\b', lower_text):
        if not is_spotify_running():
            print("[Media Handler] Spotify not running — opening Spotify in background first...")
            wait_until_spotify_running(timeout=6.0)
    # Close Spotify
    if re.search(r'\b(?:close|quit|stop|exit|band\s+karo)\s+(?:the\s+)?spotify\b|\bspotify\s+(?:close|quit|band\s+karo)\b', lower_text):
        close_app("Spotify")
        reply_msg = "Closing Spotify."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "close_spotify", "silence_tts": silence_tts}

    # Song alias memory
    alias_match = re.search(r'\b(?:whenever i say|remember that|set alias|remember|my)\s+(.+?)\s+(?:i mean|means|is)\s+(.+)', lower_text)
    if alias_match and ("song" in lower_text or "music" in lower_text or "playlist" in lower_text or "track" in lower_text):
        alias = alias_match.group(1).replace("remember", "").replace("that", "").strip()
        song = alias_match.group(2).strip()
        try:
            from database.repositories.song_memory_repo import SongMemoryRepository
            SongMemoryRepository().save_alias(alias=alias, song_name=song)
            reply_msg = f"Understood, Prem. Saved '{alias}' as '{song}' in song memory."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "none"}
        except Exception as e:
            print(f"[Brain] Song alias memory error: {e}")

    # Set volume percentage
    if extracted_vol >= 0 and not re.search(r'\bplay\b', lower_text):
        result = execute_system_command("set_volume", "", volume_percent=extracted_vol)
        reply_msg = result or f"Setting volume to {extracted_vol}%, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "set_volume", "silence_tts": silence_tts}

    # Volume down
    if re.search(r'(?:turn|lower|decrease|bring|take)\s+(?:the\s+)?(?:volume|music|sound|it)\s*(?:down)?|volume\s*down|quieter|\b(?:awaaz\s+kam|volume\s+kam|dheere\s+karo|dheere)\b', lower_text):
        result = execute_system_command("volume_down", "")
        reply_msg = result or "Decreasing volume, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "volume_down", "silence_tts": silence_tts}

    # Volume up
    if re.search(r'(?:turn|raise|increase|bring|take)\s+(?:the\s+)?(?:volume|music|sound|it)\s*(?:up)?|volume\s*up|louder|\b(?:awaaz\s+badhao|volume\s+badhao|tez\s+karo|unche\s+karo)\b', lower_text):
        result = execute_system_command("volume_up", "")
        reply_msg = result or "Increasing volume, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "volume_up", "silence_tts": silence_tts}

    # Next / Previous Track
    if re.search(r'\b(?:next|skip|play next|next song|next track)\b|\b(?:agla\s+gaana|agla\s+song|agla)\b', lower_text):
        execute_system_command("next_track", "")
        reply_msg = "Skipping to the next track, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "next_track", "silence_tts": silence_tts}

    if re.search(r'\b(?:previous|prev|previous song|previous track|play previous|go back)\b|\b(?:pichhla\s+gaana|purana\s+gaana|pichhla)\b', lower_text):
        execute_system_command("previous_track", "")
        reply_msg = "Playing the previous track, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "previous_track", "silence_tts": silence_tts}

    # Unpause / Resume
    if re.search(r'^(?:unpause|resume|play\s+(?:the\s+)?(?:song|music|track|spotify)|start\s+(?:playing|music|song)|play|gaana\s+chalao|music\s+chalao|gaana\s+bajao|shuru\s+karo)$', lower_text.strip()):
        execute_system_command("play_music", "", volume_percent=extracted_vol)
        reply_msg = "Resuming Spotify music, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "play_music", "silence_tts": silence_tts}

    # Pause / Stop
    if re.search(r'\b(?:pause|pause music|stop music|stop playing|stop the song|stop the music|hold on)\b|\b(?:band\s+karo|gaana\s+roko|roko|ruk\s+jao|gaana\s+band)\b', lower_text) or lower_text in ["stop", "band"]:
        execute_system_command("pause_music", "")
        reply_msg = "Pausing Spotify music, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "pause_music", "silence_tts": silence_tts}

    # Add track to playlist
    if re.search(r'\b(?:add|at|save)\s+(?:this|current)?\s*(?:song|track)?\s*(?:to|in)?\s*(?:my)?\s*(?:english|hindi|krishna|favorite|fav)?\s*(?:playlist)?\b|\b(?:is\s+gaane\s+ko|playlist\s+mein\s+daalo)\b', lower_text):
        track_info = get_spotify_current_track()
        if track_info.get("title"):
            add_current_track_to_playlist()
            reply_msg = f"Prem, adding '{track_info.get('title')}' to your playlist."
        else:
            reply_msg = "No song is currently playing on Spotify to add, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "none"}

    # What's playing
    if re.search(r'\b(?:what\s+song|what\s+is\s+playing|whats\s+playing|which\s+song|kaun\s+sa\s+gaana|kis\s+gaane)\b', lower_text):
        track_info = get_spotify_current_track()
        if track_info.get("playing") or track_info.get("title"):
            t = track_info.get("title", "Unknown")
            a = track_info.get("artist", "Unknown artist")
            reply_msg = f"Prem, currently playing '{t}' by {a} on Spotify." if re.search(r'\b(?:what|which|song)\b', lower_text) else f"Prem, abhi '{t}' by {a} chal raha hai."
        else:
            reply_msg = "Nothing is currently playing on Spotify, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "none"}

    # Playlists
    if re.search(r'\b(?:hindi|meri|apni|bollywood|desi)\b.*\b(?:playlist|songs|music|gaane)\b|\b(?:playlist|songs|music|gaane)\b.*\b(?:hindi|bollywood|desi)\b', lower_text):
        result = execute_system_command("play_hindi_playlist", "", volume_percent=extracted_vol)
        reply_msg = result or "Playing your Hindi playlist, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "play_hindi_playlist", "silence_tts": True}

    if re.search(r'\b(?:english|english playlist|angrezi)\b.*\b(?:playlist|songs|music)\b|\b(?:playlist|songs|music)\b.*\b(?:english|angrezi)\b', lower_text):
        result = execute_system_command("play_english_playlist", "", volume_percent=extracted_vol)
        reply_msg = result or "Playing your English playlist, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "play_english_playlist", "silence_tts": True}

    if re.search(r'\b(?:krishna|radha|radha krishna|radhe krishna|bhajan|devotional)\b', lower_text):
        result = execute_system_command("play_krishna_playlist", "", volume_percent=extracted_vol)
        reply_msg = result or "Playing your Krishna playlist, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "play_krishna_playlist", "silence_tts": True}

    # Shuffle
    if re.search(r'\b(?:shuffle|shuffel)\b', lower_text):
        execute_system_command("shuffle", "")
        reply_msg = "Enabling Spotify shuffle mode, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "shuffle", "silence_tts": True}

    # Phonetic song shortcut
    if any(kw in lower_text for kw in ["tempo city", "help away", "temper city", "temple city"]):
        target_song = "Self Aware by Temper City"
        execute_system_command("play_specific", target_song, volume_percent=extracted_vol)
        msg = f"Playing '{target_song}' on Spotify, Prem."
        if extracted_vol >= 0:
            msg += f" Sound set to {extracted_vol}%."
        log_conversation(role="assistant", message=msg)
        last_action_context.update({"query": lower_text, "target": target_song})
        log_user_action("play_music")
        return {"reply": msg, "action": "play_specific", "silence_tts": True}

    # Explicit "Play [Song]"
    play_match = re.search(r'\bplay\b\s+(.*)', lower_text)
    if play_match:
        raw_song = play_match.group(1)
        cleaned_song = clean_song_query(raw_song)
        if cleaned_song and cleaned_song.lower() not in [
            "music", "the music", "some music", "my music", "spotify", "playlist",
            "hindi", "english", "volume", "sound", "it", "this", "next", "next song",
            "next track", "previous", "previous song", "previous track"
        ]:
            execute_system_command("play_specific", cleaned_song, volume_percent=extracted_vol)
            log_conversation(role="assistant", message="ok")
            last_action_context.update({"query": lower_text, "target": cleaned_song})
            log_user_action("play_music")
            return {"reply": "", "action": "play_specific", "silence_tts": True}

    return None
