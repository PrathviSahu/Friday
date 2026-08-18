"""Targeted unit tests for Phase 5.5D Step 1: Canonical Multi-Source Job Architecture & Ingestion Engine (Tests A through R).
"""

import pytest
from unittest.mock import MagicMock, patch
from backend.services.career.provider import (
    BaseJobProvider,
    MockJobProvider,
    ExistingJobScraperAdapter,
    parse_salary_raw,
    normalize_remote_status,
    normalize_experience_level,
    compute_job_signature,
)
from backend.services.career.pipeline import run_job_pipeline
from backend.services import career_db


@pytest.fixture(autouse=True)
def init_db():
    """Ensure career DB tables are initialized before tests."""
    career_db.init_career_db()


# ==============================================================================
# TEST A: PROVIDER DISCOVERY
# ==============================================================================

def test_career_provider_discovery():
    """Test A: BaseJobProvider discovery, name, and connection checking."""
    mock_prov = MockJobProvider()
    assert mock_prov.provider_name() == "mock_provider"

    conn_status = mock_prov.check_connection()
    assert conn_status["status"] == "CONNECTED"
    assert conn_status["connected"] is True
    assert conn_status["provider"] == "mock_provider"

    adapter = ExistingJobScraperAdapter()
    assert adapter.provider_name() == "linkedin_scraper"
    assert adapter.check_connection()["connected"] is True


# ==============================================================================
# TEST B: MOCK SEARCH
# ==============================================================================

def test_career_mock_search():
    """Test B: Mock search returns deterministic job results matching query."""
    mock_prov = MockJobProvider()
    results = mock_prov.search_jobs("Python")
    assert len(results) >= 1
    assert any("Python" in j["title"] for j in results)


# ==============================================================================
# TEST C & O: NORMALIZATION & TRACEABILITY
# ==============================================================================

def test_career_canonical_schema_normalization():
    """Tests C & O: Canonical schema formatting and traceability metadata."""
    mock_prov = MockJobProvider()
    raw = {
        "id": "test_99",
        "title": " Senior React Engineer ",
        "company": " WebTech Corp ",
        "location": " Mumbai ",
        "salary_raw": "$80k-$100k",
        "experience_required": "5+ years",
        "description": "Frontend lead position.",
        "url": "https://webtech.io/jobs/99",
    }
    norm = mock_prov.normalize_job(raw)

    assert norm["provider"] == "mock_provider"
    assert norm["provider_job_id"] == "test_99"
    assert norm["title"] == "Senior React Engineer"
    assert norm["company"] == "WebTech Corp"
    assert norm["location"] == "Mumbai"
    assert norm["salary_min"] == 80000.0
    assert norm["salary_max"] == 100000.0
    assert norm["currency"] == "USD"
    assert norm["url"] == "https://webtech.io/jobs/99"
    assert norm["signature"] is not None


# ==============================================================================
# TEST D: SALARY PARSING
# ==============================================================================

def test_career_salary_parsing():
    """Test D: Parsing various raw salary strings into structured min/max/currency."""
    # INR LPA Range
    s_min, s_max, curr = parse_salary_raw("₹5–8 LPA")
    assert s_min == 500000.0
    assert s_max == 800000.0
    assert curr == "INR"

    # USD K Range
    s_min, s_max, curr = parse_salary_raw("$75k-$90k")
    assert s_min == 75000.0
    assert s_max == 90000.0
    assert curr == "USD"

    # Single Annual figure
    s_min, s_max, curr = parse_salary_raw("15,00,000 / year")
    assert s_min == 1500000.0
    assert s_max == 1500000.0
    assert curr == "INR"

    # Malformed / Empty
    s_min, s_max, curr = parse_salary_raw("Competitive Market Standard")
    assert s_min == 0.0
    assert s_max == 0.0


# ==============================================================================
# TEST E & F: LOCATION & REMOTE NORMALIZATION
# ==============================================================================

def test_career_location_remote_experience_normalization():
    """Tests E & F: Normalizing remote status and experience level."""
    assert normalize_remote_status("Remote", "India") == "remote"
    assert normalize_remote_status("", "Work from Home, Bangalore") == "remote"
    assert normalize_remote_status("Hybrid", "Delhi") == "hybrid"
    assert normalize_remote_status("Onsite", "Office in Mumbai") == "onsite"

    assert normalize_experience_level("0-1 years", "Fresher Developer") == "fresher"
    assert normalize_experience_level("5+ years", "Senior Architect") == "senior"


# ==============================================================================
# TEST G, H, I: DEDUPLICATION (EXACT, CROSS-PROVIDER, & DIFFERENT LOCATION)
# ==============================================================================

def test_career_deduplication():
    """Tests G, H, I: Exact & cross-provider duplicate detection without merging different location roles."""
    sig1 = compute_job_signature("TechCorp", "Backend Python Engineer", "Bangalore", "hybrid")
    sig2 = compute_job_signature("TechCorp", "Backend Python Engineer", "Bangalore", "hybrid")
    sig3 = compute_job_signature("TechCorp", "Backend Python Engineer", "Hyderabad", "onsite")

    assert sig1 == sig2, "Exact same role and location must produce identical SHA-256 signatures."
    assert sig1 != sig3, "Genuinely different location/role roles must produce distinct signatures."

    # Run pipeline against mock fixtures containing exact duplicate (mock_101 & mock_104)
    res = run_job_pipeline(query="", provider=MockJobProvider(), persist_to_db=False, run_llm_ranking=False)
    dup_ids = [j["provider_job_id"] for j in res["duplicate_jobs"]]
    assert "mock_104" in dup_ids, "mock_104 duplicate fixture must be detected and filtered."

    # Ensure mock_105 (Hyderabad location) is accepted and NOT merged
    accepted_ids = [j["provider_job_id"] for j in res["accepted_jobs"]]
    assert "mock_105" in accepted_ids, "Different location role mock_105 must be accepted."


# ==============================================================================
# TEST J: BLACKLIST FILTERING
# ==============================================================================

def test_career_blacklist_filtering():
    """Test J: Blacklisted company (EvilCorp) is filtered with machine-readable reason."""
    # Ensure EvilCorp is blacklisted in career_companies table
    with career_db._db() as conn:
        conn.execute("INSERT OR REPLACE INTO career_companies (name, is_blacklisted, blacklist_reason) VALUES ('EvilCorp', 1, 'Unethical hiring practices')")

    res = run_job_pipeline(query="", provider=MockJobProvider(), persist_to_db=False, run_llm_ranking=False)
    filtered_comp_reasons = [(j["company"], j["filter_reason"]) for j in res["filtered_jobs"]]

    evil_filtered = any(comp == "EvilCorp" and "BLACKLISTED" in reason for comp, reason in filtered_comp_reasons)
    assert evil_filtered is True, "EvilCorp must be filtered out by blacklist check."


# ==============================================================================
# TEST K & L: PREFERENCE FILTERING (SALARY & REMOTE)
# ==============================================================================

def test_career_preference_filtering():
    """Tests K & L: Filtering jobs based on user career_preferences (min salary & remote)."""
    # Upsert user preferences
    career_db.upsert_preference("min_salary", "2000000", "user")  # ₹20 LPA minimum salary
    career_db.upsert_preference("remote_preference", "remote_only", "user")

    res = run_job_pipeline(query="", provider=MockJobProvider(), persist_to_db=False, run_llm_ranking=False)

    for j in res["filtered_jobs"]:
        reason = j.get("filter_reason", "")
        assert "SALARY_BELOW_MINIMUM" in reason or "REMOTE_REQUIRED" in reason or "BLACKLISTED" in reason or "LOCATION_MISMATCH" in reason

    # Clean up preferences for next tests
    career_db.upsert_preference("min_salary", "0", "user")
    career_db.upsert_preference("remote_preference", "", "user")


# ==============================================================================
# TEST M: CANDIDATE RANKING INTEGRATION
# ==============================================================================

def test_career_ranking_integration():
    """Test M: Candidate match score and details attached from analyze_job_match."""
    with patch("backend.services.career_intelligence.analyze_job_match", return_value={"overall_score": 88, "recommendation": "apply_now"}):
        res = run_job_pipeline(query="Backend", provider=MockJobProvider(), persist_to_db=False, run_llm_ranking=True)
        assert len(res["accepted_jobs"]) >= 1
        top_job = res["accepted_jobs"][0]
        assert top_job["match_score"] == 88.0
        assert top_job["match_details"]["recommendation"] == "apply_now"


# ==============================================================================
# TEST N & R: CAREER DB PERSISTENCE & NO DUPLICATE INSERT
# ==============================================================================

def test_career_db_persistence_and_no_duplicate_insert():
    """Tests N & R: Jobs persisted to career_jobs table without duplicate row creation."""
    import uuid
    career_db.upsert_preference("min_salary", "0", "user")
    career_db.upsert_preference("remote_preference", "", "user")
    career_db.upsert_preference("preferred_locations", [], "user")

    rand_id = uuid.uuid4().hex[:8]
    unique_company = f"UniqueCorp_{rand_id}"

    unique_fixtures = [
        {
            "id": f"uniq_{rand_id}",
            "title": f"Fullstack Cloud Engineer {rand_id}",
            "company": unique_company,
            "location": "Chennai",
            "remote_type": "remote",
            "salary_raw": "₹50 LPA",
            "description": "Unique cloud engineering position.",
        }
    ]
    provider = MockJobProvider(fixtures=unique_fixtures)
    initial_jobs = career_db.get_jobs() or []
    initial_count = len(initial_jobs)

    # Ingest mock jobs into database
    res1 = run_job_pipeline(query="", provider=provider, persist_to_db=True, run_llm_ranking=False)
    assert len(res1["accepted_jobs"]) == 1, f"Job should be accepted, but was filtered/dup: accepted={res1['accepted_jobs']}, filtered={res1['filtered_jobs']}, dup={res1['duplicate_jobs']}"

    new_jobs = career_db.get_jobs() or []
    assert len(new_jobs) > initial_count, "New unique job must be persisted into career_jobs table."

    # Run ingestion AGAIN with same provider — should be flagged as duplicate
    res2 = run_job_pipeline(query="", provider=provider, persist_to_db=True, run_llm_ranking=False)
    final_jobs = career_db.get_jobs() or []

    assert len(res2["duplicate_jobs"]) >= 1, "Duplicate job must be caught in duplicate_jobs list."
    assert len(final_jobs) == len(new_jobs), "Re-running pipeline must not insert duplicate database rows."





# ==============================================================================
# TEST P: MALFORMED JOB HANDLING
# ==============================================================================

def test_career_malformed_job_handling():
    """Test P: Malformed job missing required fields handled gracefully without crashing."""
    malformed_fixtures = [
        {"id": None, "title": None, "company": None},
        {},
    ]
    provider = MockJobProvider(fixtures=malformed_fixtures)
    res = run_job_pipeline(query="", provider=provider, persist_to_db=False, run_llm_ranking=False)
    assert isinstance(res["accepted_jobs"], list)


# ==============================================================================
# TEST Q: PROVIDER FAILURE HANDLING
# ==============================================================================

def test_career_provider_failure_handling():
    """Test Q: Provider exception caught in errors dict without breaking execution."""
    failing_provider = MagicMock(spec=BaseJobProvider)
    failing_provider.provider_name.return_value = "failing_provider"
    failing_provider.search_jobs.side_effect = RuntimeError("External API 503 Unavailable")

    res = run_job_pipeline(query="Java", provider=failing_provider, persist_to_db=False, run_llm_ranking=False)
    assert res["success"] is False
    assert len(res["errors"]) >= 1
    assert "503 Unavailable" in res["errors"][0]
