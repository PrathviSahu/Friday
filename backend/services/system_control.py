"""FRIDAY System Automation Controller (macOS / PC).

Executes system-level commands requested by Boss:
- Spotify Advanced Media Automation (Play specific song, Set Volume %, Play Hindi / English playlist, Volume Up/Down, Mute, Next/Prev, Repeat, Quit Spotify)
- Open Applications (Spotify, Brave, VS Code, Terminal, Finder, etc.)
- Control Web & Browser (YouTube, Google, GitHub, URL navigation in Brave)
"""
import os
import re
import difflib
import base64
import subprocess
import urllib.parse
import urllib.request
import platform
import time
import json
from pathlib import Path
from datetime import datetime

IS_MAC = platform.system() == "Darwin"

# ── Spotify Web API token cache ───────────────────────────────────────────────
_spotify_token_cache: dict = {"access_token": "", "expires_at": 0.0}
_spotify_cc_cache: dict = {"access_token": "", "expires_at": 0.0}


def _get_spotify_web_anon_token() -> str:
    """Get a temporary public Spotify search token directly from Spotify Web Player API.

    Requires 0 configuration, 0 env variables, 0 setup.
    """
    try:
        url = "https://open.spotify.com/get_access_token?reason=transport&productType=web_player"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            token = data.get("accessToken", "")
            if token:
                print("[Spotify Anon Token] ✅ Successfully obtained Spotify Web Token!")
                return token
    except Exception as e:
        print(f"[Spotify Anon Token] Warning: {e}")
    return ""


def _get_spotify_client_token() -> str:
    """Get a Spotify token using Client Credentials flow or Web Player Token fallback."""
    global _spotify_cc_cache
    if _spotify_cc_cache["access_token"] and time.time() < _spotify_cc_cache["expires_at"] - 30:
        return _spotify_cc_cache["access_token"]

    client_id = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
    if client_id and client_secret:
        try:
            credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
            data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
            req = urllib.request.Request(
                "https://accounts.spotify.com/api/token",
                data=data,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                token_data = json.loads(resp.read().decode())
            access_token = token_data.get("access_token", "")
            expires_in = int(token_data.get("expires_in", 3600))
            _spotify_cc_cache = {"access_token": access_token, "expires_at": time.time() + expires_in}
            print(f"[Spotify] Client-Credentials token obtained (expires in {expires_in}s)")
            return access_token
        except Exception as err:
            print(f"[Spotify] Client-Credentials token failed: {err}")

    # Fallback to anonymous Web Player token
    anon = _get_spotify_web_anon_token()
    if anon:
        _spotify_cc_cache = {"access_token": anon, "expires_at": time.time() + 1800}
    return ""


def _search_track_uri(token: str, query: str) -> str:
    """Search Spotify catalog for `query`, return the top spotify:track:ID or ''."""
    try:
        url = "https://api.spotify.com/v1/search?" + urllib.parse.urlencode({
            "q": query,
            "type": "track",
            "limit": 1,
            "market": "IN",
        })
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        items = data.get("tracks", {}).get("items", [])
        if not items:
            print(f"[Spotify] No track found for: '{query}'")
            return ""
        track = items[0]
        name = track.get("name", query)
        artists = ", ".join(a["name"] for a in track.get("artists", []))
        uri = track["uri"]
        print(f"[Spotify] Found: '{name}' by {artists} → {uri}")
        return uri
    except Exception as err:
        print(f"[Spotify] Search error: {err}")
        return ""


def _get_spotify_access_token() -> str:
    """Return a valid Spotify access token using the stored refresh token (user OAuth).

    Requires SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and SPOTIFY_REFRESH_TOKEN.
    Run backend/spotify_auth_setup.py once to generate the refresh token.
    """
    global _spotify_token_cache
    if _spotify_token_cache["access_token"] and time.time() < _spotify_token_cache["expires_at"] - 30:
        return _spotify_token_cache["access_token"]

    client_id = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
    refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN", "").strip()

    if not client_id or not client_secret or not refresh_token:
        return ""

    try:
        credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }).encode()
        req = urllib.request.Request(
            "https://accounts.spotify.com/api/token",
            data=data,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            token_data = json.loads(resp.read().decode())

        access_token = token_data.get("access_token", "")
        expires_in = int(token_data.get("expires_in", 3600))
        if token_data.get("refresh_token"):
            os.environ["SPOTIFY_REFRESH_TOKEN"] = token_data["refresh_token"]
        _spotify_token_cache = {"access_token": access_token, "expires_at": time.time() + expires_in}
        print(f"[Spotify] User token refreshed (expires in {expires_in}s)")
        return access_token
    except Exception as err:
        print(f"[Spotify] User token refresh failed: {err}")
        return ""


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
    """Launch an application on macOS with strict input sanitization."""
    clean_name = re.sub(r'[^a-zA-Z0-9\s._\-]', '', app_name).strip()
    if not clean_name:
        return False
    if IS_MAC:
        try:
            subprocess.Popen(["open", "-a", clean_name])
            return True
        except Exception as err:
            print(f"[Automation] Failed to open app {clean_name}: {err}")
            return False
    return False


def close_app(app_name: str) -> bool:
    """Quit an application gracefully using AppleScript with strict input sanitization."""
    clean_name = re.sub(r'[^a-zA-Z0-9\s._\-]', '', app_name).strip()
    if not clean_name:
        return False
    if IS_MAC:
        try:
            script = f'tell application "{clean_name}" to quit'
            subprocess.Popen(["osascript", "-e", script])
            return True
        except Exception as err:
            print(f"[Automation] Failed to quit app {clean_name}: {err}")
            return False
    return False


def _paste_text_via_clipboard(text: str) -> str:
    """Return AppleScript snippet that pastes text via clipboard — works for Unicode/Hindi/Devanagari."""
    # Escape backslashes and double quotes for AppleScript string
    safe = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'''
        set the clipboard to "{safe}"
        delay 0.1
        keystroke "v" using {{command down}}
    '''


# ── Spotify Local Cache ────────────────────────────────────────────────────────
SPOTIFY_CACHE_FILE = Path(__file__).parent.parent / "data" / "spotify_cache.json"
SPOTIFY_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_spotify_cache() -> dict:
    if not SPOTIFY_CACHE_FILE.exists():
        return {}
    try:
        return json.loads(SPOTIFY_CACHE_FILE.read_text())
    except Exception:
        return {}


def _save_spotify_cache(cache: dict):
    try:
        SPOTIFY_CACHE_FILE.write_text(json.dumps(cache, indent=2))
    except Exception as err:
        print(f"[Spotify Cache] Failed to save cache: {err}")


def wait_until_spotify_running(timeout: float = 10.0) -> bool:
    """Dynamically wait until Spotify process is running in background (-g flag)."""
    start = time.time()
    while time.time() - start < timeout:
        if is_spotify_running():
            return True
        subprocess.Popen(["open", "-g", "-a", "Spotify"])
        time.sleep(0.5)
    return is_spotify_running()


def _strip_qualifiers(title: str) -> str:
    """Remove parenthetical and bracketed text e.g. '(Sped Up)', '[Remix]' for accurate title comparisons."""
    return re.sub(r"\(.*?\)|\[.*?\]", "", title).strip()


def _score_track_match(query: str, track_name: str, artist_name: str, popularity: int = 50) -> float:
    """Calculate similarity score (0.0 to 100.0) based on 15-point architectural spec:

    - 70% Title Match
    - 15% Artist Match
    - 15% Popularity Score
    - Heavy penalties for unwanted Remix, Cover, Karaoke, LoFi, Sped Up, or Live tracks.
    """
    q = query.lower().strip()
    t = track_name.lower().strip()
    a = artist_name.lower().strip()
    clean_t = _strip_qualifiers(t).lower()

    title_score = difflib.SequenceMatcher(None, q, clean_t).ratio() * 70.0
    artist_score = difflib.SequenceMatcher(None, q, a).ratio() * 15.0 if a else 0.0
    pop_score = (min(100, max(0, popularity)) / 100.0) * 15.0

    score = title_score + artist_score + pop_score

    # Exact title or clean title substring bonus
    if q == clean_t:
        score += 35.0
    elif q in clean_t:
        score += 20.0

    # If query does not mention 'feat' or 'with', penalize featured/collaboration titles slightly
    if ('feat' in t or 'with' in t) and 'feat' not in q and 'with' not in q:
        score -= 15.0

    # Heavy penalties for derivative/remix versions
    penalties = [
        "remix", "cover", "karaoke", "lofi", "lo-fi", "instrumental", "acoustic", "live",
        "slowed", "reverbed", "sped up", "sped-up", "nightcore", "8d audio", "8d",
        "bass boosted", "extended", "looped", "tiktok", "type beat", "parody"
    ]
    for kw in penalties:
        if kw in t and kw not in q:
            score -= 40.0

    return score


def _find_spotify_track_uri_web(song_query: str) -> dict:
    """Direct native Spotify Desktop URI search resolver with zero-auth metadata resolution.

    Queries iTunes zero-auth API to extract exact track title & primary artist name,
    eliminating generic search ambiguity so Spotify Desktop plays original songs instead of trending remixes.
    """
    clean_q = song_query.strip()
    if not clean_q:
        return {"uri": "", "title": "", "artist": ""}

    url = f"https://itunes.apple.com/search?term={urllib.parse.quote(clean_q)}&entity=song&limit=10"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    results = []
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
            results = data.get("results", [])
    except Exception as err:
        print(f"[Spotify Metadata Resolver] iTunes lookup warning: {err}")

    best_match = None
    best_score = -999.0

    for item in results:
        t_name = item.get("trackName", "")
        a_name = item.get("artistName", "")
        score = _score_track_match(clean_q, t_name, a_name)
        if score > best_score:
            best_score = score
            best_match = item

    if best_match:
        track_title = best_match.get("trackName", clean_q)
        artist_name = best_match.get("artistName", "")
        album_name  = best_match.get("collectionName", "")
        # Clean track title and album name for Spotify search
        clean_title = _strip_qualifiers(track_title)
        clean_album = _strip_qualifiers(album_name)

        # Pinpoint Search String: Track + Primary Artist + Original Album Name
        # Explicitly targets the original track & album, eliminating derivative remixes
        spotify_search_q = f"{clean_title} {artist_name} {clean_album}".strip()
        native_search_uri = f"spotify:search:{urllib.parse.quote(spotify_search_q)}"
        print(f"[Spotify Metadata Resolver] ⚡ Resolved '{clean_q}' -> Track: '{track_title}' by {artist_name} (Album: {album_name}) (Score {best_score:.1f})")
        print(f"[Spotify Direct Search] 🚀 URI: {native_search_uri}")
        return {"uri": native_search_uri, "title": track_title, "artist": artist_name}

    native_search_uri = f"spotify:search:{urllib.parse.quote(clean_q)}"
    print(f"[Spotify Direct Search] ⚡ Fallback native search: {native_search_uri}")
    return {"uri": native_search_uri, "title": clean_q, "artist": ""}


def _search_best_track_uri(token: str, query: str) -> dict:
    """Search Spotify API with limit=10, structured track:X artist:Y formatting, and score ranking. Returns dict."""
    clean_q = query.strip()
    if not clean_q or not token:
        return {"uri": "", "title": "", "artist": ""}

    market = os.getenv("SPOTIFY_MARKET", "").strip()

    search_q = clean_q
    if " by " in clean_q.lower():
        parts = re.split(r'\s+by\s+', clean_q, flags=re.I)
        if len(parts) == 2:
            search_q = f"track:{parts[0].strip()} artist:{parts[1].strip()}"

    params = {"q": search_q, "type": "track", "limit": 10}
    if market:
        params["market"] = market

    url = "https://api.spotify.com/v1/search?" + urllib.parse.urlencode(params)

    items = []
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode())
            items = data.get("tracks", {}).get("items", [])
            if items:
                break
        except Exception as err:
            print(f"[Spotify API] Search attempt {attempt + 1} failed: {err}")
            time.sleep(1.0)

    if not items:
        print(f"[Spotify API] ❌ No tracks found for '{search_q}'")
        return {"uri": "", "title": "", "artist": ""}

    best_track = None
    best_score = -999.0

    for item in items:
        name = item.get("name", "")
        artists = ", ".join(art["name"] for art in item.get("artists", []))
        pop = item.get("popularity", 50)
        score = _score_track_match(clean_q, name, artists, pop)
        print(f"[Spotify Scorer] Candidate: '{name}' by {artists} (pop {pop}) -> Score {score:.1f}")
        if score > best_score:
            best_score = score
            best_track = item

    if best_track:
        artists = ", ".join(art["name"] for art in best_track.get("artists", []))
        uri = best_track["uri"]
        title = best_track.get("name", "")
        print(f"[Spotify API] ✅ Best match: '{title}' by {artists} (Score {best_score:.1f}) -> {uri}")
        return {"uri": uri, "title": title, "artist": artists}

    return {"uri": "", "title": "", "artist": ""}


def _execute_applescript_silent(script_body: str) -> subprocess.CompletedProcess:
    """Execute AppleScript while preserving current frontmost window focus and keeping Spotify hidden."""
    full_script = f'''
    tell application "System Events"
        set activeProc to name of first application process whose frontmost is true
    end tell
    {script_body}
    tell application "System Events"
        try
            if activeProc is not "Spotify" then
                set visible of process "Spotify" to false
                set frontmost of process activeProc to true
            end if
        end try
    end tell
    '''
    return subprocess.run(["osascript", "-e", full_script], timeout=5, capture_output=True)


def verify_spotify_playback(expected_title: str = "", expected_artist: str = "") -> bool:
    """Verify active playback state and validate that expected title/artist matches playing track."""
    if not IS_MAC or not is_spotify_running():
        print("[Spotify Verification] ❌ Spotify is not running.")
        return False

    for attempt in range(1, 4):
        info = get_spotify_current_track()
        if info.get("playing"):
            if info.get("is_ad"):
                print(f"[Spotify Verification] 📢 Spotify is playing an advertisement ('{info.get('title')}'). Track queued!")
                return True

            actual_title = info.get("title", "").strip()
            actual_artist = info.get("artist", "").strip()

            if expected_title:
                actual_comb = f"{actual_title} {actual_artist}".lower()
                expected_comb = f"{expected_title} {expected_artist}".lower()
                sim = difflib.SequenceMatcher(None, expected_comb, actual_comb).ratio()

                clean_exp = _strip_qualifiers(expected_title).lower()
                clean_act = _strip_qualifiers(actual_title).lower()
                match_ok = sim >= 0.40 or (clean_exp and clean_exp in clean_act) or (clean_act and clean_act in clean_exp)

                if not match_ok:
                    print(f"[Spotify Verification] ❌ Track title mismatch: Playing '{actual_title}' by {actual_artist} — Expected '{expected_title}' (Sim: {sim:.2f})")
                    return False

            print(f"[Spotify Verification] ✅ Verified playback active: '{actual_title}' by {actual_artist}")
            return True

        print(f"[Spotify Verification] ⚠️ Attempt {attempt}: Player state is paused. Sending explicit AppleScript play command...")
        _execute_applescript_silent('tell application "Spotify" to play')
        time.sleep(1.2)

    final_info = get_spotify_current_track()
    if final_info.get("playing"):
        print(f"[Spotify Verification] ✅ Playback verified active: '{final_info.get('title')}'")
        return True

    print("[Spotify Verification] ❌ Playback verification failed.")
    return False


def play_spotify_uri(uri: str) -> bool:
    """Load and play a Spotify URI synchronously in the background without stealing window focus."""
    if not uri:
        return False
    try:
        if IS_MAC:
            _execute_applescript_silent(f'tell application "Spotify" to play track "{uri}"')
            print(f"[Spotify] ✅ Background URI play executed: {uri}")
            return True
        else:
            subprocess.run(["osascript", "-e", f'tell application "Spotify" to play track "{uri}"'], timeout=5, capture_output=True)
            return True
    except Exception as err:
        print(f"[Spotify] URI play error: {err}")
        return False


def search_and_play_spotify(song_query: str) -> bool:
    """Clean, robust Spotify playback engine with post-verification caching.

    Architecture Flow:
      1. Check Local Cache (Instant playback for repeat queries, verified against title)
      2. Ensure Spotify Desktop App is Running
      3. Spotify Search API (Top 10 results + 70/15/15 Fuzzy & Popularity Ranking)
      4. Trigger Playback via Track URI
      5. Strict Playback Verification (matches playing title against expected)
      6. Cache ONLY on Verified Success
    """
    if not song_query:
        return False

    norm_q = song_query.strip().lower()
    print(f"[Spotify] 🎵 Received request to play: '{song_query.strip()}'")

    # Local Cache Lookup
    cache = _load_spotify_cache()
    cached_uri = cache.get(norm_q)
    if cached_uri:
        print(f"[Spotify Cache] ⚡ Cache HIT for '{norm_q}' -> {cached_uri}")
        wait_until_spotify_running()
        play_spotify_uri(cached_uri)
        if verify_spotify_playback(expected_title=song_query.strip()):
            return True
        print("[Spotify Cache] Cached URI verification failed or played wrong track — invalidating cache entry...")
        del cache[norm_q]
        _save_spotify_cache(cache)

    wait_until_spotify_running()

    user_token = _get_spotify_access_token()
    client_token = _get_spotify_client_token()
    result_meta = {"uri": "", "title": "", "artist": ""}

    if user_token:
        token_type = "USER"
        result_meta = _search_best_track_uri(user_token, song_query.strip())
    elif client_token:
        token_type = "CLIENT"
        result_meta = _search_best_track_uri(client_token, song_query.strip())
    else:
        token_type = "NONE"

    track_uri = result_meta.get("uri", "")
    expected_title = result_meta.get("title", song_query.strip())
    expected_artist = result_meta.get("artist", "")

    if not track_uri:
        print("[Spotify] API token absent or returned no match — using zero-auth web URI resolver...")
        result_meta = _find_spotify_track_uri_web(song_query.strip())
        track_uri = result_meta.get("uri", "")

    if not track_uri:
        print(f"[Spotify] ❌ Could not resolve track URI for '{song_query}'")
        return False

    print("TRACK URI:", track_uri)
    print("TOKEN TYPE:", token_type)

    played_ok = False
    if user_token and track_uri and not track_uri.startswith("spotify:search:"):
        try:
            devices_url = "https://api.spotify.com/v1/me/player/devices"
            dev_req = urllib.request.Request(devices_url, headers={"Authorization": f"Bearer {user_token}"})
            device_id = ""
            try:
                with urllib.request.urlopen(dev_req, timeout=4) as dev_resp:
                    dev_data = json.loads(dev_resp.read().decode())
                    devices = dev_data.get("devices", [])
                    for d in devices:
                        if d.get("is_active"):
                            device_id = d.get("id", "")
                            break
                    if not device_id and devices:
                        device_id = devices[0].get("id", "")
            except Exception:
                pass

            play_endpoint = "https://api.spotify.com/v1/me/player/play"
            if device_id:
                play_endpoint += f"?device_id={device_id}"

            play_data = json.dumps({"uris": [track_uri]}).encode()
            play_req = urllib.request.Request(
                play_endpoint,
                data=play_data,
                headers={
                    "Authorization": f"Bearer {user_token}",
                    "Content-Type": "application/json",
                },
                method="PUT",
            )
            with urllib.request.urlopen(play_req, timeout=6) as r:
                if r.status in (200, 204):
                    print(f"[Spotify] ✅ Successfully triggered playback via Web API")
                    played_ok = True
        except Exception as err:
            print(f"[Spotify] Web API playback error: {err}")

    if not played_ok:
        print(f"[Spotify] 🚀 Playing track URI via AppleScript fallback: {track_uri}")
        play_spotify_uri(track_uri)

    # Validate playback against expected track title/artist
    if verify_spotify_playback(expected_title=expected_title, expected_artist=expected_artist):
        if track_uri and not track_uri.startswith("spotify:search:"):
            print(f"[Spotify Cache] ✅ Verification passed — caching '{norm_q}' -> {track_uri}")
            cache[norm_q] = track_uri
            _save_spotify_cache(cache)
        else:
            print(f"[Spotify Cache] ℹ️ Played via generic search URI — skipping cache write for '{norm_q}'")
        return True

    print(f"[Spotify] ❌ Verification failed for '{song_query}' — skipping cache write.")
    return False


# Spotify playlists — direct URIs for instant reliable playback (loads from env or default)
PLAYLIST_HINDI   = os.getenv("SPOTIFY_PLAYLIST_HINDI",   "spotify:playlist:4SuEAsJ6ulS62RYJk88Sap")
PLAYLIST_ENGLISH = os.getenv("SPOTIFY_PLAYLIST_ENGLISH", "spotify:playlist:2CCKzQqgsc50gtJeYDonJh")
PLAYLIST_KRISHNA = os.getenv("SPOTIFY_PLAYLIST_KRISHNA", "spotify:playlist:3Fd9z849SrTBEtHDTgQvXo")


def get_spotify_current_track() -> dict:
    """Fetch details of currently active Spotify track via AppleScript including live volume level.

    Uses a unique multi-char separator (|||SEP|||) to avoid conflicts with song/artist names.
    """
    if not IS_MAC or not is_spotify_running():
        return {"playing": False, "title": "", "artist": "", "album": "", "state": "stopped",
                "artwork_url": "", "position": 0, "duration": 180, "volume": 70}
    try:
        SEP = "|||SEP|||"
        script = f'''
        tell application "Spotify"
            try
                set trackName  to name of current track
                set artistName to artist of current track
                set albumName  to album of current track
                set trackState to (player state as string)
                set artworkURL to artwork url of current track
                set trackPos   to player position
                set trackDur   to (duration of current track) / 1000
                set trackVol   to sound volume
                return trackName & "{SEP}" & artistName & "{SEP}" & albumName & "{SEP}" & trackState & "{SEP}" & artworkURL & "{SEP}" & trackPos & "{SEP}" & trackDur & "{SEP}" & trackVol
            on error
                return "STOPPED"
            end try
        end tell
        '''
        res = subprocess.check_output(["osascript", "-e", script], timeout=3).decode("utf-8").strip()
        if not res or res == "STOPPED" or SEP not in res:
            return {"playing": False, "title": "", "artist": "", "album": "", "state": "stopped",
                    "artwork_url": "", "position": 0, "duration": 180, "volume": 70}

        parts = res.split(SEP)
        title       = parts[0].strip()
        artist      = parts[1].strip() if len(parts) > 1 else ""
        album       = parts[2].strip() if len(parts) > 2 else ""
        state       = parts[3].strip().lower() if len(parts) > 3 else "stopped"
        artwork_url = parts[4].strip() if len(parts) > 4 else ""
        position    = float(parts[5].strip()) if len(parts) > 5 and parts[5].strip() else 0.0
        duration    = float(parts[6].strip()) if len(parts) > 6 and parts[6].strip() else 180.0
        volume      = int(float(parts[7].strip())) if len(parts) > 7 and parts[7].strip() else 70

        is_ad = "ad-free" in title.lower() or "advertisement" in title.lower() or ("spotify" in title.lower() and not artist)

        return {
            "playing":     state == "playing",
            "is_ad":       is_ad,
            "title":       title,
            "artist":      artist,
            "album":       album,
            "state":       state,
            "artwork_url": artwork_url,
            "position":    round(position),
            "duration":    round(duration),
            "volume":      volume,
        }
    except Exception as err:
        print(f"[Automation] Error fetching current track: {err}")
        return {"playing": False, "title": "", "artist": "", "album": "", "state": "stopped",
                "artwork_url": "", "position": 0, "duration": 180, "volume": 70}


def set_spotify_position(seconds: float) -> bool:
    """Set Spotify player playback position in seconds via AppleScript."""
    if not IS_MAC or not is_spotify_running():
        return False
    try:
        script = f'tell application "Spotify" to set player position to {seconds}'
        subprocess.Popen(["osascript", "-e", script])
        return True
    except Exception as err:
        print(f"[Automation] Error setting player position: {err}")
        return False


def add_current_track_to_playlist(target_playlist: str = "hindi") -> bool:
    """Save currently playing track — uses Spotify Web API like-song endpoint (Cmd+S shortcut)."""
    if not IS_MAC or not is_spotify_running():
        return False
    try:
        # Cmd+S in Spotify desktop saves current track to liked songs / library
        script = '''
        tell application "Spotify" to activate
        delay 0.3
        tell application "System Events"
            tell process "Spotify"
                try
                    keystroke "s" using {command down}
                on error errMsg
                    log "Save track error: " & errMsg
                end try
            end tell
        end tell
        '''
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            print(f"[Automation] Save track AppleScript error: {result.stderr.strip()}")
        return True
    except Exception as err:
        print(f"[Automation] Error adding track to playlist: {err}")
        return False


def take_screenshot() -> str:
    """Take a full screen screenshot on macOS using screencapture and save to Desktop."""
    if not IS_MAC:
        return ""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        desktop_path = Path.home() / "Desktop" / f"FRIDAY_Screenshot_{timestamp}.png"
        subprocess.run(["screencapture", "-x", str(desktop_path)], check=True, timeout=10)
        return str(desktop_path)
    except Exception as err:
        print(f"[Automation] Screenshot failed: {err}")
        return ""


def _get_spotify_volume() -> int:
    """Get current Spotify sound volume (0-100)."""
    try:
        result = subprocess.run(
            ["osascript", "-e", "tell application \"Spotify\" to get sound volume"],
            capture_output=True, text=True, timeout=3
        )
        return int(result.stdout.strip())
    except Exception:
        return 50  # fallback


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
                    try
                        set sound volume to {vol_clamped}
                    on error errMsg
                        log "Volume set error: " & errMsg
                    end try
                end tell'''
                subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
            return True

        if cmd in ("play_hindi_playlist", "play_english_playlist", "play_krishna_playlist", "play_specific"):
            if volume_percent >= 0:
                vol_clamped = max(0, min(100, volume_percent))
                vol_script = f'tell application "Spotify" to set sound volume to {vol_clamped}'
                subprocess.run(["osascript", "-e", vol_script], capture_output=True, timeout=5)
            if cmd == "play_hindi_playlist":
                play_spotify_uri(PLAYLIST_HINDI)
            elif cmd == "play_english_playlist":
                play_spotify_uri(PLAYLIST_ENGLISH)
            elif cmd == "play_krishna_playlist":
                play_spotify_uri(PLAYLIST_KRISHNA)
            else:
                search_and_play_spotify(query)
            return True

        # --- Volume up/down: fetch current volume first, then set ---
        if cmd == "volume_up":
            current_vol = _get_spotify_volume()
            new_vol = min(100, current_vol + 20)
            script = f'tell application "Spotify" to set sound volume to {new_vol}'
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
            return True

        if cmd == "volume_down":
            current_vol = _get_spotify_volume()
            new_vol = max(0, current_vol - 20)
            script = f'tell application "Spotify" to set sound volume to {new_vol}'
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
            return True

        if cmd == "mute":
            script = 'tell application "Spotify" to set sound volume to 0'
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
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
            "repeat":     "set repeating to true",
            "shuffle":    "set shuffling to true",
        }

        spotify_action = action_map.get(cmd, "play")

        # Build atomic AppleScript with optional volume line + command
        vol_line = ""
        if volume_percent >= 0:
            vol_clamped = max(0, min(100, volume_percent))
            vol_line = f"\n            set sound volume to {vol_clamped}"

        script_body = f'''
        tell application "Spotify"
            try
                {vol_line}
                {spotify_action}
            on error errMsg
                log "Spotify action error: " & errMsg
            end try
        end tell'''
        result = _execute_applescript_silent(script_body)
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

    elif action == "play_krishna_playlist":
        control_spotify("play_krishna_playlist", volume_percent=volume_percent)
        return "Playing your Krishna playlist, Prem."

    elif action == "play_specific":
        control_spotify("play_specific", target_clean, volume_percent=volume_percent)
        msg = f"Opening Spotify and playing '{target_clean}', Prem."
        if volume_percent >= 0:
            msg += f" Sound set to {volume_percent}%."
        return msg

    elif action in ("play_music", "play_spotify"):
        if target_clean:
            control_spotify("play_specific", target_clean, volume_percent=volume_percent)
            return f"Playing '{target_clean}' on Spotify, Prem."
        control_spotify("play", volume_percent=volume_percent)
        return "Playing Spotify music now, Prem."

    elif action in ("pause_music", "pause_spotify"):
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
