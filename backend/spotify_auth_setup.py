"""
F.R.I.D.A.Y. Spotify One-Time Auth Setup
==========================================
Run this script ONCE to generate your Spotify refresh token.
It will:
  1. Open your browser to the Spotify authorization page
  2. Start a local server on port 8888 to capture the callback
  3. Exchange the auth code for access + refresh tokens
  4. Auto-write SPOTIFY_REFRESH_TOKEN to backend/.env

Usage:
    cd /Users/snehasahu/Desktop/FRIDAY/backend
    python spotify_auth_setup.py
"""

import os
import sys
import json
import base64
import urllib.parse
import urllib.request
import webbrowser
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# ─── Configuration ─────────────────────────────────────────────────────────────
REDIRECT_URI = "http://localhost:8888/callback"
SCOPES = " ".join([
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
    "streaming",
    "playlist-read-private",
    "playlist-modify-private",
    "user-library-modify",
])
ENV_PATH = Path(__file__).parent / ".env"

# ─── Read credentials from .env ────────────────────────────────────────────────
def _read_env() -> dict:
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def _write_env_key(key: str, value: str):
    """Insert or update a single key=value line in .env."""
    content = ENV_PATH.read_text() if ENV_PATH.exists() else ""
    pattern = re.compile(rf"^{re.escape(key)}\s*=.*$", re.MULTILINE)
    if pattern.search(content):
        content = pattern.sub(f"{key}={value}", content)
    else:
        content = content.rstrip("\n") + f"\n{key}={value}\n"
    ENV_PATH.write_text(content)
    print(f"  ✅ {key} saved to .env")


# ─── HTTP callback server ───────────────────────────────────────────────────────
_auth_code: str | None = None


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            _auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
                <html><body style='font-family:monospace;background:#0d0d0d;color:#00ff88;padding:40px'>
                <h2>&#10003; F.R.I.D.A.Y. Spotify Auth Complete!</h2>
                <p>You can close this tab and return to the terminal.</p>
                </body></html>
            """)
        elif "error" in params:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Authorization denied.")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass  # suppress server logs


# ─── Token exchange ─────────────────────────────────────────────────────────────
def _exchange_code(client_id: str, client_secret: str, code: str) -> dict:
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
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
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


# ─── Main ────────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 60)
    print("  F.R.I.D.A.Y.  —  Spotify Auth Setup")
    print("=" * 60)
    print()

    env = _read_env()

    # Step 1: Get Client ID & Secret
    client_id = env.get("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = env.get("SPOTIFY_CLIENT_SECRET", "").strip()

    if not client_id:
        print("📋 Steps to get your Spotify credentials:")
        print("   1. Go to: https://developer.spotify.com/dashboard")
        print("   2. Create a new app (or open existing)")
        print("   3. Add Redirect URI: http://localhost:8888/callback")
        print("   4. Copy Client ID and Client Secret\n")
        client_id = input("   Enter your Spotify CLIENT ID:     ").strip()
        client_secret = input("   Enter your Spotify CLIENT SECRET: ").strip()
        _write_env_key("SPOTIFY_CLIENT_ID", client_id)
        _write_env_key("SPOTIFY_CLIENT_SECRET", client_secret)

    if not client_id or not client_secret:
        print("\n❌ Client ID and Secret are required. Exiting.")
        sys.exit(1)

    # Step 2: Build auth URL and open browser
    auth_params = urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "show_dialog": "true",
    })
    auth_url = f"https://accounts.spotify.com/authorize?{auth_params}"

    print(f"\n🌐 Opening Spotify authorization in your browser...")
    print(f"   URL: {auth_url}\n")
    webbrowser.open(auth_url)

    # Step 3: Start local server to capture callback
    print("⏳ Waiting for authorization callback on http://localhost:8888/callback ...")
    server = HTTPServer(("localhost", 8888), _CallbackHandler)
    server.handle_request()  # handles exactly one request

    if not _auth_code:
        print("\n❌ Authorization failed or was denied. Please try again.")
        sys.exit(1)

    print(f"\n✅ Authorization code received!")

    # Step 4: Exchange code for tokens
    print("🔄 Exchanging code for access + refresh tokens...")
    try:
        tokens = _exchange_code(client_id, client_secret, _auth_code)
    except Exception as e:
        print(f"\n❌ Token exchange failed: {e}")
        sys.exit(1)

    refresh_token = tokens.get("refresh_token", "")
    access_token = tokens.get("access_token", "")

    if not refresh_token:
        print(f"\n❌ No refresh token in response: {tokens}")
        sys.exit(1)

    # Step 5: Save to .env
    print("\n💾 Saving credentials to .env...")
    _write_env_key("SPOTIFY_REFRESH_TOKEN", refresh_token)

    print("\n" + "=" * 60)
    print("  ✅ Setup Complete! F.R.I.D.A.Y. Spotify is ready.")
    print("=" * 60)
    print("\n  Your .env now has:")
    print(f"    SPOTIFY_CLIENT_ID     = {client_id[:8]}...")
    print(f"    SPOTIFY_CLIENT_SECRET = {client_secret[:4]}...")
    print(f"    SPOTIFY_REFRESH_TOKEN = {refresh_token[:16]}...")
    print()
    print("  You can now restart the FRIDAY backend.")
    print("  Spotify song search & play will work via Web API. 🎵\n")


if __name__ == "__main__":
    main()
