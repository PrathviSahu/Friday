"""backend/services/career/pipeline.py — Canonical Multi-Source Career Ingestion, Deduplication, Filtering, and Ranking Pipeline.

Orchestrates:
Multi-Provider Ingestion ──► Normalize ──► Deduplicate (with Provenance) ──► Preference Filter ──► Blacklist Filter ──► Rank ──► Persist
"""

import json
from typing import Dict, Any, List, Optional, Union
from backend.services.career.config import DEDUP_ENABLED, MIN_MATCH_SCORE
from backend.services.career.provider import BaseJobProvider, MockJobProvider


def get_existing_signatures_from_db() -> set:
    """Retrieve all existing SHA-256 job signatures from career_jobs table in friday_brain.db."""
    try:
        try:
            from backend.services import career_db
        except ImportError:
            from services import career_db

        jobs = career_db.get_jobs() or []
        signatures = set()
        for j in jobs:
            if isinstance(j, dict):
                match_json = j.get("match_json") or {}
                if isinstance(match_json, str):
                    try:
                        match_json = json.loads(match_json)
                    except Exception:
                        match_json = {}
                sig = j.get("signature") or (match_json.get("signature") if isinstance(match_json, dict) else None)
                if sig:
                    signatures.add(sig)
                # Compute fallback signature from existing title/company/location
                comp = j.get("company", "")
                title = j.get("title", "")
                loc = j.get("location", "")
                remote = j.get("remote_type", "")
                if comp and title:
                    from backend.services.career.provider import compute_job_signature
                    signatures.add(compute_job_signature(comp, title, loc, remote))
        return signatures

    except Exception as exc:
        print(f"[CareerPipeline] Failed to load DB signatures: {exc}")
        return set()


def get_blacklisted_companies_map() -> Dict[str, str]:
    """Retrieve map of blacklisted company names -> blacklist_reason from career_companies table."""
    try:
        try:
            from backend.services import career_db
        except ImportError:
            from services import career_db

        companies = career_db.get_companies() or []
        bl_map = {}
        for c in companies:
            if isinstance(c, dict) and c.get("is_blacklisted"):
                name = (c.get("name") or "").strip().lower()
                reason = c.get("blacklist_reason") or "Company blacklisted by candidate."
                if name:
                    bl_map[name] = reason
        return bl_map
    except Exception as exc:
        print(f"[CareerPipeline] Failed to load blacklisted companies: {exc}")
        return {}


def run_job_pipeline(
    query: str,
    provider: Optional[BaseJobProvider] = None,
    providers: Optional[List[BaseJobProvider]] = None,
    filters: Optional[Dict[str, Any]] = None,
    persist_to_db: bool = True,
    run_llm_ranking: bool = True,
) -> Dict[str, Any]:
    """Execute complete canonical multi-source job pipeline:

    Ingest from Providers ──► Normalize ──► Deduplicate ──► Preference Filter ──► Blacklist Filter ──► Rank ──► Persist
    """
    if providers is not None:
        effective_providers = providers
    elif provider is not None:
        effective_providers = [provider]
    else:
        effective_providers = [MockJobProvider()]

    filters = filters or {}

    accepted_jobs: List[Dict[str, Any]] = []
    filtered_jobs: List[Dict[str, Any]] = []
    duplicate_jobs: List[Dict[str, Any]] = []
    errors: List[str] = []
    providers_status: Dict[str, str] = {}

    all_raw_jobs: List[Dict[str, Any]] = []

    # Step 1: Ingest raw jobs with Provider Failure Isolation
    for prov in effective_providers:
        p_name = prov.provider_name()
        try:
            p_jobs = prov.search_jobs(query=query, filters=filters)
            providers_status[p_name] = "SUCCESS"
            all_raw_jobs.extend(p_jobs)
        except Exception as exc:
            err_msg = f"Provider '{p_name}' search failed: {str(exc)}"
            errors.append(err_msg)
            providers_status[p_name] = f"FAILED: {str(exc)}"

    # Load existing database signatures & blacklist map
    seen_signatures = get_existing_signatures_from_db() if DEDUP_ENABLED else set()
    blacklisted_map = get_blacklisted_companies_map()

    # Map of accepted jobs by signature for cross-provider provenance merging
    accepted_by_signature: Dict[str, Dict[str, Any]] = {}

    # Load user career preferences
    try:
        try:
            from backend.services import career_db
        except ImportError:
            from services import career_db
        user_prefs = career_db.get_preferences() or {}
        resumes = career_db.get_all_resumes() or []
        primary_resume = resumes[0] if resumes else {"title": "Default Resume", "content_json": {}}
    except Exception:
        user_prefs = {}
        primary_resume = {"title": "Default Resume", "content_json": {}}

    min_sal_pref = float(user_prefs.get("min_salary", 0.0) or 0.0)
    remote_pref = (user_prefs.get("remote_preference") or "").strip().lower()
    target_locations = [loc.strip().lower() for loc in (user_prefs.get("preferred_locations") or []) if isinstance(loc, str)]

    for raw in all_raw_jobs:
        # Step 2: Normalize into Canonical Schema
        try:
            norm_job = raw if (isinstance(raw, dict) and "signature" in raw) else MockJobProvider().normalize_job(raw)
        except Exception as norm_err:
            errors.append(f"Normalization failed for raw job: {norm_err}")
            continue

        sig = norm_job["signature"]
        comp_name = norm_job["company"].strip().lower()

        # Step 3: Deduplication & Cross-Provider Provenance Tracking
        if DEDUP_ENABLED and sig in seen_signatures:
            norm_job["filter_reason"] = "DUPLICATE_JOB_SIGNATURE"
            # If matching an already accepted job in current pipeline run, merge source providers
            if sig in accepted_by_signature:
                existing_accepted = accepted_by_signature[sig]
                sources = existing_accepted.setdefault("source_providers", [existing_accepted["provider"]])
                if norm_job["provider"] not in sources:
                    sources.append(norm_job["provider"])
            duplicate_jobs.append(norm_job)
            continue

        # Step 4: Blacklist Filter
        is_bl = False
        for bl_name, bl_reason in blacklisted_map.items():
            if bl_name in comp_name or comp_name in bl_name:
                norm_job["filter_reason"] = f"BLACKLISTED: {bl_reason}"
                filtered_jobs.append(norm_job)
                is_bl = True
                break
        if is_bl:
            continue

        # Step 5: Preference Filter
        if min_sal_pref > 0 and norm_job["salary_max"] > 0 and norm_job["salary_max"] < min_sal_pref:
            norm_job["filter_reason"] = f"SALARY_BELOW_MINIMUM ({norm_job['salary_max']} < {min_sal_pref})"
            filtered_jobs.append(norm_job)
            continue

        if remote_pref == "remote_only" and norm_job["remote_type"] != "remote":
            norm_job["filter_reason"] = f"REMOTE_REQUIRED (Job is {norm_job['remote_type']})"
            filtered_jobs.append(norm_job)
            continue

        if target_locations and norm_job["remote_type"] != "remote":
            loc_match = any(loc in norm_job["location"].lower() for loc in target_locations)
            if not loc_match:
                norm_job["filter_reason"] = f"LOCATION_MISMATCH (Location '{norm_job['location']}' not in preferred)"
                filtered_jobs.append(norm_job)
                continue

        # Step 6: Ranking & Intelligence Integration
        if run_llm_ranking:
            try:
                try:
                    from backend.services import career_intelligence
                except ImportError:
                    from services import career_intelligence

                resume_content = primary_resume.get("content_json") or {}
                if isinstance(resume_content, str):
                    try:
                        resume_content = json.loads(resume_content)
                    except Exception:
                        resume_content = {}

                match_report = career_intelligence.analyze_job_match(
                    job=norm_job,
                    resume_content=resume_content,
                    preferences=user_prefs,
                )
                norm_job["match_score"] = float(match_report.get("overall_score", 75))
                norm_job["match_details"] = match_report
            except Exception as rank_err:
                norm_job["match_score"] = 50.0
                norm_job["match_details"] = {"reasoning": f"LLM ranking fallback: {rank_err}"}
        else:
            norm_job["match_score"] = 75.0
            norm_job["match_details"] = {"reasoning": "Standard ranking (LLM bypass mode)"}

        # Step 7: Persistence to career_db.py
        if persist_to_db:
            try:
                try:
                    from backend.services import career_db
                except ImportError:
                    from services import career_db

                job_data = {
                    "title": norm_job["title"],
                    "company": norm_job["company"],
                    "description": norm_job["description"],
                    "source": norm_job["provider"],
                    "url": norm_job["url"],
                    "location": norm_job["location"],
                    "remote_type": norm_job["remote_type"],
                    "salary_raw": norm_job["salary_raw"],
                    "salary_min": norm_job["salary_min"],
                    "salary_max": norm_job["salary_max"],
                    "experience_required": norm_job["experience_level"],
                    "visa_sponsorship": 1 if norm_job["visa_sponsorship"] else 0,
                    "match_json": json.dumps(norm_job.get("match_details", {})),
                    "match_score": norm_job.get("match_score", 0.0),
                }

                if hasattr(career_db, "create_job"):
                    job_db_id = career_db.create_job(job_data)
                else:
                    job_db_id, _ = career_db.upsert_scraped_job(job_data)
                norm_job["db_job_id"] = job_db_id
            except Exception as db_err:
                errors.append(f"DB Persistence failed for '{norm_job['title']}': {db_err}")

        # Add to seen signatures and provenance map
        seen_signatures.add(sig)
        norm_job["source_providers"] = [norm_job["provider"]]
        accepted_by_signature[sig] = norm_job
        accepted_jobs.append(norm_job)

    # Sort accepted jobs by match_score descending
    accepted_jobs.sort(key=lambda x: x.get("match_score", 0.0), reverse=True)

    return {
        "success": len(errors) == 0 or len(accepted_jobs) > 0,
        "providers": [p.provider_name() for p in effective_providers],
        "providers_status": providers_status,
        "query": query,
        "accepted_jobs": accepted_jobs,
        "filtered_jobs": filtered_jobs,
        "duplicate_jobs": duplicate_jobs,
        "errors": errors,
        "stats": {
            "total_ingested": len(all_raw_jobs),
            "accepted": len(accepted_jobs),
            "filtered": len(filtered_jobs),
            "duplicates": len(duplicate_jobs),
        },
    }
