"""auth.py — Owner authentication for FRIDAY.

FRIDAY is a single-owner personal assistant that runs on the owner's machine.

Trust model:
  * Requests arriving from the same machine (loopback / localhost) are treated
    as the owner ("boss"). The macOS browser frontend talks to the backend
    through the Vite dev proxy, which connects from 127.0.0.1.
  * Requests arriving from any OTHER address (e.g. a neighbour on the LAN
    hitting the 0.0.0.0-bound uvicorn) must present the `FRIDAY_API_TOKEN`
    configured in backend/.env via the `X-FRIDAY-Token` header, otherwise they
    are rejected with HTTP 401.

This replaces the previous design where the HTTP client could declare itself
the boss by sending `is_boss: true` in the request body — anyone on the
network could impersonate the owner.

NOTE: the server MUST run with uvicorn `--no-proxy-headers` (see app.py /
start.sh). Uvicorn's default proxy-headers mode rewrites `request.client`
from client-supplied `X-Forwarded-For` / `X-Real-IP`, which would let a
remote attacker spoof `127.0.0.1` and bypass this check.
"""

import os
import secrets

from fastapi import Request, HTTPException

# Hosts treated as "the machine itself". "testclient"/"testserver" are the
# hostnames used by FastAPI's TestClient so tests can exercise owner paths.
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient", "testserver"}


def get_api_token() -> str:
    """Return the configured FRIDAY_API_TOKEN (empty string when unset)."""
    return (os.getenv("FRIDAY_API_TOKEN") or "").strip()


def is_loopback_host(host: str | None) -> bool:
    """True when `host` refers to the local machine."""
    if not host:
        return False
    h = host.lower()
    if h in LOOPBACK_HOSTS:
        return True
    # IPv4-mapped IPv6 loopback, e.g. ::ffff:127.0.0.1
    if h.startswith("::ffff:"):
        return h.rsplit(":", 1)[-1] in {"127.0.0.1", "localhost"}
    return False


def is_boss_request(request: Request) -> bool:
    """Owner check: loopback client, FRIDAY_MODE=demo, or a valid FRIDAY_API_TOKEN bearer."""
    if os.getenv("FRIDAY_MODE", "").strip().lower() == "demo":
        return True
    host = request.client.host if request.client else ""
    if is_loopback_host(host):
        return True
    token = get_api_token()
    if token:
        provided = request.headers.get("X-FRIDAY-Token") or ""
        if provided and secrets.compare_digest(provided, token):
            return True
    return False


def require_boss(request: Request) -> None:
    """FastAPI dependency: 401 unless the caller is the owner.

    Attach to any route that controls the machine, reads personal data, or
    spends API credits (chat, system control, career profile, ...).
    """
    if not is_boss_request(request):
        raise HTTPException(
            status_code=401,
            detail=(
                "Unauthorized. FRIDAY only answers its owner: access from "
                "localhost, or set FRIDAY_API_TOKEN in backend/.env and send "
                "it as the X-FRIDAY-Token header."
            ),
        )
