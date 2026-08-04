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
import threading
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
_spotify_cache_lock = threading.Lock()
SPOTIFY_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_spotify_cache() -> dict:
    with _spotify_cache_lock:
        if not SPOTIFY_CACHE_FILE.exists():
            return {}
        try:
            return json.loads(SPOTIFY_CACHE_FILE.read_text())
        except Exception:
            return {}


def _save_spotify_cache(cache: dict):
    with _spotify_cache_lock:
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
    """Calculate similarity score (0.0 to 150.0) for matching a user query to a Spotify track.

    Scoring breakdown:
    - Title containment / overlap (up to 70 pts)
    - Exact title match bonus (+45 pts)
    - Word-completeness bonus (+20 pts — all query words appear in clean title)
    - Substring bonus (+15 pts — entire query is a substring of the title)
    - Popularity score (up to 15 pts)
    - Artist relevance bonus (up to 10 pts)
    - Heavy penalties (‑45 each) for Remix, Cover, Karaoke, LoFi, Sped Up, Live, etc.
    - Featured-track penalty (‑20) if query doesn't mention 'feat'
    """
    q = query.lower().strip()
    t = track_name.lower().strip()
    a = artist_name.lower().strip()
    clean_t = _strip_qualifiers(t).lower()

    score = 0.0

    # ── Title containment (core signal) ──────────────────────────────────────
    # Perfect match gets massive priority (+150 pts) so popularity can never override it
    if q == clean_t:
        score += 150.0
    elif q in clean_t:
        score += 90.0
        if clean_t.startswith(q):
            score += 30.0
    elif clean_t in q:
        score += 70.0
    else:
        # SequenceMatcher fallback
        ratio = difflib.SequenceMatcher(None, q, clean_t).ratio()
        score += ratio * 40.0

    # ── Word-completeness bonus: every word in query appears in title ───────
    q_words = [w for w in q.split() if len(w) > 2]
    if q_words and all(w in clean_t for w in q_words):
        score += 30.0

    # ── Artist relevance bonus (up to 50 pts) ────────────────────────────────
    q_lower = q
    for artist_part in re.split(r'[,&]', a):
        artist_part = artist_part.strip()
        if artist_part and artist_part in q_lower:
            score += 50.0
            break

    # ── Popularity bonus (capped at max 10 pts so it NEVER overrides title/artist match) ──
    pop_score = (min(100, max(0, popularity)) / 100.0) * 10.0
    score += pop_score

    # ── Heavy penalties for derivative/remix/synthwave/cover versions ────────
    penalties = [
        "remix", "cover", "karaoke", "lofi", "lo-fi", "instrumental", "acoustic", "live",
        "slowed", "reverbed", "sped up", "sped-up", "nightcore", "8d audio", "8d",
        "bass boosted", "extended", "looped", "tiktok", "type beat", "parody", "synthwave",
        "mashup", "dubstep", "flip", "remake", "club", "dj mix"
    ]
    for kw in penalties:
        if kw in t and kw not in q:
            score -= 250.0

    return score


def _find_spotify_track_uri_web(song_query: str) -> dict:
    """Zero-auth track URI resolver using iTunes metadata + multi-strategy search.

    Strategy:
    1. Query iTunes API to resolve the exact track name & artist
    2. Build multiple Spotify search URIs — full title (with album qualifiers) + artist
       → This is far more precise than using the stripped bare title
    3. Try API search (if by chance a token is available)
    4. Verify playback after playing and retry if wrong
    """
    clean_q = song_query.strip()
    if not clean_q:
        return {"uri": "", "title": "", "artist": ""}

    # Try anonymous Spotify web token for a proper API search (may fail → silent)
    anon_token = _get_spotify_web_anon_token()
    if anon_token:
        api_result = _search_best_track_uri(anon_token, clean_q)
        if api_result.get("uri"):
            print(f"[Spotify Zero-Auth] ✅ Anon API resolved '{clean_q}' → '{api_result['title']}' by {api_result['artist']}")
            return api_result

    # iTunes zero-auth API to resolve exact track metadata
    url = f"https://itunes.apple.com/search?term={urllib.parse.quote(clean_q)}&entity=song&limit=10&country=IN"
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
        artist_name  = best_match.get("artistName", "")
        album_name   = best_match.get("collectionName", "")
        # Extract only the primary (first) artist for a cleaner search
        primary_artist = re.split(r"[,&]", artist_name)[0].strip()

        # CRITICAL: Use the FULL track title including album qualifiers like
        # "(From "Brahmastra")" — these qualifiers DISTINGUISH the original
        # track from remixes/covers/alternate versions on Spotify.
        # Previously we stripped them, which made the search ambiguous!
        spotify_search_queries = []

        # Strategy 1: Full title + primary artist (most precise)
        spotify_search_queries.append(f"{track_title} {primary_artist}")

        # Strategy 2: Full title + album name (helps disambiguate)
        if album_name and album_name.lower() not in track_title.lower():
            spotify_search_queries.append(f"{track_title} {album_name}")

        # Strategy 3: Full title alone
        if track_title != clean_q:
            spotify_search_queries.append(track_title)

        # Strategy 4: Clean title + artist (fallback)
        clean_title = _strip_qualifiers(track_title)
        if clean_title.lower() != track_title.lower():
            spotify_search_queries.append(f"{clean_title} {primary_artist}")

        # Strategy 5: Bare query (last resort)
        if clean_q not in ' '.join(spotify_search_queries).lower():
            spotify_search_queries.append(clean_q)

        native_search_uri = f"spotify:search:{urllib.parse.quote(spotify_search_queries[0])}"
        print(f"[Spotify Metadata Resolver] ⚡ iTunes resolved '{clean_q}' → '{track_title}' by {artist_name} (Score {best_score:.1f})")
        print(f"[Spotify Metadata Resolver] 🔍 Search strategies:")
        for i, q in enumerate(spotify_search_queries):
            print(f"    {i+1}. spotify:search:{urllib.parse.quote(q)}")
        print(f"[Spotify Direct Search] 🚀 Using: {native_search_uri}")

        # Also try the anonymous token with a precise title+artist search
        if anon_token:
            precise_q = f"track:\"{track_title}\" artist:{primary_artist}"
            anon_url = "https://api.spotify.com/v1/search?" + urllib.parse.urlencode({
                "q": precise_q, "type": "track", "limit": 1, "market": "IN"
            })
            try:
                anon_req = urllib.request.Request(anon_url, headers={"Authorization": f"Bearer {anon_token}"})
                with urllib.request.urlopen(anon_req, timeout=4) as anon_resp:
                    anon_data = json.loads(anon_resp.read().decode())
                anon_items = anon_data.get("tracks", {}).get("items", [])
                if anon_items:
                    uri = anon_items[0]["uri"]
                    name = anon_items[0].get("name", "")
                    artists = ", ".join(a["name"] for a in anon_items[0].get("artists", []))
                    print(f"[Spotify Metadata Resolver] ✅ Precise API match: '{name}' by {artists} → {uri}")
                    return {"uri": uri, "title": name, "artist": artists}
            except Exception as err:
                print(f"[Spotify Metadata Resolver] Precise API search failed: {err}")

        # Return the first search URI with the FULL track title + artist
        return {"uri": native_search_uri, "title": track_title, "artist": primary_artist,
                "_alt_search_uris": [f"spotify:search:{urllib.parse.quote(q)}" for q in spotify_search_queries[1:]]}

    # Absolute last resort: bare search URI
    native_search_uri = f"spotify:search:{urllib.parse.quote(clean_q)}"
    print(f"[Spotify Direct Search] ⚡ Fallback native search: {native_search_uri}")
    return {"uri": native_search_uri, "title": clean_q, "artist": ""}



def _search_best_track_uri(token: str, query: str) -> dict:
    """Search Spotify API with limit=20, structured track:X query, and smarter score ranking. Returns dict."""
    clean_q = query.strip()
    if not clean_q or not token:
        return {"uri": "", "title": "", "artist": ""}

    market = os.getenv("SPOTIFY_MARKET", "").strip()
    if not market:
        market = "IN"  # Default to Indian market for Bollywood accuracy

    # Always use track:X filter so Spotify restricts matches to track names
    search_q = f"track:{clean_q}"
    if " by " in clean_q.lower():
        parts = re.split(r'\s+by\s+', clean_q, flags=re.I)
        if len(parts) == 2:
            search_q = f"track:{parts[0].strip()} artist:{parts[1].strip()}"

    params = {"q": search_q, "type": "track", "limit": 20}
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

    # Sort candidates by match score
    scored_candidates = []
    for item in items:
        name = item.get("name", "")
        artists = ", ".join(art["name"] for art in item.get("artists", []))
        pop = item.get("popularity", 50)
        score = _score_track_match(clean_q, name, artists, pop)
        scored_candidates.append({
            "uri": item["uri"],
            "title": name,
            "artist": artists,
            "popularity": pop,
            "score": score
        })

    scored_candidates.sort(key=lambda x: x["score"], reverse=True)
    best_track = scored_candidates[0] if scored_candidates else {"uri": "", "title": "", "artist": ""}
    print(f"[Spotify API] ✅ Top match: '{best_track.get('title')}' by {best_track.get('artist')} -> {best_track.get('uri')}")

    return {
        "uri": best_track.get("uri", ""),
        "title": best_track.get("title", ""),
        "artist": best_track.get("artist", ""),
        "candidates": scored_candidates[:5]
    }


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


def verify_spotify_playback(expected_title: str = "", expected_artist: str = "", is_search_uri: bool = False) -> bool:
    """Verify active playback state and validate that expected title/artist matches playing track.

    Args:
        expected_title: Title we expected to play (from API search result)
        expected_artist: Artist we expected (from API search result)
        is_search_uri: If True, we used a generic spotify:search: URI — check that at
                       least the PLAYING track title contains query keywords.
    """
    if not IS_MAC or not is_spotify_running():
        print("[Spotify Verification] ❌ Spotify is not running.")
        return False

    for attempt in range(1, 5):  # 4 attempts, 1.5s apart = up to 6s total
        info = get_spotify_current_track()
        if info.get("playing"):
            if info.get("is_ad"):
                print(f"[Spotify Verification] 📢 Spotify is playing an advertisement. Track queued!")
                return True

            actual_title = info.get("title", "").strip()
            actual_artist = info.get("artist", "").strip()

            # Strict title verification
            clean_exp = _strip_qualifiers(expected_title).lower()
            clean_act = _strip_qualifiers(actual_title).lower()
            q_words = [w for w in clean_exp.split() if len(w) > 2]
            
            word_match = any(w in clean_act for w in q_words) if q_words else (clean_exp in clean_act or clean_act in clean_exp)
            sim = difflib.SequenceMatcher(None, clean_exp, clean_act).ratio()

            if not word_match and sim < 0.55:
                print(f"[Spotify Verification] ❌ Title mismatch: Playing '{actual_title}' — Expected '{expected_title}' (Sim: {sim:.2f})")
                return False

            print(f"[Spotify Verification] ✅ Verified playing: '{actual_title}' by {actual_artist}")
            return True

        print(f"[Spotify Verification] ⚠️ Attempt {attempt}: Not playing yet — sending play command...")
        _execute_applescript_silent('tell application "Spotify" to play')
        time.sleep(1.5)

    final_info = get_spotify_current_track()
    if final_info.get("playing"):
        print(f"[Spotify Verification] ✅ Playback confirmed: '{final_info.get('title')}'")
        return True

    print("[Spotify Verification] ❌ Playback verification failed after all attempts.")
    return False



def play_spotify_uri(uri: str) -> bool:
    """Loads and plays a Spotify URI directly via AppleScript or Web API without UI keystrokes."""
    if not uri:
        return False
    try:
        if IS_MAC:
            _execute_applescript_silent(f'tell application "Spotify" to play track "{uri}"')
            print(f"[Spotify Direct Play] ✅ Direct URI playback triggered: {uri}")
            return True
        else:
            subprocess.run(["osascript", "-e", f'tell application "Spotify" to play track "{uri}"'], timeout=5, capture_output=True)
            return True
    except Exception as err:
        print(f"[Spotify Direct Play] URI play error: {err}")
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

    # ── 1. Song Memory Alias Lookup ("my gym song", "breakup song", "coding music") ──
    try:
        from database.repositories.song_memory_repo import SongMemoryRepository
        alias_match = SongMemoryRepository().lookup_alias(norm_q)
        if alias_match:
            song_name = alias_match.get("song_name", "")
            artist = alias_match.get("artist", "")
            saved_uri = alias_match.get("spotify_uri", "")
            print(f"[Song Memory] 🧠 Recognized alias '{norm_q}' -> '{song_name}' by {artist} (URI: {saved_uri})")
            wait_until_spotify_running()
            if saved_uri and not saved_uri.startswith("spotify:search:"):
                play_spotify_uri(saved_uri)
                return True
            else:
                song_query = f"{song_name} {artist}".strip()
                norm_q = song_query.lower()
    except Exception as err:
        print(f"[Song Memory] Lookup notice: {err}")

    # ── 2. Local Cache Lookup ──
    with _spotify_cache_lock:
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

    candidates = result_meta.get("candidates", [])
    if not candidates and track_uri:
        candidates = [{"uri": track_uri, "title": expected_title, "artist": expected_artist}]

    for idx, cand in enumerate(candidates):
        cand_uri = cand.get("uri", "")
        cand_title = cand.get("title", "").strip() or expected_title or song_query.strip()
        cand_artist = cand.get("artist", "").strip() or expected_artist

        if not cand_uri:
            continue

        print(f"[Verification Loop] 🔄 Trying candidate #{idx + 1}: '{cand_title}' by {cand_artist} ({cand_uri})...")
        if cand_uri.startswith("spotify:search:"):
            _execute_applescript_silent(f'tell application "Spotify" to open location "{cand_uri}"')
            time.sleep(0.5)
            _execute_applescript_silent('tell application "Spotify" to play')
            play_ok = True
        else:
            play_ok = play_spotify_uri(cand_uri)

        if play_ok:
            time.sleep(1.0)
            if verify_spotify_playback(expected_title=cand_title, expected_artist=cand_artist):
                print(f"[Verification Loop] ✅ Verified candidate #{idx + 1} matches requested song!")
                with _spotify_cache_lock:
                    cache = _load_spotify_cache()
                    cache[norm_q] = cand_uri
                    _save_spotify_cache(cache)
                return True
            else:
                print(f"[Verification Loop] ❌ Candidate #{idx + 1} failed verification — stopping playback and trying candidate #{idx + 2}...")
                _execute_applescript_silent('tell application "Spotify" to pause')
                time.sleep(0.5)

    print(f"[Spotify] ❌ All candidate verifications failed for '{song_query}'")
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


_pre_duck_volume = -1

def duck_spotify_volume() -> bool:
    """Temporarily duck (lower) Spotify volume while FRIDAY is speaking."""
    global _pre_duck_volume
    if not IS_MAC or not is_spotify_running():
        return False
    try:
        vol = _get_spotify_volume()
        if vol > 25:
            _pre_duck_volume = vol
            _execute_applescript_silent('tell application "Spotify" to set sound volume to 20')
            return True
    except Exception:
        pass
    return False

def unduck_spotify_volume() -> bool:
    """Restore Spotify volume back to pre-duck level after speaking."""
    global _pre_duck_volume
    if not IS_MAC or not is_spotify_running():
        return False
    try:
        if _pre_duck_volume > 0:
            _execute_applescript_silent(f'tell application "Spotify" to set sound volume to {_pre_duck_volume}')
            _pre_duck_volume = -1
            return True
    except Exception:
        pass
    return False


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
