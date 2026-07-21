"""FRIDAY System Automation Controller (macOS / PC).

Executes system-level commands requested by Boss:
- Spotify Advanced Media Automation (Play specific song, Play Hindi / English playlist, Volume Up/Down, Mute, Next/Prev, Repeat, Quit Spotify)
- Open Applications (Spotify, Brave, VS Code, Terminal, Finder, etc.)
- Control Web & Browser (YouTube, Google, GitHub, URL navigation in Brave)
"""
import os
import subprocess
import urllib.parse
import platform
import time

IS_MAC = platform.system() == "Darwin"


def open_app(app_name: str) -> bool:
    """Launch an application on macOS."""
    clean_name = app_name.strip()
    if IS_MAC:
        try:
            subprocess.Popen(["open", "-a", clean_name])
            return True
        except Exception as err:
            print(f"[Automation] Failed to open app {clean_name}: {err}")
            return False
    return False


def close_app(app_name: str) -> bool:
    """Quit an application gracefully using AppleScript (Cmd + Q equivalent)."""
    clean_name = app_name.strip()
    if IS_MAC:
        try:
            script = f'tell application "{clean_name}" to quit'
            subprocess.Popen(["osascript", "-e", script])
            return True
        except Exception as err:
            print(f"[Automation] Failed to quit app {clean_name}: {err}")
            return False
    return False


def search_and_play_spotify(song_or_playlist: str) -> bool:
    """Search for a specific song or playlist on Spotify and immediately play it."""
    if not IS_MAC or not song_or_playlist:
        return False
    try:
        q_clean = song_or_playlist.strip()
        
        # 1. Direct AppleScript Spotify track URI play attempt
        direct_script = f'''
        tell application "Spotify"
            activate
            play track "spotify:search:{q_clean}"
        end tell
        '''
        subprocess.Popen(["osascript", "-e", direct_script])

        # 2. Automated UI keystroke fallback (Cmd+K search -> type song -> Press Enter -> Play)
        keystroke_script = f'''
        delay 0.8
        tell application "Spotify" to activate
        tell application "System Events"
            tell process "Spotify"
                keystroke "k" using {{command down}}
                delay 0.4
                keystroke "{q_clean}"
                delay 0.6
                key code 36
                delay 0.4
                key code 36
            end tell
        end tell
        '''
        subprocess.Popen(["osascript", "-e", keystroke_script])
        return True
    except Exception as err:
        print(f"[Automation] Spotify search play error: {err}")
        return False


def control_spotify(command: str, query: str = "") -> bool:
    """Control Spotify playback, volume, playlists, and repeat mode via macOS AppleScript."""
    if not IS_MAC:
        return False
    
    cmd = command.lower().strip()
    try:
        open_app("Spotify")

        if cmd == "play":
            script = 'tell application "Spotify" to play'
        elif cmd == "pause" or cmd == "stop":
            script = 'tell application "Spotify" to pause'
        elif cmd == "play_pause" or cmd == "toggle":
            script = 'tell application "Spotify" to playpause'
        elif cmd == "next":
            script = 'tell application "Spotify" to next track'
        elif cmd == "previous":
            script = 'tell application "Spotify" to previous track'
        elif cmd == "volume_up":
            script = 'tell application "Spotify" to set sound volume to (sound volume + 20)'
        elif cmd == "volume_down":
            script = 'tell application "Spotify" to set sound volume to (sound volume - 20)'
        elif cmd == "mute":
            script = 'tell application "Spotify" to set sound volume to 0'
        elif cmd == "repeat":
            script = 'tell application "Spotify" to set repeating to true'
        elif cmd == "shuffle":
            script = 'tell application "Spotify" to set shuffling to true'
        elif cmd == "play_hindi_playlist":
            search_and_play_spotify("Only for me")
            return True
        elif cmd == "play_english_playlist":
            search_and_play_spotify("Losing my self")
            return True
        elif cmd == "play_specific":
            search_and_play_spotify(query)
            return True
        else:
            script = 'tell application "Spotify" to play'

        subprocess.Popen(["osascript", "-e", script])
        return True
    except Exception as err:
        print(f"[Automation] Spotify control error: {err}")
        return False


def open_url_in_brave(url: str) -> bool:
    """Open a URL in Brave browser (or default browser)."""
    target_url = url if url.startswith("http") else f"https://{url}"
    if IS_MAC:
        try:
            subprocess.Popen(["open", "-a", "Brave Browser", target_url])
            return True
        except Exception:
            subprocess.Popen(["open", target_url])
            return True
    return False


def open_youtube_search(query: str = "") -> bool:
    """Open YouTube or search YouTube in Brave."""
    if not query or query.lower().strip() in ["youtube", "open youtube"]:
        url = "https://www.youtube.com"
    else:
        q_encoded = urllib.parse.quote(query.strip())
        url = f"https://www.youtube.com/results?search_query={q_encoded}"
    return open_url_in_brave(url)


def open_google_search(query: str) -> bool:
    """Search Google in Brave."""
    q_encoded = urllib.parse.quote(query.strip())
    url = f"https://www.google.com/search?q={q_encoded}"
    return open_url_in_brave(url)


def execute_system_command(action_type: str, target: str = "") -> str:
    """Router for executing OS automation requests."""
    action = action_type.lower().strip()
    target_clean = target.strip()

    print(f"[Automation] Executing action='{action}' target='{target_clean}'")

    if action == "open_spotify":
        open_app("Spotify")
        return "Opening Spotify now, Boss."

    elif action == "close_spotify":
        close_app("Spotify")
        return "Closing Spotify, Boss."

    elif action == "play_hindi_playlist":
        control_spotify("play_hindi_playlist")
        return "Playing your Hindi playlist 'Only for me', Boss."

    elif action == "play_english_playlist":
        control_spotify("play_english_playlist")
        return "Playing your English playlist 'Losing my self', Boss."

    elif action == "play_specific":
        control_spotify("play_specific", target_clean)
        return f"Playing '{target_clean}' on Spotify, Boss."

    elif action == "play_music" or action == "play_spotify":
        if target_clean:
            control_spotify("play_specific", target_clean)
            return f"Playing '{target_clean}' on Spotify, Boss."
        control_spotify("play")
        return "Playing Spotify music now, Boss."

    elif action == "pause_music" or action == "pause_spotify":
        control_spotify("pause")
        return "Pausing Spotify music, Boss."

    elif action == "toggle_music":
        control_spotify("play_pause")
        return "Toggling Spotify playback, Boss."

    elif action == "next_track":
        control_spotify("next")
        return "Skipping to the next track, Boss."

    elif action == "previous_track":
        control_spotify("previous")
        return "Playing previous track, Boss."

    elif action == "volume_up":
        control_spotify("volume_up")
        return "Increasing Spotify volume, Boss."

    elif action == "volume_down":
        control_spotify("volume_down")
        return "Decreasing Spotify volume, Boss."

    elif action == "mute":
        control_spotify("mute")
        return "Muting Spotify, Boss."

    elif action == "repeat":
        control_spotify("repeat")
        return "Setting Spotify to repeat mode, Boss."

    elif action == "shuffle":
        control_spotify("shuffle")
        return "Setting Spotify to shuffle mode, Boss."

    elif action == "open_brave":
        if target_clean:
            open_url_in_brave(target_clean)
            return f"Opening {target_clean} in Brave, Boss."
        open_app("Brave Browser")
        return "Opening Brave browser, Boss."

    elif action == "open_youtube":
        open_youtube_search(target_clean)
        return f"Opening YouTube search for '{target_clean}', Boss." if target_clean else "Opening YouTube in Brave, Boss."

    elif action == "open_app":
        open_app(target_clean)
        return f"Opening {target_clean}, Boss."

    elif action == "close_app":
        close_app(target_clean)
        return f"Closing {target_clean}, Boss."

    elif action == "search_web":
        open_google_search(target_clean)
        return f"Searching '{target_clean}' in Brave, Boss."

    return ""
