"""Targeted unit tests for Phase 5.5D Step 3: Multi-Source Job Provider Expansion (Tests A through Q).
"""

import pytest
from unittest.mock import MagicMock, patch
from backend.services.career.provider import (
    BaseJobProvider,
    MockJobProvider,
    LinkedInJobProvider,
)
from backend.services.career.remoteok_provider import RemoteOKJobProvider
from backend.services.career.pipeline import run_job_pipeline
from backend.services import career_db


@pytest.fixture(autouse=True)
def init_db():
    """Initialize DB tables before tests."""
    career_db.init_career_db()
    career_db.upsert_preference("min_salary", 0)
    career_db.upsert_preference("target_salary", 0)



# ==============================================================================
# TEST A, J, O, P: PROVIDER REGISTRATION, CONNECTION & BOUNDARY GUARDS
# ==============================================================================

def test_step3_remoteok_provider_registration_and_guards():
    """Tests A, J, O, P: Provider name, connection check, and read-only boundary."""
    provider = RemoteOKJobProvider()
    assert provider.provider_name() == "remoteok"

    # Connection check mock
    with patch("urllib.request.urlopen") as mock_open:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp
        mock_open.return_value = mock_resp

        status = provider.check_connection()
        assert status["status"] == "CONNECTED"
        assert status["connected"] is True
        assert status["provider"] == "remoteok"

    # Boundary guards: Apply and messaging must raise NotImplementedError
    with pytest.raises(NotImplementedError):
        provider.apply_to_job("https://remoteok.com/job/1")

    with pytest.raises(NotImplementedError):
        provider.submit_application_form({})

    with pytest.raises(NotImplementedError):
        provider.send_recruiter_message("recruiter_1", "Hello")


# ==============================================================================
# TEST B, C, I: MULTI-PROVIDER SEARCH, NORMALIZATION & RATE LIMIT
# ==============================================================================

def test_step3_multi_provider_search_and_normalization():
    """Tests B, C, I: Search across multiple providers with canonical normalization."""
    mock_linkedin_raw = [
        {
            "title": "Python Software Engineer",
            "company": "TechGlobal",
            "location": "Bangalore",
            "url": "https://linkedin.com/jobs/view/201",
        }
    ]

    mock_remoteok_raw = [
        {"legal": "RemoteOK API"},
        {
            "id": "rok_301",
            "position": "Python Cloud Developer",
            "company": "CloudNative Corp",
            "location": "Worldwide Remote",
            "salary_min": 110000,
            "salary_max": 140000,
            "tags": ["python", "aws", "docker"],
            "url": "https://remoteok.com/jobs/301",
            "description": "Building cloud infrastructure with Python.",
        }
    ]

    linkedin_prov = LinkedInJobProvider()
    remoteok_prov = RemoteOKJobProvider()

    with patch("backend.services.job_scraper.fetch_live_linkedin_jobs", return_value=mock_linkedin_raw), \
         patch("services.job_scraper.fetch_live_linkedin_jobs", return_value=mock_linkedin_raw), \
         patch("urllib.request.urlopen") as mock_open:

        mock_resp = MagicMock()
        mock_resp.read.return_value = json_bytes(mock_remoteok_raw)
        mock_resp.__enter__.return_value = mock_resp
        mock_open.return_value = mock_resp

        pipeline_res = run_job_pipeline(
            query="Python",
            providers=[linkedin_prov, remoteok_prov],
            persist_to_db=False,
            run_llm_ranking=False,
        )

        assert pipeline_res["success"] is True
        assert len(pipeline_res["providers"]) == 2
        assert len(pipeline_res["accepted_jobs"]) == 2

        providers_found = {j["provider"] for j in pipeline_res["accepted_jobs"]}
        assert "linkedin_scraper" in providers_found
        assert "remoteok" in providers_found

        # Assert RemoteOK normalization
        rok_job = next(j for j in pipeline_res["accepted_jobs"] if j["provider"] == "remoteok")
        assert rok_job["title"] == "Python Cloud Developer"
        assert rok_job["salary_min"] == 110000.0
        assert rok_job["remote_type"] == "remote"
        assert "aws" in rok_job["skills"]


# ==============================================================================
# TEST D, K: CROSS-PROVIDER DEDUPLICATION WITH PROVENANCE TRACKING
# ==============================================================================

def test_step3_cross_provider_deduplication_and_provenance():
    """Tests D & K: Exact same role from LinkedIn and RemoteOK merges into ONE canonical job retaining both sources."""
    mock_linkedin_raw = [
        {
            "title": "Senior Python Architect",
            "company": "ScaleAI",
            "location": "Remote",
            "url": "https://linkedin.com/jobs/view/401",
        }
    ]

    mock_remoteok_raw = [
        {
            "id": "rok_401",
            "position": "Senior Python Architect",
            "company": "ScaleAI",
            "location": "Worldwide Remote",
            "url": "https://remoteok.com/jobs/401",
            "description": "Leading Python AI architecture.",
        }
    ]

    linkedin_prov = LinkedInJobProvider()
    remoteok_prov = RemoteOKJobProvider()

    with patch("backend.services.job_scraper.fetch_live_linkedin_jobs", return_value=mock_linkedin_raw), \
         patch("services.job_scraper.fetch_live_linkedin_jobs", return_value=mock_linkedin_raw), \
         patch("urllib.request.urlopen") as mock_open:

        mock_resp = MagicMock()
        mock_resp.read.return_value = json_bytes(mock_remoteok_raw)
        mock_resp.__enter__.return_value = mock_resp
        mock_open.return_value = mock_resp

        pipeline_res = run_job_pipeline(
            query="Python",
            providers=[linkedin_prov, remoteok_prov],
            persist_to_db=False,
            run_llm_ranking=False,
        )

        # Exact same role -> merged into ONE accepted job
        assert len(pipeline_res["accepted_jobs"]) == 1
        accepted = pipeline_res["accepted_jobs"][0]
        assert accepted["company"] == "ScaleAI"

        # K: Provenance metadata retains both providers
        assert "source_providers" in accepted
        assert "linkedin_scraper" in accepted["source_providers"]
        assert "remoteok" in accepted["source_providers"]

        # Duplicate job captured in duplicate list
        assert len(pipeline_res["duplicate_jobs"]) == 1


# ==============================================================================
# TEST E & F: LOCATION AND TITLE DIFFERENTIATION
# ==============================================================================

def test_step3_location_and_title_differentiation():
    """Tests E & F: Same company but different role or different location must NOT be merged."""
    fixtures = [
        {
            "id": "f_1",
            "title": "DevOps Engineer",
            "company": "MegaCorp",
            "location": "Bangalore",
            "remote_type": "onsite",
            "description": "DevOps in Bangalore",
        },
        {
            "id": "f_2",
            "title": "DevOps Engineer",
            "company": "MegaCorp",
            "location": "Hyderabad",
            "remote_type": "onsite",
            "description": "DevOps in Hyderabad",
        },
        {
            "id": "f_3",
            "title": "Frontend Engineer",
            "company": "MegaCorp",
            "location": "Bangalore",
            "remote_type": "onsite",
            "description": "Frontend in Bangalore",
        },
    ]

    mock_prov = MockJobProvider(fixtures=fixtures)
    pipeline_res = run_job_pipeline(query="", provider=mock_prov, persist_to_db=False, run_llm_ranking=False)

    assert len(pipeline_res["accepted_jobs"]) == 3, "Different locations and different roles at same company must NOT be merged."


# ==============================================================================
# TEST G & H: PROVIDER FAILURE ISOLATION & TIMEOUT
# ==============================================================================

def test_step3_provider_failure_isolation():
    """Tests G & H: When RemoteOK fails/times out, LinkedIn search STILL returns jobs safely."""
    mock_linkedin_raw = [
        {
            "title": "Java Spring Developer",
            "company": "HCLTech",
            "location": "Noida",
            "url": "https://linkedin.com/jobs/view/501",
        }
    ]

    linkedin_prov = LinkedInJobProvider()
    failing_remoteok_prov = RemoteOKJobProvider()

    with patch("backend.services.job_scraper.fetch_live_linkedin_jobs", return_value=mock_linkedin_raw), \
         patch("services.job_scraper.fetch_live_linkedin_jobs", return_value=mock_linkedin_raw), \
         patch("urllib.request.urlopen", side_effect=Exception("Connection Timed Out")):

        pipeline_res = run_job_pipeline(
            query="Java",
            providers=[linkedin_prov, failing_remoteok_prov],
            persist_to_db=False,
            run_llm_ranking=False,
        )

        # Assert LinkedIn succeeded and jobs were preserved
        assert len(pipeline_res["accepted_jobs"]) == 1
        assert pipeline_res["accepted_jobs"][0]["company"] == "HCLTech"

        # Assert Failure Isolation recorded in providers_status
        assert pipeline_res["providers_status"]["linkedin_scraper"] == "SUCCESS"
        assert "FAILED" in pipeline_res["providers_status"]["remoteok"]
        assert len(pipeline_res["errors"]) >= 1


# ==============================================================================
# TEST M & N: MALFORMED & EMPTY PROVIDER RESPONSES
# ==============================================================================

def test_step3_malformed_and_empty_responses():
    """Tests M & N: Non-list or empty provider responses handled gracefully."""
    remoteok_prov = RemoteOKJobProvider()

    # M: Non-list API response
    with patch("urllib.request.urlopen") as mock_open:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"error": "Invalid API format"}'
        mock_resp.__enter__.return_value = mock_resp
        mock_open.return_value = mock_resp

        jobs = remoteok_prov.search_jobs("Go")
        assert jobs == []

    # N: Empty list API response
    with patch("urllib.request.urlopen") as mock_open:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'[]'
        mock_resp.__enter__.return_value = mock_resp
        mock_open.return_value = mock_resp

        jobs = remoteok_prov.search_jobs("Rust")
        assert jobs == []


def json_bytes(obj) -> bytes:
    import json
    return json.dumps(obj).encode("utf-8")
