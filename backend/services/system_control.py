"""FRIDAY System Automation Controller (macOS / PC).

Executes system-level commands requested by Boss:
- Spotify Advanced Media Automation (Play specific song, Set Volume %, Play Hindi / English playlist, Volume Up/Down, Mute, Next/Prev, Repeat, Quit Spotify)
- Open Applications (Spotify, Brave, VS Code, Terminal, Finder, etc.)
- Control Web & Browser (YouTube, Google, GitHub, URL navigation in Brave)
"""
import os
import subprocess
import urllib.parse
import platform
import time

IS_MAC = platform.system() == "Darwin"


def is_spotify_running() -> bool:
    """Check if Spotify is currently running via AppleScript."""
    if not IS_MAC:
        return False
    try:
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to (name of processes) contains "Spotify"'],
            capture_output=True, text=True, timeout=2
        )
        return result.stdout.strip().lower() == "true"
    except Exception:
        return False


def system_set_volume(percent: int) -> bool:
    """Set macOS system output volume (0-100)."""
    if not IS_MAC:
        return False
    clamped = max(0, min(100, percent))
    try:
        subprocess.Popen(["osascript", "-e", f"set volume output volume {clamped}"])
        return True
    except Exception as err:
        print(f"[Automation] System volume set error: {err}")
        return False


def system_volume_up() -> bool:
    """Raise macOS system output volume by 10 points."""
    if not IS_MAC:
        return False
    try:
        result = subprocess.run(
            ["osascript", "-e", "output volume of (get volume settings)"],
            capture_output=True, text=True, timeout=2
        )
        current = int(result.stdout.strip())
        system_set_volume(min(100, current + 10))
        return True
    except Exception as err:
        print(f"[Automation] System volume up error: {err}")
        return False


def system_volume_down() -> bool:
    """Lower macOS system output volume by 10 points."""
    if not IS_MAC:
        return False
    try:
        result = subprocess.run(
            ["osascript", "-e", "output volume of (get volume settings)"],
            capture_output=True, text=True, timeout=2
        )
        current = int(result.stdout.strip())
        system_set_volume(max(0, current - 10))
        return True
    except Exception as err:
        print(f"[Automation] System volume down error: {err}")
        return False


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

# Boss's actual Spotify playlists — direct URIs for instant reliable playback
PLAYLIST_HINDI   = "spotify:playlist:4SuEAsJ6ulS62RYJk88Sap"
PLAYLIST_ENGLISH = "spotify:playlist:2CCKzQqgsc50gtJeYDonJh"


def play_spotify_uri(uri: str) -> bool:
    """Play a Spotify URI (track / playlist / album) directly via AppleScript — no search needed."""
    if not IS_MAC or not uri:
        return False
    try:
        script = f'''
        tell application "Spotify"
            activate
            play track "{uri}"
        end tell
        '''
        subprocess.Popen(["osascript", "-e", script])
        return True
    except Exception as err:
        print(f"[Automation] Spotify URI play error: {err}")
        return False



def control_spotify(command: str, query: str = "", volume_percent: int = -1) -> bool:
    """Control Spotify playback, volume %, playlists, and repeat mode via macOS AppleScript."""
    if not IS_MAC:
        return False
    cmd = command.lower().strip()
    try:
        if cmd == "set_volume":
            if volume_percent >= 0:
                vol_clamped = max(0, min(100, volume_percent))
                script = f'''
                tell application "Spotify"
                    activate
                    set sound volume to {vol_clamped}
                end tell'''
                subprocess.Popen(["osascript", "-e", script])
            return True

        if cmd in ("play_hindi_playlist", "play_english_playlist", "play_specific"):
            # These use their own activate logic inside search_and_play_spotify
            if volume_percent >= 0:
                vol_clamped = max(0, min(100, volume_percent))
                vol_script = f'tell application "Spotify" to set sound volume to {vol_clamped}'
                subprocess.Popen(["osascript", "-e", vol_script])
            if cmd == "play_hindi_playlist":
                play_spotify_uri(PLAYLIST_HINDI)
            elif cmd == "play_english_playlist":
                play_spotify_uri(PLAYLIST_ENGLISH)
            else:
                search_and_play_spotify(query)
            return True

        # Map command → AppleScript action string
        action_map = {
            "play":       "play",
            "resume":     "play",
            "pause":      "pause",
            "stop":       "pause",
            "play_pause": "playpause",
            "toggle":     "playpause",
            "next":       "next track",
            "previous":   "previous track",
            "volume_up":  f"set sound volume to (sound volume + 20)",
            "volume_down":f"set sound volume to (sound volume - 20)",
            "mute":       "set sound volume to 0",
            "repeat":     "set repeating to true",
            "shuffle":    "set shuffling to true",
        }

        spotify_action = action_map.get(cmd, "play")

        # Build single atomic AppleScript — activate + optional volume + command
        vol_line = ""
        if volume_percent >= 0:
            vol_clamped = max(0, min(100, volume_percent))
            vol_line = f"\n    set sound volume to {vol_clamped}"

        script = f'''
        tell application "Spotify"
            activate{vol_line}
            {spotify_action}
        end tell'''

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


def execute_system_command(action_type: str, target: str = "", volume_percent: int = -1) -> str:
    """Router for executing OS automation requests."""
    action = action_type.lower().strip()
    target_clean = target.strip()

    print(f"[Automation] Executing action='{action}' target='{target_clean}' vol={volume_percent}")

    spotify_running = is_spotify_running()
    print(f"[Automation] Spotify running: {spotify_running}")

    if action == "open_spotify":
        open_app("Spotify")
        return "Opening Spotify now, Prem."

    elif action == "close_spotify":
        close_app("Spotify")
        return "Closing Spotify, Prem."

    elif action == "play_hindi_playlist":
        control_spotify("play_hindi_playlist", volume_percent=volume_percent)
        return "Playing your Hindi playlist, Prem."

    elif action == "play_english_playlist":
        control_spotify("play_english_playlist", volume_percent=volume_percent)
        return "Playing your English playlist, Prem."

    elif action == "play_specific":
        control_spotify("play_specific", target_clean, volume_percent=volume_percent)
        msg = f"Playing '{target_clean}' on Spotify, Prem."
        if volume_percent >= 0:
            msg += f" Sound set to {volume_percent}%."
        return msg

    elif action == "play_music" or action == "play_spotify":
        if target_clean:
            control_spotify("play_specific", target_clean, volume_percent=volume_percent)
            return f"Playing '{target_clean}' on Spotify, Prem."
        control_spotify("play", volume_percent=volume_percent)
        return "Playing Spotify music now, Prem."

    elif action == "pause_music" or action == "pause_spotify":
        control_spotify("pause")
        return "Pausing Spotify music, Prem."

    elif action == "toggle_music":
        control_spotify("play_pause")
        return "Toggling Spotify playback, Prem."

    elif action == "next_track":
        control_spotify("next")
        return "Skipping to the next track, Prem."

    elif action == "previous_track":
        control_spotify("previous")
        return "Playing previous track, Prem."

    elif action == "volume_up":
        if spotify_running:
            control_spotify("volume_up")
            return "Increasing Spotify volume, Prem."
        else:
            system_volume_up()
            return "Increasing system volume, Prem."

    elif action == "volume_down":
        if spotify_running:
            control_spotify("volume_down")
            return "Decreasing Spotify volume, Prem."
        else:
            system_volume_down()
            return "Decreasing system volume, Prem."

    elif action == "set_volume":
        if spotify_running:
            control_spotify("set_volume", volume_percent=volume_percent)
            return f"Setting Spotify volume to {volume_percent}%, Prem."
        else:
            system_set_volume(volume_percent)
            return f"Setting system volume to {volume_percent}%, Prem."

    elif action == "mute":
        if spotify_running:
            control_spotify("mute")
            return "Muting Spotify, Prem."
        else:
            subprocess.Popen(["osascript", "-e", "set volume output muted true"])
            return "Muting system audio, Prem."

    elif action == "repeat":
        control_spotify("repeat")
        return "Setting Spotify to repeat mode, Prem."

    elif action == "shuffle":
        control_spotify("shuffle")
        return "Setting Spotify to shuffle mode, Prem."

    elif action == "open_brave":
        if target_clean:
            open_url_in_brave(target_clean)
            return f"Opening {target_clean} in Brave, Prem."
        open_app("Brave Browser")
        return "Opening Brave browser, Prem."

    elif action == "open_youtube":
        open_youtube_search(target_clean)
        return f"Opening YouTube search for '{target_clean}', Prem." if target_clean else "Opening YouTube in Brave, Prem."

    elif action == "open_app":
        open_app(target_clean)
        return f"Opening {target_clean}, Prem."

    elif action == "close_app":
        close_app(target_clean)
        return f"Closing {target_clean}, Prem."

    elif action == "search_web":
        open_google_search(target_clean)
        return f"Searching '{target_clean}' in Brave, Prem."

    return ""
