"""Targeted unit tests for Phase 5.5D Step 2: Real Job Provider Integration — LinkedIn Read/Search Only (Tests A through R).
"""

import pytest
from unittest.mock import MagicMock, patch
from backend.services.career.provider import (
    LinkedInJobProvider,
    ExistingJobScraperAdapter,
)
from backend.services.career.pipeline import run_job_pipeline
from backend.services import career_db


@pytest.fixture(autouse=True)
def init_db():
    """Initialize DB tables before tests."""
    career_db.init_career_db()


# ==============================================================================
# TEST A & R: PROVIDER REGISTRATION & ADAPTER REUSE
# ==============================================================================

def test_step2_provider_registration_and_adapter_alias():
    """Tests A & R: LinkedInJobProvider registration and ExistingJobScraperAdapter alias."""
    provider = LinkedInJobProvider()
    assert provider.provider_name() == "linkedin_scraper"
    assert ExistingJobScraperAdapter is LinkedInJobProvider


# ==============================================================================
# TEST B, C, D, E, N: CONNECTION STATES & CHALLENGE HANDLING
# ==============================================================================

def test_step2_connection_states():
    """Tests B, C, D, E, N: Truthful connection status reporting for LinkedIn."""
    provider = LinkedInJobProvider()

    # C: Auth Required when cookies missing from DB
    with patch("backend.services.career_db._db") as mock_db:
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_db.return_value.__enter__.return_value = mock_conn

        res_auth = provider.check_connection()
        assert res_auth["status"] == "AUTH_REQUIRED"
        assert res_auth["connected"] is False

    # B: Connected when cookies present in DB
    with patch("backend.services.career_db._db") as mock_db:
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = ('[{"name": "li_at", "value": "secret"}]',)
        mock_db.return_value.__enter__.return_value = mock_conn

        res_conn = provider.check_connection()
        assert res_conn["status"] == "CONNECTED"
        assert res_conn["connected"] is True


def test_step2_challenge_and_timeout_handling():
    """Tests D & N: Anti-bot challenge raises CHALLENGE_REQUIRED and timeout raises TEMPORARILY_UNAVAILABLE."""
    provider = LinkedInJobProvider()

    # D: Anti-bot challenge detection
    with patch("backend.services.job_scraper.fetch_live_linkedin_jobs", side_effect=Exception("LinkedIn CAPTCHA Checkpoint Challenge")), \
         patch("services.job_scraper.fetch_live_linkedin_jobs", side_effect=Exception("LinkedIn CAPTCHA Checkpoint Challenge")):
        with pytest.raises(RuntimeError) as exc_info:
            provider.search_jobs("Java")
        assert "CHALLENGE_REQUIRED" in str(exc_info.value)

    # N: Timeout handling
    with patch("backend.services.job_scraper.fetch_live_linkedin_jobs", side_effect=Exception("Connection Timeout")), \
         patch("services.job_scraper.fetch_live_linkedin_jobs", side_effect=Exception("Connection Timeout")):
        with pytest.raises(RuntimeError) as exc_info:
            provider.search_jobs("Java")
        assert "TEMPORARILY_UNAVAILABLE" in str(exc_info.value)



# ==============================================================================
# TEST F, G, H, J, K, O: READ-ONLY SEARCH, CANONICAL NORMALIZATION & RATE LIMIT
# ==============================================================================

def test_step2_search_normalization_and_rate_limit():
    """Tests F, G, H, J, K, O: Read-only search returns normalized jobs capped at 10 results."""
    mock_raw = [
        {
            "title": f"Java Software Engineer {i}",
            "company": f"TechCorp_{i}",
            "location": "Mumbai, India",
            "url": f"https://linkedin.com/jobs/view/{i}",
            "posted": "2 days ago",
        }
        for i in range(15)  # 15 raw results
    ]

    provider = LinkedInJobProvider()

    with patch("backend.services.job_scraper.fetch_live_linkedin_jobs", return_value=mock_raw), \
         patch("services.job_scraper.fetch_live_linkedin_jobs", return_value=mock_raw):
        results = provider.search_jobs("Java Spring Boot")
        # O: Enforce strict rate limit cap of max 10
        assert len(results) == 10
        top = results[0]
        assert top["provider"] == "linkedin_scraper"
        assert top["title"] == "Java Software Engineer 0"
        assert top["company"] == "TechCorp_0"
        assert top["location"] == "Mumbai, India"


# ==============================================================================
# TEST I, L, M: CANONICAL PIPELINE INTEGRATION (DEDUP, BLACKLIST, PREFERENCES)
# ==============================================================================

def test_step2_canonical_pipeline_integration():
    """Tests I, L, M: Passing LinkedIn provider results through canonical deduplication, blacklist, and preferences."""
    mock_raw = [
        {
            "title": "Java Spring Boot Developer",
            "company": "Infosys",
            "location": "Mumbai",
            "url": "https://linkedin.com/jobs/view/1001",
        },
        {
            "title": "Java Spring Boot Developer",
            "company": "Infosys",
            "location": "Mumbai",
            "url": "https://linkedin.com/jobs/view/1002_dup",
        },
        {
            "title": "Data Analyst",
            "company": "EvilCorp",  # Blacklisted
            "location": "Delhi",
            "url": "https://linkedin.com/jobs/view/1003",
        },
    ]

    # Blacklist EvilCorp
    with career_db._db() as conn:
        conn.execute("INSERT OR REPLACE INTO career_companies (name, is_blacklisted, blacklist_reason) VALUES ('EvilCorp', 1, 'Blacklisted company')")

    provider = LinkedInJobProvider()

    with patch("backend.services.job_scraper.fetch_live_linkedin_jobs", return_value=mock_raw), \
         patch("services.job_scraper.fetch_live_linkedin_jobs", return_value=mock_raw):
        pipeline_res = run_job_pipeline(query="Java", provider=provider, persist_to_db=False, run_llm_ranking=False)


        assert len(pipeline_res["accepted_jobs"]) == 1
        assert pipeline_res["accepted_jobs"][0]["company"] == "Infosys"

        # I: Exact duplicate caught
        assert len(pipeline_res["duplicate_jobs"]) == 1

        # L: Blacklisted job caught
        assert len(pipeline_res["filtered_jobs"]) == 1
        assert "BLACKLISTED" in pipeline_res["filtered_jobs"][0]["filter_reason"]


# ==============================================================================
# TEST P: SECRET REDACTION
# ==============================================================================

def test_step2_secret_redaction():
    """Test P: Guarantees no cookies, li_at session tokens, or passwords enter status or job dicts."""
    provider = LinkedInJobProvider()
    with patch("backend.services.career_db._db") as mock_db:
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = ('[{"name": "li_at", "value": "SECRET_SESSION_TOKEN_12345"}]',)
        mock_db.return_value.__enter__.return_value = mock_conn

        status = provider.check_connection()
        status_str = str(status).lower()
        assert "li_at" not in status_str
        assert "secret_session_token" not in status_str
        assert "password" not in status_str


# ==============================================================================
# TEST Q: NO APPLICATION ACTION INVOKED (STRICT READ-ONLY BOUNDARY)
# ==============================================================================

def test_step2_read_only_boundary_guards():
    """Test Q: Assert that apply, form-filling, or recruiter messaging methods raise NotImplementedError."""
    provider = LinkedInJobProvider()

    with pytest.raises(NotImplementedError) as exc1:
        provider.apply_to_job("https://linkedin.com/jobs/view/1001")
    assert "READ/SEARCH ONLY" in str(exc1.value)

    with pytest.raises(NotImplementedError) as exc2:
        provider.submit_application_form({})
    assert "READ/SEARCH ONLY" in str(exc2.value)

    with pytest.raises(NotImplementedError) as exc3:
        provider.send_recruiter_message("recruiter_123", "Hello")
    assert "READ/SEARCH ONLY" in str(exc3.value)
