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
from backend.services.career.remoteok_provider import RemoteOKJobProvider
from backend.services.career.pipeline import (
    run_job_pipeline,
    get_existing_signatures_from_db,
    get_blacklisted_companies_map,
)
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
from backend.services.career.portal import (
    BaseApplicationPortal,
    MockApplicationPortal,
    LinkedInApplicationPortal,
    PortalAutomationEngine,
    PortalSecurityError,
    FieldSensitivity,
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
    "RemoteOKJobProvider",
    "parse_salary_raw",
    "normalize_remote_status",
    "normalize_experience_level",
    "compute_job_signature",
    "run_job_pipeline",
    "get_existing_signatures_from_db",
    "get_blacklisted_companies_map",
    "generate_application_packet",
    "edit_application_packet",
    "approve_application_packet",
    "compute_packet_hash",
    "check_job_eligibility",
    "select_best_resume",
    "estimate_ats_score",
    "analyze_skill_gaps",
    "analyze_salary_fit",
    "check_missing_fields",
    "format_packet_preview",
    "BaseApplicationPortal",
    "MockApplicationPortal",
    "LinkedInApplicationPortal",
    "PortalAutomationEngine",
    "PortalSecurityError",
    "FieldSensitivity",
]





