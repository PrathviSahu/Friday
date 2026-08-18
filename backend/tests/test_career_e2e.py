"""Targeted End-to-End tests for Phase 6.1: End-to-End Career OS Validation (Tests A through O).

Validates the full user journey:
Discovery ──► Multi-Source Ingestion ──► Deduplication ──► Preference Filtering ──►
AI Matching & Ranking ──► ApplicationPacket Generation ──► LinkedIn Portal Session ──►
Form Discovery ──► Field Mapping ──► Sensitive Screening Review ──► Final Immutable Preview (No Submission).
"""

import pytest
import time
from backend.services.career import (
    MockJobProvider,
    run_job_pipeline,
    generate_application_packet,
    LinkedInApplicationPortal,
    PortalAutomationEngine,
    FieldSensitivity,
)
from backend.services import career_db


@pytest.fixture(autouse=True)
def init_db():
    """Initialize DB tables before tests."""
    career_db.init_career_db()
    career_db.upsert_preference("min_salary", 0)
    career_db.upsert_preference("target_salary", 0)



def test_career_e2e_full_journey():
    """Tests A through O: Full End-to-End Career OS journey for 'Find me Java jobs above 6 LPA'."""
    start_time = time.time()

    # Step 1: Multi-Source Provider Setup with Realistic Java Jobs
    mock_jobs = [
        {
            "id": "java_01",
            "title": "Senior Java Backend Engineer",
            "company": "FinTech Corp",
            "location": "Bengaluru, India",
            "salary": "₹12,00,000 - ₹18,00,000 PA",
            "description": "Core Java, Spring Boot, Microservices, Kafka, PostgreSQL",
            "url": "https://www.linkedin.com/jobs/view/901001",
            "remote": "hybrid",
            "experience_level": "mid-level",
        },
        {
            "id": "java_02",
            "title": "Java Spring Boot Developer",
            "company": "CloudScale Global",
            "location": "Remote",
            "salary": "₹8,00,000 - ₹12,00,000 PA",
            "description": "Java 17, Spring Cloud, AWS, Kubernetes, REST APIs",
            "url": "https://www.linkedin.com/jobs/view/901002",
            "remote": "remote",
            "experience_level": "mid-level",
        },
        {
            "id": "java_03_dup",
            "title": "Senior Java Backend Engineer",
            "company": "FinTech Corp",
            "location": "Bengaluru, India",
            "salary": "₹12,00,000 - ₹18,00,000 PA",
            "description": "Core Java, Spring Boot, Microservices, Kafka",
            "url": "https://www.linkedin.com/jobs/view/901001",
            "remote": "hybrid",
            "experience_level": "mid-level",
        },
        {
            "id": "java_04_low_salary",
            "title": "Junior Java Trainee",
            "company": "Startup Hub",
            "location": "Pune, India",
            "salary": "₹3,50,000 PA",
            "description": "Java basics, SQL",
            "url": "https://www.linkedin.com/jobs/view/901004",
            "remote": "on-site",
            "experience_level": "entry-level",
        },
        {
            "id": "java_05_blacklisted",
            "title": "Lead Java Architect",
            "company": "ScammyConsulting LLC",
            "location": "Noida, India",
            "salary": "₹25,00,000 PA",
            "description": "Java enterprise",
            "url": "https://www.linkedin.com/jobs/view/901005",
            "remote": "on-site",
            "experience_level": "senior",
        }
    ]

    mock_provider = MockJobProvider(fixtures=mock_jobs)


    # Step 2: Set candidate preferences and blacklist in Career DB
    career_db.upsert_preference("min_salary", 600000)
    career_db.upsert_preference("target_salary", 1200000)
    career_db.upsert_company(
        "ScammyConsulting LLC",
        {
            "is_blacklisted": 1,
            "blacklist_reason": "Fraudulent consultancy company.",
        }
    )




    # Candidate profile
    candidate_profile = {
        "full_name": "Prathvi Sahu",
        "email": "prathvi@example.com",
        "phone": "+91 98765 43210",
        "skills": ["Java", "Spring Boot", "Microservices", "Kafka", "SQL", "Docker", "AWS"],
        "years_experience": "4",
        "work_authorization": "Yes",
        "visa_sponsorship": "No",
        "notice_period": "30 days",
    }

    # A & B: Discovery across providers
    pipeline_res = run_job_pipeline(
        query="Java",
        providers=[mock_provider],
        persist_to_db=False,
        run_llm_ranking=False,
    )



    discovered_jobs = pipeline_res["accepted_jobs"]
    elapsed_search = time.time() - start_time

    # C: Deduplication verified (java_01 and java_03_dup merged)
    # D: Filtering verified (java_04 below 6 LPA removed, java_05 blacklisted removed)
    assert len(discovered_jobs) == 2, f"Expected 2 qualified jobs after deduplication & filtering, got {len(discovered_jobs)}"
    assert all(j["company"] != "ScammyConsulting LLC" for j in discovered_jobs)
    assert all(j["salary_min"] is None or j["salary_min"] >= 600000 for j in discovered_jobs)


    # E: Ranking verified
    assert discovered_jobs[0]["match_score"] >= discovered_jobs[1]["match_score"]
    selected_job = discovered_jobs[0]
    assert selected_job["company"] == "FinTech Corp"
    assert "Senior Java" in selected_job["title"]

    # F & G: ApplicationPacket Generation & Content Hashing
    packet = generate_application_packet(
        job=selected_job,
        candidate_profile=candidate_profile,
        run_llm=False,
    )

    assert packet["readiness"] == "READY_FOR_REVIEW"
    assert packet["company"] == "FinTech Corp"
    assert packet["role"] == selected_job["title"]
    assert packet["source_url"] == selected_job["url"]
    assert len(packet["content_hash"]) == 64
    assert packet["ats_score"] >= 50
    assert "Meets or exceeds" in packet["salary_analysis"]["salary_fit"]
    assert "Java" in packet["skill_gaps"]["matched_skills"]




    # H: Portal Session Initialization
    engine = PortalAutomationEngine()
    portal = LinkedInApplicationPortal()

    sess_res = engine.create_portal_session(packet, portal)
    assert sess_res["status"] == "READY_FOR_PREVIEW"
    sess_id = sess_res["session_id"]
    approval_token = sess_res["approval_token"]

    # I & J & K: Form Discovery, Safe Mapping & Form Data Hash
    assert len(sess_res["form_data_hash"]) == 64
    assert sess_res["can_proceed"] is True
    assert len(sess_res["missing_required"]) == 0
    assert len(sess_res["review_required"]) >= 2

    # L: Packet / Form Binding Integrity Check
    session_obj = engine._active_sessions[sess_id]
    assert session_obj.packet_id == packet["packet_id"]
    assert session_obj.packet_content_hash == packet["content_hash"]
    assert session_obj.company == selected_job["company"]
    assert session_obj.role == selected_job["title"]
    assert session_obj.source_url == selected_job["url"]

    # M: Sensitive-field Review Provenance
    preview_txt = engine.generate_submission_preview(sess_id)
    assert "Boss, here is the application submission preview:" in preview_txt
    assert "FinTech Corp" in preview_txt
    assert "Senior Java Backend Engineer" in preview_txt
    assert "REVIEW REQUIRED FIELDS (Explicit Candidate Confirmation Required):" in preview_txt
    assert "Candidate Profile → work_authorization" in preview_txt
    assert "Candidate Profile → visa_sponsorship" in preview_txt

    # N: Absolute Safety Check — Zero Submissions Executed
    assert "Nothing has been submitted yet." in preview_txt
    assert session_obj.submitted is False
    assert session_obj.approval_consumed is False

    # Check CRM table — no applications inserted prior to execution
    apps = career_db.get_applications() or []
    assert not any((a.get("company") or "") == "FinTech Corp" and a.get("status") == "applied" for a in apps)

    # Cleanup preferences for subsequent tests
    career_db.upsert_preference("min_salary", 0)
    career_db.upsert_preference("target_salary", 0)



def test_career_e2e_invariants_and_drift_protection():
    """Validates that any tampering across the E2E chain strictly halts execution."""
    engine = PortalAutomationEngine()
    portal = LinkedInApplicationPortal()

    job = {
        "id": "e2e_tamper_01",
        "title": "Java Microservices Architect",
        "company": "TamperProof Systems",
        "url": "https://www.linkedin.com/jobs/view/902001",
    }
    profile = {"full_name": "Prathvi Sahu", "email": "prathvi@example.com", "phone": "+91 98765 43210"}
    packet = generate_application_packet(job=job, candidate_profile=profile, run_llm=False)

    sess_res = engine.create_portal_session(packet, portal)
    sess_id = sess_res["session_id"]
    token = sess_res["approval_token"]

    # 1. Tamper company name
    tampered_company = dict(packet, company="CorruptedCorp")
    with pytest.raises(ValueError) as exc1:
        engine.execute_approved_submission(sess_id, token, tampered_company)
    assert "mismatch" in str(exc1.value).lower()

    # 2. Tamper URL
    tampered_url = dict(packet, source_url="https://www.linkedin.com/jobs/view/999999")
    with pytest.raises(ValueError) as exc2:
        engine.execute_approved_submission(sess_id, token, tampered_url)
    assert "mismatch" in str(exc2.value).lower()

    # 3. Reject review fields
    with pytest.raises(ValueError) as exc3:
        engine.execute_approved_submission(sess_id, token, packet, confirmed_review_fields=False)
    assert "unconfirmed" in str(exc3.value).lower()
