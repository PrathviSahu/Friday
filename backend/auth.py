"""auth.py — Owner authentication for FRIDAY.

FRIDAY is a single-owner personal assistant that runs either locally on the owner's
machine or deployed to cloud hosting (e.g. Render / Cloud Run / VPS).

Trust model:
  * LOCAL DEVELOPMENT (RENDER / ENVIRONMENT != production):
      Requests arriving from loopback (127.0.0.1 / ::1 / localhost / testclient)
      are treated as the owner ("boss").
  * PRODUCTION DEPLOYMENT (RENDER=true or ENVIRONMENT=production):
      Reverse proxies (like Render, Cloudflare, Nginx) route external requests to
      the application container over a local loopback bridge (127.0.0.1).
      Therefore, in production, client IP is NEVER trusted for owner identity.
      ALL owner-level requests MUST present a valid `FRIDAY_API_TOKEN` via the
      `X-FRIDAY-Token` HTTP header, compared in constant time.
"""

import os
import secrets
from fastapi import Request, HTTPException

# Hosts treated as "the machine itself" in local development.
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient", "testserver"}


def is_production_environment() -> bool:
    """Return True if running in a cloud hosting or production environment."""
    return (
        os.getenv("RENDER", "").lower() in ("true", "1")
        or os.getenv("ENVIRONMENT", "").lower() in ("production", "prod")
        or os.getenv("FRIDAY_DEPLOYED", "").lower() in ("true", "1")
        or os.getenv("FRIDAY_ENVIRONMENT", "").lower() in ("production", "prod")
    )


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
    """Owner check: constant-time token verification in production, loopback in local dev."""
    token = get_api_token()
    provided = request.headers.get("X-FRIDAY-Token") or ""

    # Valid token bearer is always authorized (local and production)
    if token and provided and secrets.compare_digest(provided, token):
        return True

    # In production/cloud environments, NEVER trust client IP or loopback bridge
    if is_production_environment():
        return False

    # In local development, allow loopback connections
    host = request.client.host if request.client else ""
    return is_loopback_host(host)


def require_boss(request: Request) -> None:
    """FastAPI dependency: 401 unless the caller is the authenticated owner."""
    if not is_boss_request(request):
        if is_production_environment():
            raise HTTPException(
                status_code=401,
                detail="Unauthorized. Production access requires a valid X-FRIDAY-Token header.",
            )
        raise HTTPException(
            status_code=401,
            detail=(
                "Unauthorized. This operation requires owner authentication: access from "
                "localhost, or provide FRIDAY_API_TOKEN via the X-FRIDAY-Token header."
            ),
        )


def require_public_demo(request: Request) -> None:
    """FastAPI dependency for public recruiter showcase endpoints.

    Allows public visitors and recruiters to interact with F.R.I.D.A.Y.'s Voice AI,
    Career OS, Trading Workstation, and ATS analysis without needing a master token.
    Endpoints using this dependency are protected by IP-based rate limiting.
    """
    return None
