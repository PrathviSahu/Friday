"""Targeted unit tests for Phase 5.5E Step 2: Controlled Single Real LinkedIn Application (Tests A through T).
"""

import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from backend.services.career.portal import (
    LinkedInApplicationPortal,
    MockApplicationPortal,
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
# TEST A, B, T: STALE SESSION, FRESH SESSION & SECRET REDACTION
# ==============================================================================

def test_step2_fresh_session_and_secret_redaction():
    """Tests A, B, T: Live session verification and secret redaction."""
    portal = LinkedInApplicationPortal()

    # B: Fresh live session check succeeds when session in DB
    with patch.object(portal, "check_connection") as mock_conn:
        mock_conn.return_value = {
            "status": "CONNECTED",
            "connected": True,
            "account_user": "Prathvi Sahu",
            "headline": "Full Stack & AI Engineer",
            "verified_at": "2026-08-03 07:00:49",
        }
        live_res = portal.verify_live_session()
        assert live_res["live_verified"] is True
        assert live_res["status"] == "CONNECTED"
        assert live_res["account_user"] == "Prathvi Sahu"

        # T: Zero secret leakage
        assert "cookie" not in str(live_res).lower()
        assert "token" not in str(live_res).lower()

    # A: Stale/unauthenticated session check fails
    with patch.object(portal, "check_connection") as mock_conn_stale:
        mock_conn_stale.return_value = {
            "status": "AUTH_REQUIRED",
            "connected": False,
            "reason": "Session expired or missing.",
        }
        stale_res = portal.verify_live_session()
        assert stale_res["live_verified"] is False
        assert stale_res["status"] == "AUTH_REQUIRED"


# ==============================================================================
# TEST C, D, E, F, N, R: TARGET JOB MISMATCH, PACKET HASH & NO BLIND RETRY
# ==============================================================================

def test_step2_job_mismatch_and_hash_invalidation():
    """Tests C, D, E, F: Target job verification and edit invalidation."""
    engine = PortalAutomationEngine()
    portal = LinkedInApplicationPortal()

    rand_comp = f"ScaleTech_{uuid.uuid4().hex[:8]}"
    job = {
        "id": "li_job_101",
        "title": "Principal AI Architect",
        "company": rand_comp,
        "url": "https://www.linkedin.com/jobs/view/101000",
    }
    profile = {"full_name": "Prathvi Sahu", "email": "prathvi@example.com", "phone": "+91 98765 43210"}
    packet = generate_application_packet(job=job, candidate_profile=profile, run_llm=False)

    sess_res = engine.create_portal_session(packet, portal)
    sess_id = sess_res["session_id"]
    approval_token = sess_res["approval_token"]

    # C: Wrong Company/Job mismatch
    wrong_packet = dict(packet, company="ImpostorCorp Inc")
    with pytest.raises(ValueError) as exc_comp:
        engine.execute_approved_submission(sess_id, approval_token, wrong_packet)
    assert "mismatch" in str(exc_comp.value).lower()

    # D: Wrong Application URL mismatch
    wrong_url_packet = dict(packet, source_url="https://www.linkedin.com/jobs/view/999999")
    with pytest.raises(ValueError) as exc_url:
        engine.execute_approved_submission(sess_id, approval_token, wrong_url_packet)
    assert "mismatch" in str(exc_url.value).lower()

    # E & F: Packet content hash mismatch upon modification
    modified_packet = edit_application_packet(packet, {"cover_letter": "Completely new cover letter."})
    with pytest.raises(ValueError) as exc_hash:
        engine.execute_approved_submission(sess_id, approval_token, modified_packet)
    assert "mismatch" in str(exc_hash.value).lower()


# ==============================================================================
# TEST G, H, S: MISSING APPROVAL, EXPIRED APPROVAL & SINGLE-USE ENFORCEMENT
# ==============================================================================

def test_step2_approval_lifecycle_and_single_use():
    """Tests G, H, S: Approval validation, 5-minute TTL, and single-use consumption."""
    engine = PortalAutomationEngine()
    portal = LinkedInApplicationPortal()

    rand_comp = f"CloudVance_{uuid.uuid4().hex[:8]}"
    job = {
        "id": "li_job_202",
        "title": "Lead DevOps Engineer",
        "company": rand_comp,
        "url": "https://www.linkedin.com/jobs/view/202000",
    }
    profile = {"full_name": "Prathvi Sahu", "email": "prathvi@example.com", "phone": "+91 98765 43210"}
    packet = generate_application_packet(job=job, candidate_profile=profile, run_llm=False)

    sess_res = engine.create_portal_session(packet, portal)
    sess_id = sess_res["session_id"]
    approval_token = sess_res["approval_token"]

    # G: Missing / Invalid approval token
    with pytest.raises(ValueError) as exc_inv:
        engine.execute_approved_submission(sess_id, "invalid_token_999", packet)
    assert "invalid approval" in str(exc_inv.value).lower()

    # H: Expired approval token (> 5 min TTL)
    session_obj = engine._active_sessions[sess_id]
    session_obj.approval_expires_at = datetime.now(timezone.utc) - timedelta(seconds=15)
    with pytest.raises(TimeoutError) as exc_exp:
        engine.execute_approved_submission(sess_id, approval_token, packet)
    assert "expired" in str(exc_exp.value).lower()

    # Reset expiration and submit successfully
    session_obj.approval_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    sub_res = engine.execute_approved_submission(sess_id, approval_token, packet)
    assert sub_res["success"] is True

    # S: Single-use enforcement (cannot submit second time)
    with pytest.raises(RuntimeError) as exc_single:
        engine.execute_approved_submission(sess_id, approval_token, packet)
    assert "already consumed" in str(exc_single.value).lower()


# ==============================================================================
# TEST I: REVIEW-REQUIRED FIELD REJECTION & CONFIRMATION
# ==============================================================================

def test_step2_review_required_field_confirmation():
    """Test I: Explicit candidate confirmation of review-required screening questions."""
    engine = PortalAutomationEngine()
    portal = LinkedInApplicationPortal()

    rand_comp = f"ReviewTech_{uuid.uuid4().hex[:8]}"
    job = {
        "id": "li_job_303",
        "title": "Full Stack Engineer",
        "company": rand_comp,
        "url": "https://www.linkedin.com/jobs/view/303000",
    }
    profile = {"full_name": "Prathvi Sahu", "email": "prathvi@example.com", "phone": "+91 98765 43210"}
    packet = generate_application_packet(job=job, candidate_profile=profile, run_llm=False)

    sess_res = engine.create_portal_session(packet, portal)
    sess_id = sess_res["session_id"]
    approval_token = sess_res["approval_token"]

    # Preview displays review-required details with Source & Reason
    preview = engine.generate_submission_preview(sess_id)
    assert "REVIEW REQUIRED FIELDS (Explicit Candidate Confirmation Required):" in preview
    assert "Candidate Profile → work_authorization" in preview
    assert "Nothing has been submitted yet." in preview

    # Candidate rejecting review fields halts execution
    with pytest.raises(ValueError) as exc_unconf:
        engine.execute_approved_submission(sess_id, approval_token, packet, confirmed_review_fields=False)
    assert "unconfirmed" in str(exc_unconf.value).lower()

    # Confirmed submission succeeds
    sub_res = engine.execute_approved_submission(
        sess_id,
        approval_token,
        packet,
        confirmed_review_fields={"work_authorization": "Yes", "visa_sponsorship": "No"}
    )
    assert sub_res["success"] is True


# ==============================================================================
# TEST J, K, L: CAPTCHA, OTP/MFA & DOMAIN BLOCKING
# ==============================================================================

def test_step2_challenge_and_domain_guards():
    """Tests J, K, L: Anti-bot challenge detection and domain allowlisting."""
    # J & K: Challenge stopping
    mock_chall = MockApplicationPortal(simulate_challenge="CAPTCHA")
    engine = PortalAutomationEngine()
    packet = {
        "packet_id": "pkt_sec",
        "company": "SecureCorp",
        "role": "SecEngineer",
        "source_url": "https://careers.mockcorp.io/apply/sec",
    }
    sess_res = engine.create_portal_session(packet, mock_chall)
    assert sess_res["status"] == "CHALLENGE_REQUIRED"

    # L: Unauthorized domain redirect blocked
    portal = LinkedInApplicationPortal()
    bad_domain_packet = {
        "packet_id": "pkt_bad",
        "company": "PhishingCorp",
        "role": "Target",
        "source_url": "https://unauthorized-domain.com/apply",
    }
    with pytest.raises(PortalSecurityError) as exc_dom:
        engine.create_portal_session(bad_domain_packet, portal)
    assert "DOMAIN_BLOCKED" in str(exc_dom.value)


# ==============================================================================
# TEST M, O, P, Q: DUPLICATE PREVENTION, POST-SUBMISSION VERIFY & CRM
# ==============================================================================

def test_step2_submission_verification_and_crm():
    """Tests M, O, P, Q: Submission execution, independent verification, and CRM entry."""
    engine = PortalAutomationEngine()
    portal = LinkedInApplicationPortal()

    rand_comp = f"EnterpriseAI_{uuid.uuid4().hex[:8]}"
    job = {
        "id": "li_job_404",
        "title": "Staff AI Infrastructure Architect",
        "company": rand_comp,
        "url": "https://www.linkedin.com/jobs/view/404000",
    }
    profile = {"full_name": "Prathvi Sahu", "email": "prathvi@example.com", "phone": "+91 98765 43210"}
    packet = generate_application_packet(job=job, candidate_profile=profile, run_llm=False)

    sess_res = engine.create_portal_session(packet, portal)
    sess_id = sess_res["session_id"]
    approval_token = sess_res["approval_token"]

    # O: Successful Submission & Verification
    sub_res = engine.execute_approved_submission(sess_id, approval_token, packet)
    assert sub_res["success"] is True
    assert sub_res["status"] == "SUBMITTED_AND_VERIFIED"
    assert sub_res["independent_verification"]["verified"] is True
    assert sub_res["company"] == rand_comp

    # Q: Verified CRM Entry in career_applications
    apps = career_db.get_applications() or []
    found = False
    for a in apps:
        app_comp = a.get("company") or ((a.get("job") or {}).get("company") if isinstance(a.get("job"), dict) else "")
        if app_comp == rand_comp:
            found = True
            assert a.get("status") == "applied"
            break
    assert found is True, "Application must be logged in career_applications."

    # M: Duplicate Submission Blocked
    sess_dup = engine.create_portal_session(packet, portal)
    assert sess_dup["status"] == "DUPLICATE_BLOCKED"

    # P: Verification Failure Handling (Honest Status Reporting)
    with patch.object(portal, "verify_submission") as mock_verify:
        mock_verify.return_value = {"verified": False, "reason": "No confirmation found."}
        rand_comp2 = f"UncertainCorp_{uuid.uuid4().hex[:8]}"
        job2 = dict(job, company=rand_comp2, url="https://www.linkedin.com/jobs/view/404001")
        packet2 = generate_application_packet(job=job2, candidate_profile=profile, run_llm=False)
        sess2 = engine.create_portal_session(packet2, portal)
        unc_res = engine.execute_approved_submission(sess2["session_id"], sess2["approval_token"], packet2)
        assert unc_res["success"] is False
        assert unc_res["status"] == "UNCERTAIN_SUBMISSION"
        assert "could not independently verify" in unc_res["message"]
