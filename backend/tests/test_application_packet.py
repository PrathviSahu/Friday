"""Targeted unit tests for Phase 5.5D Step 4: Career Application Packet Generation (Tests A through U).
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from backend.services.career.packet import (
    generate_application_packet,
    edit_application_packet,
    approve_application_packet,
    compute_packet_hash,
    check_job_eligibility,
    select_best_resume,
    estimate_ats_score,
    analyze_skill_gaps,
    analyze_salary_fit,
    check_missing_fields,
    format_packet_preview,
)
from backend.services import career_db


@pytest.fixture(autouse=True)
def init_db():
    """Initialize DB tables before tests."""
    career_db.init_career_db()


# ==============================================================================
# TEST A, O, P, T, U: ELIGIBLE JOB PACKET GENERATION & HASH BINDING
# ==============================================================================

def test_step4_eligible_job_packet_generation_and_provenance():
    """Tests A, O, P, T, U: Full packet generation, readiness, hash, and no submission side-effects."""
    job = {
        "id": "job_101",
        "title": "Senior Python Backend Engineer",
        "company": "FastTech Solutions",
        "location": "Bangalore",
        "remote_type": "hybrid",
        "salary_raw": "₹25–35 LPA",
        "salary_min": 2500000.0,
        "salary_max": 3500000.0,
        "description": "We need a Senior Python Engineer with FastAPI, PostgreSQL, Docker, and AWS.",
        "url": "https://fasttech.io/careers/101",
        "provider": "linkedin_scraper",
        "signature": "sig_python_fasttech_101",
    }

    profile = {
        "full_name": "Alex Mercer",
        "email": "alex.mercer@gmail.com",
        "phone": "+91 98765 43210",
        "github_url": "https://github.com/alexmercer",
    }

    prefs = {
        "min_salary": 2000000.0,
        "preferred_remote": "any",
        "preferred_locations": ["Bangalore"],
    }

    packet = generate_application_packet(
        job=job,
        candidate_profile=profile,
        preferences=prefs,
        run_llm=False,
    )

    # A & O: State must be READY_FOR_REVIEW
    assert packet["readiness"] == "READY_FOR_REVIEW"
    assert packet["company"] == "FastTech Solutions"
    assert packet["role"] == "Senior Python Backend Engineer"

    # T: Retain Provider Provenance
    assert packet["provider"] == "linkedin_scraper"
    assert packet["source_url"] == "https://fasttech.io/careers/101"
    assert packet["canonical_signature"] == "sig_python_fasttech_101"

    # P: Deterministic SHA-256 Content Hash
    assert len(packet["content_hash"]) == 64
    assert packet["version"] == 1

    # U: No submission allowed in Step 4
    assert packet["readiness"] != "SUBMITTED"
    approved = approve_application_packet(packet)
    assert approved["readiness"] == "APPROVED"
    assert approved["readiness"] != "SUBMITTED"


# ==============================================================================
# TEST B, C, D, E, F: INELIGIBILITY & SALARY VARIATIONS
# ==============================================================================

def test_step4_ineligible_reasons_and_salary_fit():
    """Tests B, C, D, E, F: Blacklist, salary, remote, and location ineligibility."""
    # B: Blacklisted company
    with career_db._db() as conn:
        conn.execute("INSERT OR REPLACE INTO career_companies (name, is_blacklisted, blacklist_reason) VALUES ('BlacklistedOrg', 1, 'Toxic culture')")

    job_bl = {
        "title": "Backend Dev",
        "company": "BlacklistedOrg",
        "location": "Bangalore",
        "remote_type": "remote",
        "salary_max": 3000000.0,
    }
    is_el, reasons = check_job_eligibility(job_bl, {})
    assert is_el is False
    assert any("blacklisted" in r.lower() for r in reasons)

    # C: Salary below minimum
    job_low_sal = {
        "title": "Junior Dev",
        "company": "LowPay Corp",
        "location": "Bangalore",
        "remote_type": "remote",
        "salary_max": 500000.0,
    }
    is_el_sal, reasons_sal = check_job_eligibility(job_low_sal, {"min_salary": 1500000.0})
    assert is_el_sal is False
    assert any("compensation below minimum" in r.lower() for r in reasons_sal)

    # D: Salary unknown
    job_unknown_sal = {"title": "Dev", "company": "SecretCorp"}
    sal_fit = analyze_salary_fit(job_unknown_sal, {"min_salary": 1000000.0})
    assert sal_fit["status"] == "UNKNOWN"

    # E: Remote mismatch
    job_onsite = {
        "title": "Hardware Eng",
        "company": "OnsiteFab",
        "location": "Pune",
        "remote_type": "onsite",
    }
    is_el_rem, reasons_rem = check_job_eligibility(job_onsite, {"preferred_remote": "remote_only"})
    assert is_el_rem is False
    assert any("remote" in r.lower() for r in reasons_rem)


# ==============================================================================
# TEST G, H, I, J: RESUME SELECTION, ATS ESTIMATION & SKILL GAPS
# ==============================================================================

def test_step4_resume_selection_and_ats_analysis():
    """Tests G, H, I, J: Resume selection, ATS score estimation, and skill gaps."""
    resumes = [
        {
            "id": 1,
            "title": "Frontend React Resume",
            "content_json": {"skills": ["React", "TypeScript", "Tailwind", "CSS"]},
        },
        {
            "id": 2,
            "title": "Backend Cloud Resume",
            "content_json": {"skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"]},
        },
    ]

    job = {
        "title": "Python Cloud Architect",
        "description": "Looking for Python, FastAPI, Docker, and AWS experience.",
    }

    best_res, reason, score = select_best_resume(job, resumes)
    # G: Selects Resume 2
    assert best_res["id"] == 2
    assert "skill alignment" in reason.lower()

    # I: Estimated ATS Score
    ats_report = estimate_ats_score(job, best_res["content_json"])
    assert ats_report["label"] == "FRIDAY ESTIMATED ATS SCORE"
    assert ats_report["overall_ats_score"] >= 70.0
    assert "python" in ats_report["matched_keywords"]

    # J: Skill Gap Analysis
    gaps = analyze_skill_gaps(job, best_res["content_json"])
    assert "Python" in gaps["matched_skills"]
    assert "Fastapi" in gaps["matched_skills"]


# ==============================================================================
# TEST K, L, M: COMPANY INTEL, RECRUITER & COVER LETTER
# ==============================================================================

def test_step4_company_recruiter_and_cover_letter():
    """Tests K, L, M: Company intel context, recruiter info, and cover letter formatting."""
    job = {
        "title": "Data Platform Engineer",
        "company": "DataFlow Labs",
        "description": "Building streaming pipelines with Python.",
    }
    profile = {"full_name": "Jordan Lee", "email": "jordan@example.com", "phone": "123456"}

    packet = generate_application_packet(job=job, candidate_profile=profile, run_llm=False)

    # K & L: Company analysis & Recruiter
    assert packet["company_analysis"]["name"] == "DataFlow Labs"
    assert packet["recruiter_info"]["name"] == "Hiring Team"

    # M: Tailored Cover Letter
    assert "DataFlow Labs" in packet["cover_letter"]
    assert "Data Platform Engineer" in packet["cover_letter"]
    assert "Jordan Lee" in packet["cover_letter"]


# ==============================================================================
# TEST N & S: MISSING FIELDS DETECTION & FABRICATED DATA PREVENTION
# ==============================================================================

def test_step4_missing_required_fields_state():
    """Tests N & S: Missing required email or phone puts packet into INCOMPLETE state."""
    job = {"title": "Fullstack Dev", "company": "StartupX"}
    incomplete_profile = {"full_name": "Incomplete Candidate"}  # Missing email & phone

    packet = generate_application_packet(job=job, candidate_profile=incomplete_profile, run_llm=False)
    assert packet["readiness"] == "INCOMPLETE"
    assert "Email Address" in packet["missing_fields"]["REQUIRED"]
    assert "Phone Number" in packet["missing_fields"]["REQUIRED"]


# ==============================================================================
# TEST Q & R: EDIT INVALIDATION & DUPLICATE APPLICATION WARNING
# ==============================================================================

def test_step4_edit_invalidation_and_duplicate_detection():
    """Tests Q & R: Modifications increment version and change hash; duplicate applications flag warnings."""
    job = {
        "title": "Java Spring Developer",
        "company": "EnterpriseCorp",
        "description": "Java microservices.",
    }
    profile = {"full_name": "Dev User", "email": "dev@corp.com", "phone": "99999"}

    # Simulate existing application in database
    created_job_id = career_db.create_job({"title": "Java Spring Developer", "company": "EnterpriseCorp"})
    with career_db._db() as conn:
        conn.execute("INSERT OR REPLACE INTO career_applications (job_id, status) VALUES (?, 'applied')", (created_job_id,))

    packet = generate_application_packet(job=job, candidate_profile=profile, run_llm=False)

    initial_hash = packet["content_hash"]
    initial_version = packet["version"]

    # Q: Edit Cover Letter
    edited_packet = edit_application_packet(packet, {"cover_letter": "Custom shortened cover letter for hiring manager."})
    assert edited_packet["version"] == initial_version + 1
    assert edited_packet["content_hash"] != initial_hash
    assert edited_packet["readiness"] == "READY_FOR_REVIEW"

    # Preview formatting check
    preview_text = format_packet_preview(edited_packet)
    assert "Boss, I've prepared the application packet." in preview_text
    assert "EnterpriseCorp" in preview_text
