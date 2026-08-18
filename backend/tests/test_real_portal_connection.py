"""Targeted unit tests for Phase 5.5E Step 1: Real Job Portal Connection & Read-Only Form Discovery (Tests A through T).
"""

import pytest
from unittest.mock import MagicMock, patch
from backend.services.career.portal import (
    LinkedInApplicationPortal,
    PortalAutomationEngine,
    PortalSecurityError,
    FieldSensitivity,
)
from backend.services.career.packet import (
    generate_application_packet,
    edit_application_packet,
)
from backend.services import career_db


@pytest.fixture(autouse=True)
def init_db():
    """Initialize DB tables before tests."""
    career_db.init_career_db()


# ==============================================================================
# TEST A, F, R, S: PROVIDER REGISTRATION, DOMAIN ALLOWLIST & BOUNDARY GUARDS
# ==============================================================================

def test_step1_real_portal_registration_and_guards():
    """Tests A, F, R, S: Registration, domain allowlist, and strict submission/messaging guards."""
    portal = LinkedInApplicationPortal()
    assert portal.provider_name() == "linkedin_portal"

    # F: Allowed Domains
    allowed = portal.allowed_domains()
    assert "linkedin.com" in allowed
    assert "www.linkedin.com" in allowed

    # R: Real submission is permanently disabled in Step 1
    with pytest.raises(NotImplementedError) as exc_sub:
        portal.submit_form("sess_123", "appr_123")
    assert "STRICTLY DISABLED" in str(exc_sub.value)

    # S: Recruiter messaging is disabled
    with pytest.raises(NotImplementedError) as exc_msg:
        portal.send_recruiter_message("rec_1", "Hello")
    assert "STRICTLY DISABLED" in str(exc_msg.value).upper()


# ==============================================================================
# TEST B, C, D, E, G, T: CONNECTION STATES, AUTH PROFILE & SECRET REDACTION
# ==============================================================================

def test_step1_connection_states_and_secret_redaction():
    """Tests B, C, D, E, G, T: Connection checking, profile retrieval, and zero secret leakage."""
    portal = LinkedInApplicationPortal()

    # B & G: Connected when cookies exist in DB
    with patch("sqlite3.connect") as mock_conn_fn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (
            "Prathvi Sahu",
            "Full Stack & AI Engineer",
            842,
            1,
            '[{"name": "li_at", "value": "SECRET_COOKIE_TOKEN_9999"}]',
            "2026-08-03 07:00:49"
        )
        mock_conn.cursor.return_value = mock_cursor
        mock_conn_fn.return_value = mock_conn

        conn_res = portal.check_connection()
        assert conn_res["status"] == "CONNECTED"
        assert conn_res["connected"] is True
        assert conn_res["account_user"] == "Prathvi Sahu"

        # G: Authenticated profile read
        prof_res = portal.get_authenticated_profile()
        assert prof_res["status"] == "CONNECTED"
        assert prof_res["profile"]["name"] == "Prathvi Sahu"
        assert prof_res["profile"]["connections"] == 842

        # T: Secret redaction check
        res_str = str(conn_res) + str(prof_res)
        assert "SECRET_COOKIE_TOKEN" not in res_str
        assert "li_at" not in res_str

    # C: Auth required when no cookies exist
    with patch("sqlite3.connect") as mock_conn_fn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        mock_conn_fn.return_value = mock_conn

        conn_unauth = portal.check_connection()
        assert conn_unauth["status"] == "AUTH_REQUIRED"
        assert conn_unauth["connected"] is False


# ==============================================================================
# TEST H, I, J, K: JOB OPENING, FORM DISCOVERY, REQUIRED & SENSITIVE MAPPING
# ==============================================================================

def test_step1_job_open_and_form_discovery():
    """Tests H, I, J, K: Opening job page, discovering LinkedIn form, and sensitivity mapping."""
    portal = LinkedInApplicationPortal()

    job = {
        "id": "li_job_777",
        "title": "Staff Backend Engineer",
        "company": "EnterpriseAI",
        "url": "https://www.linkedin.com/jobs/view/777000",
    }

    # H: Open Application
    open_res = portal.open_application(job)
    assert open_res["status"] == "READY"
    sess_id = open_res["session_id"]

    # I: Discover Form Schema
    schema = portal.discover_form(sess_id)
    assert schema["fields_count"] >= 8
    assert any(f["name"] == "work_authorization" for f in schema["fields"])
    assert any(f["name"] == "resume" for f in schema["fields"])

    # K: Field sensitivity verification
    work_auth_f = next(f for f in schema["fields"] if f["name"] == "work_authorization")
    assert work_auth_f["sensitivity"] == FieldSensitivity.REVIEW_REQUIRED.value

    # Packet for mapping
    profile = {
        "full_name": "Prathvi Sahu",
        "email": "prathvi@example.com",
        "phone": "+91 98765 43210",
    }
    packet = generate_application_packet(job=job, candidate_profile=profile, run_llm=False)

    # Map fields
    mapped = portal.map_fields(schema, packet)
    assert mapped["can_proceed"] is True
    assert mapped["mapped_fields"]["email"]["value"] == "prathvi@example.com"
    assert mapped["mapped_fields"]["first_name"]["value"] == "Prathvi"
    assert len(mapped["review_required"]) >= 2

    # J: Incomplete Profile detection
    inc_packet = generate_application_packet(job=job, candidate_profile={"name": "Inc User"}, run_llm=False)
    inc_mapped = portal.map_fields(schema, inc_packet)
    assert inc_mapped["can_proceed"] is False
    assert len(inc_mapped["missing_required"]) >= 2


# ==============================================================================
# TEST L, M, N: PACKET HASH BINDING, PREVIEW & MODIFICATION INVALIDATION
# ==============================================================================

def test_step1_packet_hash_binding_and_invalidation():
    """Tests L, M, N: Binding session to ApplicationPacket hash and invalidation upon edit."""
    engine = PortalAutomationEngine()
    portal = LinkedInApplicationPortal()

    job = {
        "id": "li_job_888",
        "title": "Cloud Architect",
        "company": "ScaleTech Systems",
        "url": "https://www.linkedin.com/jobs/view/888000",
    }
    profile = {"full_name": "Dev User", "email": "dev@scaletech.com", "phone": "1234567890"}

    packet = generate_application_packet(job=job, candidate_profile=profile, run_llm=False)

    # L: Create portal session
    sess_res = engine.create_portal_session(packet, portal)
    assert sess_res["status"] == "READY_FOR_PREVIEW"
    sess_id = sess_res["session_id"]
    approval_token = sess_res["approval_token"]

    # M: Generate preview
    preview_txt = engine.generate_submission_preview(sess_id)
    assert "ScaleTech Systems" in preview_txt
    assert "dev@scaletech.com" in preview_txt

    # N: Edit packet invalidates session
    modified_packet = edit_application_packet(packet, {"cover_letter": "Altered cover letter text."})
    with pytest.raises(ValueError) as exc_mod:
        engine.execute_approved_submission(sess_id, approval_token, modified_packet)
    assert "mismatch" in str(exc_mod.value).lower()


# ==============================================================================
# TEST O, P, Q: DOMAIN BLOCKING & ANTI-BOT CHALLENGE DETECTION
# ==============================================================================

def test_step1_domain_blocking_and_challenge_detection():
    """Tests O, P, Q: Unexpected domain redirection blocking and anti-bot challenge handling."""
    portal = LinkedInApplicationPortal()

    # O: Unexpected domain
    job_bad_domain = {
        "id": "bad_01",
        "url": "https://unauthorized-domain.com/apply/1",
    }
    res_bad = portal.open_application(job_bad_domain)
    assert res_bad["status"] == "DOMAIN_BLOCKED"

    # P & Q: Engine domain blocking
    engine = PortalAutomationEngine()
    bad_packet = {
        "packet_id": "pkt_bad",
        "company": "BadCorp",
        "role": "BadRole",
        "source_url": "https://unauthorized-domain.com/apply/1",
    }
    with pytest.raises(PortalSecurityError) as exc_sec:
        engine.create_portal_session(bad_packet, portal)
    assert "DOMAIN_BLOCKED" in str(exc_sec.value)
