"""Phase 6.6A — Security Remediation Regression Test Suite.

Verifies remediation of findings SEC-001 through SEC-005:
  SEC-001: Elimination of FRIDAY_MODE=demo owner authentication bypass
  SEC-002: Restricted Spotify mutation endpoints (/seek, /duck, /unduck) to require_boss
  SEC-003: Masking of sensitive profile fields in /api/career/profile (no plaintext secret leakage)
  SEC-004: Cross-origin state-changing request protection (CSRF / Origin validation)
  SEC-005: Thread-safe bounded pruning of expired presence approvals
"""

import os
import time
import pytest
from fastapi.testclient import TestClient
from app import app


@pytest.fixture
def test_client():
    return TestClient(app)


# ===========================================================================
# SEC-001: FRIDAY_MODE=demo OWNER AUTH BYPASS REMEDIATION
# ===========================================================================

def test_sec001_demo_mode_anonymous_caller_rejected(monkeypatch):
    """1. In demo mode, an anonymous non-localhost caller must receive HTTP 401 on owner routes."""
    monkeypatch.setenv("FRIDAY_MODE", "demo")
    monkeypatch.setenv("FRIDAY_API_TOKEN", "prod_secret_token_123")
    client = TestClient(app, client=("198.51.100.25", 43210))

    resp = client.get("/api/career/dashboard")
    assert resp.status_code == 401
    assert "Unauthorized" in resp.json().get("detail", "")

    resp_sys = client.post("/api/open-app", json={"app": "Terminal"})
    assert resp_sys.status_code == 401


def test_sec001_demo_mode_invalid_token_rejected(monkeypatch):
    """2. In demo mode, a non-localhost caller with an invalid token is rejected with 401."""
    monkeypatch.setenv("FRIDAY_MODE", "demo")
    monkeypatch.setenv("FRIDAY_API_TOKEN", "prod_secret_token_123")
    client = TestClient(app, client=("198.51.100.25", 43210))

    resp = client.get(
        "/api/dev/overview",
        headers={"X-FRIDAY-Token": "invalid_forged_token"}
    )
    assert resp.status_code == 401


def test_sec001_demo_mode_valid_token_accepted(monkeypatch):
    """3. In demo mode, a non-localhost caller with a VALID token is accepted with 200."""
    monkeypatch.setenv("FRIDAY_MODE", "demo")
    monkeypatch.setenv("FRIDAY_API_TOKEN", "prod_secret_token_123")
    client = TestClient(app, client=("198.51.100.25", 43210))

    resp = client.get(
        "/api/dev/overview",
        headers={"X-FRIDAY-Token": "prod_secret_token_123"}
    )
    assert resp.status_code == 200


def test_sec001_demo_mode_public_route_remains_accessible(monkeypatch):
    """4. In demo mode, public routes (/system/stats, /weather) remain accessible to anonymous callers."""
    monkeypatch.setenv("FRIDAY_MODE", "demo")
    client = TestClient(app, client=("198.51.100.25", 43210))

    resp_stats = client.get("/api/system/stats")
    assert resp_stats.status_code == 200

    resp_weather = client.get("/api/weather")
    assert resp_weather.status_code == 200


# ===========================================================================
# SEC-002: PUBLIC SPOTIFY STATE MUTATION REMEDIATION
# ===========================================================================

def test_sec002_anonymous_spotify_seek_blocked():
    """Anonymous remote caller cannot seek Spotify playback."""
    client = TestClient(app, client=("198.51.100.25", 43210))
    resp = client.post("/api/spotify/seek", json={"seconds": 45.0})
    assert resp.status_code == 401


def test_sec002_anonymous_spotify_duck_blocked():
    """Anonymous remote caller cannot duck Spotify volume."""
    client = TestClient(app, client=("198.51.100.25", 43210))
    resp = client.post("/api/spotify/duck")
    assert resp.status_code == 401


def test_sec002_anonymous_spotify_unduck_blocked():
    """Anonymous remote caller cannot unduck Spotify volume."""
    client = TestClient(app, client=("198.51.100.25", 43210))
    resp = client.post("/api/spotify/unduck")
    assert resp.status_code == 401


def test_sec002_spotify_current_track_remains_public():
    """GET /api/spotify/current-track remains readable by public demo callers."""
    client = TestClient(app, client=("198.51.100.25", 43210))
    resp = client.get("/api/spotify/current-track")
    assert resp.status_code == 200


# ===========================================================================
# SEC-003: PLAINTEXT CAREER PROFILE SECRET EXPOSURE REMEDIATION
# ===========================================================================

def test_sec003_career_profile_masks_sensitive_values_over_api(test_client):
    """GET /api/career/profile must NOT expose plaintext passwords or API keys."""
    from services.career_db import upsert_profile_field

    # Upsert a sensitive credential into vault
    upsert_profile_field("linkedin_password", "SuperSecretPassword987!", is_sensitive=True)
    upsert_profile_field("candidate_name", "Prem Sahu", is_sensitive=False)

    resp = test_client.get("/api/career/profile")
    assert resp.status_code == 200
    data = resp.json()["profile"]

    # Sensitive field must NOT contain plaintext password
    pw_field = data.get("linkedin_password", {})
    assert pw_field.get("value") != "SuperSecretPassword987!"
    assert pw_field.get("value") == "••••••••"
    assert pw_field.get("is_set") is True
    assert pw_field.get("sensitive") is True

    # Non-sensitive field retains value
    name_field = data.get("candidate_name", {})
    assert name_field.get("value") == "Prem Sahu"


def test_sec003_backend_internal_access_retains_decrypted_values():
    """Internal backend callers can still decrypt credentials via get_profile(mask_sensitive=False)."""
    from services.career_db import upsert_profile_field, get_profile

    upsert_profile_field("smtp_password", "MySmtpPass2026#", is_sensitive=True)

    # Internal call with mask_sensitive=False
    internal_profile = get_profile(mask_sensitive=False)
    assert internal_profile["smtp_password"]["value"] == "MySmtpPass2026#"
    assert internal_profile["smtp_password"]["is_set"] is True


# ===========================================================================
# SEC-004: LOCALHOST CROSS-ORIGIN STATE-CHANGING REQUEST PROTECTION
# ===========================================================================

def test_sec004_allowed_same_origin_state_changing_request_succeeds(test_client):
    """1. State-changing POST with allowed Origin (e.g. http://localhost:5173) is accepted."""
    resp = test_client.post(
        "/api/tts",
        json={"text": "Test speech"},
        headers={"Origin": "http://localhost:5173"}
    )
    assert resp.status_code == 200


def test_sec004_malicious_cross_origin_request_blocked(test_client):
    """2. State-changing POST with untrusted Origin (http://evil-hacker.com) is blocked (403)."""
    resp = test_client.post(
        "/api/tts",
        json={"text": "Evil cross-site attack"},
        headers={"Origin": "http://evil-hacker.com"}
    )
    assert resp.status_code == 403
    assert "Cross-origin state-changing request blocked" in resp.json().get("detail", "")


def test_sec004_missing_origin_non_browser_request_allowed(test_client):
    """3. Non-browser client request (no Origin header) passes cross-origin check."""
    resp = test_client.post(
        "/api/tts",
        json={"text": "Direct non-browser call"}
    )
    assert resp.status_code == 200


def test_sec004_valid_owner_token_cross_origin_request_accepted(test_client, monkeypatch):
    """4. External request with valid X-FRIDAY-Token is accepted even if Origin is unfamiliar."""
    monkeypatch.setenv("FRIDAY_API_TOKEN", "valid_secret_token_abc")
    resp = test_client.post(
        "/api/tts",
        json={"text": "Authorized cross-origin call"},
        headers={
            "Origin": "https://trusted-remote-client.app",
            "X-FRIDAY-Token": "valid_secret_token_abc",
        }
    )
    assert resp.status_code == 200


def test_sec004_preflight_options_passes_through(test_client):
    """5. Preflight OPTIONS requests are handled by CORS middleware without 403 blocking."""
    resp = test_client.options(
        "/api/chat/text",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        }
    )
    assert resp.status_code == 200


# ===========================================================================
# SEC-005: PRESENCE APPROVAL EXPIRATION PRUNING
# ===========================================================================

def test_sec005_presence_expired_approvals_pruned():
    """Expired presence approval tokens are cleanly pruned from memory."""
    from services.presence import _PENDING, create_approval, _prune_expired

    res = create_approval("system.control", "Test command", push=False)
    token = res["approval_token"]
    assert token in _PENDING

    # Artificially expire the token
    _PENDING[token]["expires_at"] = time.time() - 10

    # Pruning removes it
    _prune_expired()
    assert token not in _PENDING
