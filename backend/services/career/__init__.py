"""backend/services/career/__init__.py — Canonical Multi-Source Career Integration Subsystem.
"""

from backend.services.career.config import (
    JOB_SEARCH_ENABLED,
    MAX_RESULTS,
    DEDUP_ENABLED,
    MIN_MATCH_SCORE,
    DRY_RUN,
)
from backend.services.career.provider import (
    BaseJobProvider,
    MockJobProvider,
    LinkedInJobProvider,
    ExistingJobScraperAdapter,
    parse_salary_raw,
    normalize_remote_status,
    normalize_experience_level,
    compute_job_signature,
)
from backend.services.career.pipeline import (
    run_job_pipeline,
    get_existing_signatures_from_db,
    get_blacklisted_companies_map,
)

__all__ = [
    "JOB_SEARCH_ENABLED",
    "MAX_RESULTS",
    "DEDUP_ENABLED",
    "MIN_MATCH_SCORE",
    "DRY_RUN",
    "BaseJobProvider",
    "MockJobProvider",
    "LinkedInJobProvider",
    "ExistingJobScraperAdapter",
    "parse_salary_raw",
    "normalize_remote_status",
    "normalize_experience_level",
    "compute_job_signature",
    "run_job_pipeline",
    "get_existing_signatures_from_db",
    "get_blacklisted_companies_map",
]

