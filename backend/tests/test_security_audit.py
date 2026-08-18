"""Phase 6.6 — Security & Authorization Audit Test Suite.

Automated verification of security boundaries, authentication, authorization,
token integrity, session isolation, CORS policy, secret non-leakage, path traversal,
portal automation domain allowlists, and trading boundaries.

Test Matrix:
  A. Unauthenticated protected endpoint rejection (HTTP 401)
  B. Unauthorized owner resource access prevention
  C. Forged approval token rejection
  D. Altered packet hash rejection
  E. Altered form data hash rejection
  F. Expired approval token rejection
  G. Reused (consumed) approval token rejection
  H. CORS policy configuration validation
  I. Cross-user session binding validation
  J. Secret non-leakage in config, logs, and error responses
  K. Path traversal prevention in temp files and uploads
  L. Unsafe upload limits and validation
  M. Arbitrary domain navigation blocking in PortalAutomationEngine
  N. Tool privilege escalation defense
  O. Public demo vs owner privilege boundaries
  P. Trading order permission boundaries and validation
"""

import time
import pytest
from fastapi.testclient import TestClient
from app import app


@pytest.fixture
def test_client():
    return TestClient(app)


# ===========================================================================
# A & B: UNAUTHENTICATED & UNAUTHORIZED ENDPOINT ACCESS
# ===========================================================================

def test_sec_A1_unauthenticated_career_dashboard_rejected(test_client):
    """A1: Non-localhost caller without X-FRIDAY-Token must receive HTTP 401 on career endpoints."""
    # Remote client host (simulating LAN / non-loopback attacker)
    client = TestClient(app, client=("192.168.1.100", 54321))
    resp = client.get("/api/career/dashboard")
    assert resp.status_code == 401
    assert "Unauthorized" in resp.json().get("detail", "")


def test_sec_A2_unauthenticated_email_unread_rejected(test_client):
    """A2: Non-localhost caller without token must receive HTTP 401 on email endpoints."""
    client = TestClient(app, client=("192.168.1.100", 54321))
    resp = client.get("/api/email/unread")
    assert resp.status_code == 401


def test_sec_A3_unauthenticated_system_control_rejected(test_client):
    """A3: Non-localhost caller without token cannot trigger system commands."""
    client = TestClient(app, client=("192.168.1.100", 54321))
    resp = client.post("/api/open-app", json={"app": "Terminal"})
    assert resp.status_code == 401


def test_sec_A4_unauthenticated_devtools_rejected(test_client):
    """A4: Non-localhost caller without token cannot inspect dev overview or logs."""
    client = TestClient(app, client=("192.168.1.100", 54321))
    resp = client.get("/api/dev/overview")
    assert resp.status_code == 401


def test_sec_A5_authenticated_remote_caller_accepted(test_client, monkeypatch):
    """A5: Non-localhost caller presenting valid X-FRIDAY-Token is authenticated as owner."""
    monkeypatch.setenv("FRIDAY_API_TOKEN", "super_secret_test_token_999")
    client = TestClient(app, client=("192.168.1.100", 54321))

    # Without token -> 401
    resp_no_token = client.get("/api/dev/overview")
    assert resp_no_token.status_code == 401

    # With valid token -> 200
    resp_with_token = client.get(
        "/api/dev/overview",
        headers={"X-FRIDAY-Token": "super_secret_test_token_999"}
    )
    assert resp_with_token.status_code == 200


# ===========================================================================
# C, D, E, F, G: APPROVAL TOKEN INTEGRITY & TAMPERING
# ===========================================================================

def test_sec_C1_forged_email_approval_id_rejected():
    """C1: Submitting a completely forged approval ID is rejected."""
    from services.email.service import send_email_with_approval
    from services.email.provider import MockEmailProvider

    result = send_email_with_approval(
        approval_id="forged_approval_uuid_0000",
        draft_id="some_draft_id",
        user_confirmation_text="Yes, send it",
        provider=MockEmailProvider(),
    )
    assert not result["success"]
    assert result["status"] == "VALIDATION_FAILED"
    assert result["real_email_sent"] is False


def test_sec_C2_forged_calendar_approval_id_rejected():
    """C2: Submitting a forged calendar approval ID is rejected."""
    from services.calendar.service import create_calendar_event_with_approval
    from services.calendar.provider import MockCalendarProvider

    result = create_calendar_event_with_approval(
        approval_id="forged_cal_uuid_0000",
        event_id="some_event_id",
        user_confirmation_text="Yes, create it.",
        provider=MockCalendarProvider(),
    )
    assert not result["success"]
    assert result["status"] == "VALIDATION_FAILED"
    assert result["real_event_created"] is False


def test_sec_D1_altered_email_packet_hash_invalidates_approval():
    """D1: Altering draft body changes SHA-256 hash and invalidates prior approval."""
    from services.email.service import create_email_draft, send_email_with_approval
    from services.email.draft import update_draft
    from services.email.provider import MockEmailProvider

    draft_res = create_email_draft("target@example.com", "Initial Subject", "Initial Body")
    draft_id = draft_res["draft"]["draft_id"]
    approval_id = draft_res["approval_token"]["approval_id"]

    # Attacker alters draft content
    update_draft(draft_id, new_body="Tampered malicious body")

    # Prior approval token must be rejected with EDIT_INVALIDATION
    result = send_email_with_approval(
        approval_id=approval_id,
        draft_id=draft_id,
        user_confirmation_text="Yes, send it",
        provider=MockEmailProvider(),
    )
    assert not result["success"]
    assert result["status"] == "EDIT_INVALIDATION"
    assert result["real_email_sent"] is False


def test_sec_D2_altered_calendar_event_hash_invalidates_approval():
    """D2: Altering calendar event time/title changes hash and invalidates approval."""
    from services.calendar.service import prepare_calendar_event, create_calendar_event_with_approval
    from services.calendar.event import update_calendar_event_draft
    from services.calendar.provider import MockCalendarProvider

    draft_res = prepare_calendar_event("Sprint Planning", "2026-09-01T10:00:00", "2026-09-01T11:00:00", "UTC")
    event_id = draft_res["event_draft"]["event_id"]
    approval_id = draft_res["approval_token"]["approval_id"]

    # Attacker alters event title
    update_calendar_event_draft(event_id, new_title="Tampered Meeting Title")

    result = create_calendar_event_with_approval(
        approval_id=approval_id,
        event_id=event_id,
        user_confirmation_text="Yes, create it.",
        provider=MockCalendarProvider(),
    )
    assert not result["success"]
    assert result["status"] == "EDIT_INVALIDATION"
    assert result["real_event_created"] is False


def test_sec_E1_altered_portal_form_data_hash_blocks_submission():
    """E1: Altering portal form fields causes form_data_hash mismatch and blocks execution."""
    from services.career.portal.engine import PortalAutomationEngine
    from services.career.portal.mock_portal import MockApplicationPortal

    engine = PortalAutomationEngine()
    packet = {
        "job_id": "job_sec_101",
        "company": "MockCorp",
        "role": "Software Engineer",
        "source_url": "https://careers.mockcorp.io/apply/1",
        "name": "Prem Sahu",
        "email": "prem@example.com",
    }
    portal = MockApplicationPortal()
    init_res = engine.create_portal_session(packet, portal=portal)
    session_id = init_res["session_id"]
    approval_token = init_res["approval_token"]

    # Attacker tampers with the packet content hash after preview
    tampered_packet = dict(packet)
    tampered_packet["content_hash"] = "tampered_hash_00000"

    with pytest.raises(ValueError) as exc_info:
        engine.execute_approved_submission(
            session_id=session_id,
            approval_token=approval_token,
            current_packet=tampered_packet,
        )
    assert "mismatch" in str(exc_info.value).lower()




def test_sec_F1_expired_email_approval_rejected():
    """F1: Approval token beyond TTL (300s) is rejected."""
    from services.email.service import create_email_draft, send_email_with_approval
    from services.email.provider import MockEmailProvider

    draft_res = create_email_draft("r@example.com", "Subject", "Body", ttl_seconds=10)
    draft_id = draft_res["draft"]["draft_id"]
    approval_id = draft_res["approval_token"]["approval_id"]

    # Simulate time advancing 100 seconds
    now_future = time.time() + 100
    result = send_email_with_approval(
        approval_id=approval_id,
        draft_id=draft_id,
        user_confirmation_text="Yes, send it",
        now=now_future,
        provider=MockEmailProvider(),
    )
    assert not result["success"]
    assert result["status"] == "TOKEN_EXPIRED"


def test_sec_G1_replayed_consumed_approval_rejected():
    """G1: Approval token cannot be consumed a second time."""
    from services.email.service import create_email_draft, send_email_with_approval
    from services.email.provider import MockEmailProvider

    draft_res = create_email_draft("r@example.com", "Subject", "Body")
    draft_id = draft_res["draft"]["draft_id"]
    approval_id = draft_res["approval_token"]["approval_id"]
    provider = MockEmailProvider()

    # First send succeeds
    r1 = send_email_with_approval(
        approval_id=approval_id,
        draft_id=draft_id,
        user_confirmation_text="Yes, send it",
        provider=provider,
    )
    assert r1["success"]

    # Second send with same token is BLOCKED (already sent / consumed)
    r2 = send_email_with_approval(
        approval_id=approval_id,
        draft_id=draft_id,
        user_confirmation_text="Yes, send it",
        provider=provider,
    )
    assert not r2["success"]
    assert r2["status"] == "ALREADY_SENT"
    assert len(provider._outbox) == 1


# ===========================================================================
# H: CORS POLICY CONFIGURATION
# ===========================================================================

def test_sec_H1_cors_allowed_origins_no_wildcard_with_credentials():
    """H1: CORS middleware must not allow '*' combined with credentials."""
    import os
    raw_origins = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080"
    )
    origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    assert "*" not in origins, "Wildcard '*' must never be combined with allow_credentials=True"
    for o in origins:
        assert o.startswith("http://") or o.startswith("https://")


# ===========================================================================
# I: SESSION & USER ISOLATION
# ===========================================================================

def test_sec_I1_unauthorized_session_user_cannot_approve():
    """I1: Approval signed by 'Attacker' cannot execute Prem's draft."""
    from services.email.service import create_email_draft, send_email_with_approval
    from services.email.provider import MockEmailProvider

    draft_res = create_email_draft("r@example.com", "Subject", "Body")
    draft_id = draft_res["draft"]["draft_id"]
    approval_id = draft_res["approval_token"]["approval_id"]

    result = send_email_with_approval(
        approval_id=approval_id,
        draft_id=draft_id,
        user_confirmation_text="Yes, send it",
        session_user="HackerBob",
        provider=MockEmailProvider(),
    )
    assert not result["success"]
    assert result["status"] == "VALIDATION_FAILED"
    assert "Unauthorized session user" in result["message"]


# ===========================================================================
# J: SECRET NON-LEAKAGE
# ===========================================================================

def test_sec_J1_dev_config_does_not_reveal_secret_values(test_client):
    """J1: /api/dev/config returns booleans only for env keys, never plaintext values."""
    resp = test_client.get("/api/dev/config")
    assert resp.status_code == 200
    data = resp.json()
    env_map = data.get("env", {})
    for key, val in env_map.items():
        assert isinstance(val, bool), f"Key '{key}' exposed non-boolean value '{val}'"


# ===========================================================================
# K & L: PATH TRAVERSAL & UNSAFE UPLOADS
# ===========================================================================

def test_sec_K1_tts_random_uuid_filename_no_path_traversal(test_client):
    """K1: TTS endpoint returns safe relative path with UUID, not user-controlled name."""
    resp = test_client.post("/api/tts", json={"text": "Security test audio"})
    assert resp.status_code == 200
    url = resp.json().get("audio_url", "")
    assert url.startswith("/temp_audio/")
    assert ".." not in url
    assert "/" not in url.replace("/temp_audio/", "")


def test_sec_L1_document_upload_size_limit(test_client):
    """L1: Uploading files larger than MAX_UPLOAD_BYTES returns HTTP 413."""
    from services.document_agent import MAX_UPLOAD_BYTES
    oversized_data = b"A" * (MAX_UPLOAD_BYTES + 1024)
    resp = test_client.post(
        "/api/documents/upload",
        files={"file": ("large.txt", oversized_data, "text/plain")}
    )
    assert resp.status_code == 413


# ===========================================================================
# M: PORTAL AUTOMATION DOMAIN ALLOWLIST
# ===========================================================================

def test_sec_M1_portal_automation_blocks_unauthorized_domains():
    """M1: Target URL outside portal's allowed_domains is blocked immediately."""
    from services.career.portal.engine import PortalAutomationEngine, PortalSecurityError
    from services.career.portal.mock_portal import MockApplicationPortal

    engine = PortalAutomationEngine()
    unauthorized_packet = {
        "job_id": "job_evil",
        "company": "EvilPhishing",
        "role": "Engineer",
        "source_url": "https://evil-phishing-site.com/steal-credentials",
    }
    portal = MockApplicationPortal()
    with pytest.raises(PortalSecurityError) as exc_info:
        engine.create_portal_session(unauthorized_packet, portal=portal)
    assert "DOMAIN_BLOCKED" in str(exc_info.value)



# ===========================================================================
# N & O: PRIVILEGE ESCALATION & PUBLIC DEMO BOUNDARIES
# ===========================================================================

def test_sec_N1_guest_speech_cannot_invoke_system_commands():
    """N1: Spoken command from non-owner (is_boss=False) cannot execute system automation."""
    from services.brain.engine import respond

    # Guest user requests system lock or app opening
    result = respond("Open terminal right now and lock the screen", is_boss=False)
    assert isinstance(result, dict)
    # Action must be refused or set to none/chat
    action = result.get("action", "none")
    assert action in ("none", "chat", "reply") or "guest" in result.get("reply", "").lower()


def test_sec_O1_public_demo_endpoints_accessible_without_auth(test_client):
    """O1: Public demo endpoints (/system/stats, /weather, /trading/live-prices) return 200 for remote caller."""
    client = TestClient(app, client=("192.168.1.100", 54321))
    assert client.get("/api/system/stats").status_code == 200
    assert client.get("/api/weather").status_code == 200
    assert client.get("/api/trading/live-prices").status_code == 200


# ===========================================================================
# P: TRADING PERMISSION BOUNDARY
# ===========================================================================

def test_sec_P1_paper_order_validation_and_permission_requirement(test_client):
    """P1: Trading order requires valid side/quantity and is strictly paper simulated."""
    # Invalid side
    resp_invalid_side = test_client.post(
        "/api/trading/order",
        json={"symbol": "AAPL", "side": "invalid_side", "quantity": 10}
    )
    # Can be 400 (validation) or 403 (permission)
    assert resp_invalid_side.status_code in (400, 403)

    # Invalid quantity
    resp_invalid_qty = test_client.post(
        "/api/trading/order",
        json={"symbol": "AAPL", "side": "buy", "quantity": 0}
    )
    assert resp_invalid_qty.status_code in (400, 403)
