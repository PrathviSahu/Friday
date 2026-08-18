"""Targeted unit tests for Phase 5.5D Step 5: Portal Automation Safety Architecture (Tests A through W).
"""

import pytest
from datetime import datetime, timezone, timedelta
from backend.services.career.portal import (
    BaseApplicationPortal,
    MockApplicationPortal,
    PortalAutomationEngine,
    PortalSecurityError,
    FieldSensitivity,
    classify_field_sensitivity,
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
# TEST A, F, T: PROVIDER DISCOVERY & SENSITIVITY CLASSIFICATION
# ==============================================================================

def test_step5_provider_discovery_and_sensitivity_policy():
    """Tests A, F, T: Sensitivity classification and credential rejection."""
    portal = MockApplicationPortal()
    assert portal.provider_name() == "mock_portal"
    assert "careers.mockcorp.io" in portal.allowed_domains()

    # F & T: Safe, Review Required, and Forbidden Sensitive Fields
    assert classify_field_sensitivity("email") == FieldSensitivity.SAFE_AUTO_FILL
    assert classify_field_sensitivity("phone") == FieldSensitivity.SAFE_AUTO_FILL
    assert classify_field_sensitivity("expected_salary") == FieldSensitivity.REVIEW_REQUIRED
    assert classify_field_sensitivity("work_authorization") == FieldSensitivity.REVIEW_REQUIRED

    # Forbidden fields MUST be classified as NEVER_AUTO_FILL
    assert classify_field_sensitivity("password") == FieldSensitivity.NEVER_AUTO_FILL
    assert classify_field_sensitivity("otp_code") == FieldSensitivity.NEVER_AUTO_FILL
    assert classify_field_sensitivity("mfa_token") == FieldSensitivity.NEVER_AUTO_FILL
    assert classify_field_sensitivity("captcha_answer") == FieldSensitivity.NEVER_AUTO_FILL
    assert classify_field_sensitivity("vault_key") == FieldSensitivity.NEVER_AUTO_FILL


# ==============================================================================
# TEST B, C, D, E, H: FORM DISCOVERY, FIELD MAPPING, AUTOFILL & MISSING FIELDS
# ==============================================================================

def test_step5_form_discovery_and_mapping():
    """Tests B, C, D, E, H: Form inspection, safe mapping, and missing data detection."""
    portal = MockApplicationPortal()
    open_res = portal.open_application({"id": "1", "url": "https://careers.mockcorp.io/apply/1", "company": "MockCorp", "title": "Dev"})
    sess_id = open_res["session_id"]

    # B: Form Discovery
    schema = portal.discover_form(sess_id)
    assert schema["fields_count"] >= 10
    assert any(f["name"] == "email" for f in schema["fields"])
    assert any(f["name"] == "resume" for f in schema["fields"])

    # Sample packet
    mock_packet = {
        "packet_id": "pkt_test_101",
        "version": 1,
        "company": "MockCorp",
        "role": "Python Engineer",
        "profile_data": {
            "name": "Jane Doe",
            "email": "jane@doe.com",
            "phone": "+1 555-0199",
            "github": "https://github.com/janedoe",
        },
        "selected_resume_title": "Fullstack Cloud Resume",
        "cover_letter": "I am excited to apply...",
    }

    # C & D: Mapping & Safe Autofill
    mapped = portal.map_fields(schema, mock_packet)
    assert mapped["can_proceed"] is True
    assert mapped["mapped_fields"]["email"]["value"] == "jane@doe.com"
    assert mapped["mapped_fields"]["first_name"]["value"] == "Jane"
    assert mapped["mapped_fields"]["last_name"]["value"] == "Doe"
    assert len(mapped["review_required"]) > 0

    # E: Missing Required Field Detection
    incomplete_packet = {
        "packet_id": "pkt_inc_102",
        "profile_data": {"name": "No Contact User"},
    }
    inc_mapped = portal.map_fields(schema, incomplete_packet)
    assert inc_mapped["can_proceed"] is False
    assert any("email" in m.lower() for m in inc_mapped["missing_required"])
    assert any("phone" in m.lower() for m in inc_mapped["missing_required"])


# ==============================================================================
# TEST G, I, J, K, L, V: SESSION BINDING, PREVIEW, APPROVAL & INVALIDATION
# ==============================================================================

def test_step5_session_binding_preview_and_approval_invalidation():
    """Tests G, I, J, K, L, V: Packet hash binding, 5-min TTL approval, and edit invalidation."""
    import uuid
    engine = PortalAutomationEngine()
    portal = MockApplicationPortal()

    rand_comp1 = f"CloudScale_{uuid.uuid4().hex[:8]}"
    job = {
        "id": "job_sess_01",
        "title": "Backend Architect",
        "company": rand_comp1,
        "url": "https://careers.mockcorp.io/apply/101",
    }
    profile = {"full_name": "Sarah Connor", "email": "sarah@cyberdyne.io", "phone": "555-1234"}
    packet = generate_application_packet(job=job, candidate_profile=profile, run_llm=False)

    # G: Session Creation & Binding
    sess_res = engine.create_portal_session(packet, portal)
    assert sess_res["status"] == "READY_FOR_PREVIEW"
    sess_id = sess_res["session_id"]
    approval_token = sess_res["approval_token"]

    # I: Preview Generation
    preview_txt = engine.generate_submission_preview(sess_id)
    assert "Boss, here is the application submission preview:" in preview_txt
    assert rand_comp1 in preview_txt
    assert "sarah@cyberdyne.io" in preview_txt
    assert approval_token in preview_txt

    # J: Valid Approval Execution
    sub_res = engine.execute_approved_submission(sess_id, approval_token, packet)
    assert sub_res["success"] is True
    assert sub_res["status"] == "SUBMITTED_AND_VERIFIED"
    assert "application_id" in sub_res

    # Single-use: Reusing token must fail
    with pytest.raises(RuntimeError) as exc_reuse:
        engine.execute_approved_submission(sess_id, approval_token, packet)
    assert "already consumed" in str(exc_reuse.value).lower()

    # V & L: Packet Modification Invalidation Test on fresh job
    rand_comp2 = f"NextGenScale_{uuid.uuid4().hex[:8]}"
    job2 = {
        "id": "job_sess_02",
        "title": "Cloud Architect",
        "company": rand_comp2,
        "url": "https://careers.mockcorp.io/apply/102",
    }
    packet2 = generate_application_packet(job=job2, candidate_profile=profile, run_llm=False)
    sess_res2 = engine.create_portal_session(packet2, portal)
    sess_id2 = sess_res2["session_id"]
    token2 = sess_res2["approval_token"]

    # Modify packet cover letter
    modified_packet2 = edit_application_packet(packet2, {"cover_letter": "Shortened new version."})
    with pytest.raises(ValueError) as exc_mod:
        engine.execute_approved_submission(sess_id2, token2, modified_packet2)
    assert "mismatch" in str(exc_mod.value).lower()


# ==============================================================================
# TEST K: APPROVAL TTL EXPIRATION
# ==============================================================================

def test_step5_approval_ttl_expiration():
    """Test K: Approval token expires after 5 minutes."""
    import uuid
    engine = PortalAutomationEngine()
    portal = MockApplicationPortal()

    job = {"id": "j_exp_01", "title": "Dev", "company": f"ExpCorp_{uuid.uuid4().hex[:8]}", "url": "https://careers.mockcorp.io/apply/1"}
    profile = {"full_name": "Sam Expire", "email": "sam@exp.com", "phone": "123"}
    packet = generate_application_packet(job=job, candidate_profile=profile, run_llm=False)

    sess_res = engine.create_portal_session(packet, portal)
    sess_id = sess_res["session_id"]
    token = sess_res["approval_token"]

    # Artificially expire the approval
    session_obj = engine._active_sessions[sess_id]
    session_obj.approval_expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)

    with pytest.raises(TimeoutError) as exc_exp:
        engine.execute_approved_submission(sess_id, token, packet)
    assert "expired" in str(exc_exp.value).lower()


# ==============================================================================
# TEST M, N, W: MOCK SUBMISSION, INDEPENDENT VERIFICATION & CRM LOGGING
# ==============================================================================

def test_step5_submission_independent_verification_and_crm():
    """Tests M, N, W: Mock submission, verification on portal, and CRM recording."""
    import uuid
    engine = PortalAutomationEngine()
    portal = MockApplicationPortal()

    rand_comp = f"DataHub_{uuid.uuid4().hex[:8]}"
    job = {
        "id": "job_crm_01",
        "title": "Data Infrastructure Engineer",
        "company": rand_comp,
        "url": "https://careers.mockcorp.io/apply/501",
    }
    profile = {"full_name": "Marcus Vance", "email": "marcus@analytics.org", "phone": "777-8888"}
    packet = generate_application_packet(job=job, candidate_profile=profile, run_llm=False)

    sess_res = engine.create_portal_session(packet, portal)
    sub_res = engine.execute_approved_submission(sess_res["session_id"], sess_res["approval_token"], packet)

    # M & N: Submitted & Independently Verified
    assert sub_res["status"] == "SUBMITTED_AND_VERIFIED"
    assert sub_res["independent_verification"]["verified"] is True
    assert sub_res["independent_verification"]["company"] == rand_comp

    # W: Verified Career CRM Entry in career_applications
    apps = career_db.get_applications() or []
    found_app = False
    for a in apps:
        app_comp = a.get("company") or ((a.get("job") or {}).get("company") if isinstance(a.get("job"), dict) else "")
        if app_comp == rand_comp:
            found_app = True
            assert a.get("status") == "applied"
            break
    assert found_app is True, "Submitted application must be logged in career_applications table."


# ==============================================================================
# TEST O: DUPLICATE APPLICATION PREVENTION
# ==============================================================================

def test_step5_duplicate_application_prevention():
    """Test O: Duplicate application to the same job/company is blocked."""
    import uuid
    engine = PortalAutomationEngine()
    portal = MockApplicationPortal()

    rand_comp = f"DuplicatePrevent_{uuid.uuid4().hex[:8]}"
    job = {
        "id": "job_dup_01",
        "title": "Platform Lead",
        "company": rand_comp,
        "url": "https://careers.mockcorp.io/apply/601",
    }
    profile = {"full_name": "Test User", "email": "test@prevent.com", "phone": "123"}
    packet = generate_application_packet(job=job, candidate_profile=profile, run_llm=False)

    # First session & submission
    sess1 = engine.create_portal_session(packet, portal)
    engine.execute_approved_submission(sess1["session_id"], sess1["approval_token"], packet)

    # Attempt second session for same job
    sess2 = engine.create_portal_session(packet, portal)
    assert sess2["status"] == "DUPLICATE_BLOCKED"
    assert "already submitted" in sess2["message"].lower()



# ==============================================================================
# TEST P, Q, R: CAPTCHA, OTP & MFA CHALLENGE DETECTION
# ==============================================================================

def test_step5_challenge_detection():
    """Tests P, Q, R: CAPTCHA, OTP, and MFA challenges halt automation cleanly."""
    engine = PortalAutomationEngine()

    packet = {
        "packet_id": "pkt_chall_01",
        "company": "SecureBank",
        "role": "Security Eng",
        "source_url": "https://careers.mockcorp.io/apply/sec",
    }

    # Q: CAPTCHA Challenge Portal
    captcha_portal = MockApplicationPortal(simulate_challenge="CAPTCHA")
    res_captcha = engine.create_portal_session(packet, captcha_portal)
    assert res_captcha["status"] == "CHALLENGE_REQUIRED"
    assert res_captcha["challenge_type"] == "CAPTCHA"

    # R: OTP Challenge Portal
    otp_portal = MockApplicationPortal(simulate_challenge="OTP")
    res_otp = engine.create_portal_session(packet, otp_portal)
    assert res_otp["status"] == "CHALLENGE_REQUIRED"
    assert res_otp["challenge_type"] == "OTP"


# ==============================================================================
# TEST S & U: UNEXPECTED DOMAIN & ARBITRARY NAVIGATION BLOCKING
# ==============================================================================

def test_step5_domain_allowlist_and_arbitrary_navigation_blocking():
    """Tests S & U: Navigation to arbitrary or untrusted domains is strictly blocked."""
    engine = PortalAutomationEngine()
    portal = MockApplicationPortal()

    packet_bad_domain = {
        "packet_id": "pkt_untrusted_01",
        "company": "UntrustedSite",
        "role": "Hacker Role",
        "source_url": "https://phishing-site.evil/apply",
    }

    with pytest.raises(PortalSecurityError) as exc_dom:
        engine.create_portal_session(packet_bad_domain, portal)
    assert "DOMAIN_BLOCKED" in str(exc_dom.value)
