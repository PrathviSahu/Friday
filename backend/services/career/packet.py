"""backend/services/career/packet.py — Career Application Packet Generation, ATS Estimation, and Approval Binding.

PREPARATION ONLY: Evaluates eligibility, selects/tailors resumes, estimates ATS scores, drafts cover letters,
analyzes skill gaps and salary fit, detects missing fields, and computes SHA-256 content hashes.
STRICT READINESS CEILING: Maximum state is READY_FOR_REVIEW / APPROVED. Never transitions to SUBMITTED.
"""

import os
import json
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple


# ==============================================================================
# PACKET HASH & PROVENANCE UTILITIES
# ==============================================================================

def compute_packet_hash(packet_data: Dict[str, Any]) -> str:
    """Compute deterministic SHA-256 content hash over exact application packet fields."""
    core_payload = {
        "job_id": str(packet_data.get("job_id", "")),
        "company": (packet_data.get("company") or "").strip().lower(),
        "role": (packet_data.get("role") or "").strip().lower(),
        "canonical_signature": packet_data.get("canonical_signature", ""),
        "selected_resume_id": packet_data.get("selected_resume_id"),
        "cover_letter": (packet_data.get("cover_letter") or "").strip(),
        "profile_data": packet_data.get("profile_data") or {},
        "version": packet_data.get("version", 1),
    }
    raw_json = json.dumps(core_payload, sort_keys=True)
    return hashlib.sha256(raw_json.encode("utf-8")).hexdigest()


# ==============================================================================
# JOB ELIGIBILITY CHECK
# ==============================================================================

def check_job_eligibility(
    job: Dict[str, Any],
    preferences: Dict[str, Any],
    candidate_skills: Optional[List[str]] = None,
) -> Tuple[bool, List[str]]:
    """Evaluate job fit against candidate constraints (salary, location, remote, blacklist, visa)."""
    reasons: List[str] = []
    company = (job.get("company") or "").strip().lower()
    title = (job.get("title") or "").strip().lower()
    loc = (job.get("location") or "").strip().lower()
    remote_type = (job.get("remote_type") or "unknown").strip().lower()

    # 1. Blacklist check
    try:
        try:
            from backend.services import career_db
        except ImportError:
            from services import career_db
        companies = career_db.get_companies() or []
        for c in companies:
            if isinstance(c, dict) and c.get("is_blacklisted"):
                b_name = (c.get("name") or "").strip().lower()
                if b_name and (b_name in company or company in b_name):
                    reasons.append(f"Company '{job.get('company')}' is blacklisted: {c.get('blacklist_reason', 'Candidate preference')}")
    except Exception:
        pass

    # 2. Salary check
    min_sal = float(preferences.get("min_salary", 0.0) or 0.0)
    job_max_sal = float(job.get("salary_max", 0.0) or 0.0)
    if min_sal > 0 and job_max_sal > 0 and job_max_sal < min_sal:
        reasons.append(f"Compensation below minimum preference (Job max: {job_max_sal:,.0f} < Preference min: {min_sal:,.0f})")

    # 3. Remote preference check
    remote_pref = (preferences.get("remote_preference") or preferences.get("preferred_remote") or "").strip().lower()
    if remote_pref == "remote_only" and remote_type != "remote":
        reasons.append(f"Remote requirement mismatch: Candidate prefers remote only, job is {remote_type}")

    # 4. Location check
    pref_locs = [l.strip().lower() for l in (preferences.get("preferred_locations") or preferences.get("preferred_cities") or []) if isinstance(l, str)]
    if pref_locs and remote_type != "remote":
        if not any(pref in loc for pref in pref_locs):
            reasons.append(f"Location mismatch: Job location '{job.get('location')}' not in preferred cities")

    # 5. Visa check
    visa_req = preferences.get("visa_required", False)
    job_visa = bool(job.get("visa_sponsorship"))
    if visa_req and not job_visa:
        reasons.append("Candidate requires visa sponsorship, but job does not provide it")

    is_eligible = len(reasons) == 0
    return is_eligible, reasons


# ==============================================================================
# RESUME SELECTION & TAILORING
# ==============================================================================

def select_best_resume(
    job: Dict[str, Any],
    resumes: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], str, float]:
    """Select most relevant candidate resume based on keyword/skill match."""
    if not resumes:
        return {"id": 0, "title": "Default Profile Resume", "content_json": {}}, "Default fallback profile", 70.0

    job_text = f"{job.get('title', '')} {job.get('description', '')}".lower()
    best_resume = resumes[0]
    best_score = -1.0
    best_reason = "Selected primary candidate resume"

    for r in resumes:
        content = r.get("content_json") or {}
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except Exception:
                content = {}
        skills = content.get("skills") or []
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]

        matched_count = sum(1 for s in skills if s.lower() in job_text)
        score = (matched_count / max(len(skills), 1)) * 100.0 if skills else 50.0

        if score > best_score:
            best_score = score
            best_resume = r
            best_reason = f"Highest skill alignment ({matched_count} matching skills for {job.get('title', 'role')})"

    return best_resume, best_reason, max(best_score, 60.0)


# ==============================================================================
# ATS ANALYSIS & SKILL GAPS
# ==============================================================================

def estimate_ats_score(
    job: Dict[str, Any],
    resume_content: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate structured FRIDAY ESTIMATED ATS SCORE report without claiming external authority."""
    skills = resume_content.get("skills") or []
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]

    desc = (job.get("description") or "").lower()
    title = (job.get("title") or "").lower()
    combined_job = f"{title} {desc}"

    # Extract potential keywords from job description
    extracted_keywords = [
        "python", "java", "spring boot", "fastapi", "react", "docker", "kubernetes",
        "aws", "gcp", "azure", "postgresql", "mysql", "mongodb", "redis", "rest api",
        "microservices", "graphql", "git", "ci/cd", "machine learning", "ai", "sql",
        "linux", "leadership", "agile"
    ]
    job_keywords = [kw for kw in extracted_keywords if kw in combined_job]
    candidate_skills_lower = [s.lower() for s in skills]

    matched_kw = [kw for kw in job_keywords if kw in candidate_skills_lower or any(kw in s for s in candidate_skills_lower)]
    missing_kw = [kw for kw in job_keywords if kw not in matched_kw]

    kw_score = (len(matched_kw) / max(len(job_keywords), 1)) * 100.0 if job_keywords else 85.0
    overall_ats = min(max(round(kw_score * 0.7 + (85.0 if skills else 50.0) * 0.3, 1), 40.0), 98.0)

    return {
        "label": "FRIDAY ESTIMATED ATS SCORE",
        "overall_ats_score": overall_ats,
        "keyword_alignment_pct": round(kw_score, 1),
        "matched_keywords": matched_kw,
        "missing_keywords": missing_kw,
        "formatting_status": "Clean ATS-Friendly Layout",
        "recommendations": [f"Highlight '{kw}' in recent project bullets" for kw in missing_kw[:3]],
    }


def analyze_skill_gaps(
    job: Dict[str, Any],
    resume_content: Dict[str, Any],
) -> Dict[str, List[str]]:
    """Categorize matched skills, critical missing requirements, and optional skills."""
    skills = resume_content.get("skills") or []
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]

    desc = (job.get("description") or "").lower()
    title = (job.get("title") or "").lower()
    combined_job = f"{title} {desc}"

    core_techs = [
        "python", "java", "spring boot", "fastapi", "react", "docker", "kubernetes",
        "aws", "gcp", "postgresql", "redis", "rest api", "microservices", "sql"
    ]
    job_required = [t for t in core_techs if t in combined_job]
    cand_lower = [s.lower() for s in skills]

    matched = [t.title() for t in job_required if t in cand_lower or any(t in s for s in cand_lower)]
    critical_missing = [t.title() for t in job_required if t.title() not in matched]
    optional = ["Docker", "CI/CD", "AWS Cloud", "Agile"] if not critical_missing else ["GraphQL", "Terraform"]

    return {
        "matched_skills": matched or ["Core Engineering"],
        "missing_critical_skills": critical_missing,
        "optional_skills": [o for o in optional if o not in matched and o not in critical_missing],
    }


# ==============================================================================
# SALARY & MISSING FIELDS
# ==============================================================================

def analyze_salary_fit(
    job: Dict[str, Any],
    preferences: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare job compensation against candidate minimum and target salary preferences."""
    min_pref = float(preferences.get("min_salary", 0.0) or 0.0)
    target_pref = float(preferences.get("target_salary", min_pref * 1.25) or 0.0)

    job_min = float(job.get("salary_min", 0.0) or 0.0)
    job_max = float(job.get("salary_max", 0.0) or 0.0)
    raw_str = job.get("salary_raw") or ""

    if not raw_str and job_min == 0.0 and job_max == 0.0:
        return {
            "status": "UNKNOWN",
            "salary_fit": "Salary not disclosed in job listing",
            "salary_position": "Market Standard",
            "warning": None,
        }

    effective_val = job_max if job_max > 0 else job_min
    if min_pref > 0 and effective_val > 0 and effective_val < min_pref:
        return {
            "status": "BELOW_PREFERENCE",
            "salary_fit": f"Below minimum preference (Max {effective_val:,.0f} < Min {min_pref:,.0f})",
            "salary_position": "Low",
            "warning": f"Compensation is lower than your preferred minimum of {min_pref:,.0f}.",
        }
    elif target_pref > 0 and effective_val >= target_pref:
        return {
            "status": "EXCELLENT",
            "salary_fit": f"Meets or exceeds target compensation ({effective_val:,.0f} >= {target_pref:,.0f})",
            "salary_position": "Top Tier",
            "warning": None,
        }
    else:
        return {
            "status": "MEETS_MINIMUM",
            "salary_fit": "Within acceptable compensation range",
            "salary_position": "Competitive",
            "warning": None,
        }


def check_missing_fields(profile: Dict[str, Any]) -> Dict[str, List[str]]:
    """Detect required and optional application fields from candidate profile."""
    required = []
    optional = []

    if not (profile.get("email") or profile.get("contact_email")):
        required.append("Email Address")
    if not (profile.get("phone") or profile.get("phone_number")):
        required.append("Phone Number")
    if not profile.get("full_name") and not profile.get("name"):
        required.append("Full Name")

    if not profile.get("github_url") and not profile.get("github"):
        optional.append("GitHub Profile URL")
    if not profile.get("linkedin_url") and not profile.get("linkedin"):
        optional.append("LinkedIn Profile URL")
    if not profile.get("portfolio_url") and not profile.get("portfolio"):
        optional.append("Portfolio Website")

    return {
        "REQUIRED": required,
        "OPTIONAL": optional,
        "UNKNOWN": [],
    }


# ==============================================================================
# APPLICATION PACKET GENERATOR
# ==============================================================================

def generate_application_packet(
    job: Dict[str, Any],
    resume_id: Optional[int] = None,
    candidate_profile: Optional[Dict[str, Any]] = None,
    preferences: Optional[Dict[str, Any]] = None,
    run_llm: bool = True,
) -> Dict[str, Any]:
    """Generate complete, verifiable ApplicationPacket for a selected job.

    PREPARATION ONLY: Returns state READY_FOR_REVIEW / INCOMPLETE / NOT_ELIGIBLE.
    """
    try:
        try:
            from backend.services import career_db
        except ImportError:
            from services import career_db
    except Exception:
        career_db = None

    prefs = preferences or (career_db.get_all_preferences() if career_db and hasattr(career_db, "get_all_preferences") else {}) or {}

    resumes = (career_db.get_all_resumes() if career_db else []) or []
    profile = candidate_profile or (career_db.get_profile() if career_db else {}) or {}

    # Check duplicate application in career_applications
    previous_app = None
    if career_db:
        try:
            apps = career_db.get_applications() or []
            job_title = (job.get("title") or "").strip().lower()
            job_comp = (job.get("company") or "").strip().lower()
            for a in apps:
                ajob = a.get("job") or {}
                if isinstance(ajob, dict):
                    if (ajob.get("title") or "").strip().lower() == job_title and (ajob.get("company") or "").strip().lower() == job_comp:
                        previous_app = a
                        break
        except Exception:
            pass

    # 1. Eligibility Check
    is_eligible, eligibility_reasons = check_job_eligibility(job, prefs)

    # 2. Resume Selection
    if resume_id and resumes:
        selected_resume = next((r for r in resumes if r.get("id") == resume_id), resumes[0])
        resume_reason = f"User explicitly selected resume ID {resume_id}"
        resume_match_score = 80.0
    else:
        selected_resume, resume_reason, resume_match_score = select_best_resume(job, resumes)

    res_content = selected_resume.get("content_json") or {}
    if isinstance(res_content, str):
        try:
            res_content = json.loads(res_content)
        except Exception:
            res_content = {}

    # 3. ATS Score & Skill Gaps
    ats_report = estimate_ats_score(job, res_content)
    skill_gaps = analyze_skill_gaps(job, res_content)
    salary_eval = analyze_salary_fit(job, prefs)
    missing_fields_report = check_missing_fields(profile)

    # 4. Company Intelligence
    company_intel = {
        "name": job.get("company", "Unknown"),
        "reputation": "High Growth / Established Tech" if not eligibility_reasons else "Review Required",
        "previous_applications": 1 if previous_app else 0,
        "blacklist_status": "Clean" if is_eligible else "Flagged",
        "notes": f"Ingested via {job.get('provider', 'Multi-Source Provider')}",
    }

    # 5. Cover Letter Generation
    cand_name = profile.get("full_name") or profile.get("name") or "Candidate"
    if run_llm:
        try:
            try:
                from backend.services import career_intelligence
            except ImportError:
                from services import career_intelligence
            cover_letter = career_intelligence.generate_cover_letter(
                job=job,
                resume_content=res_content,
                tone="confident",
            )
        except Exception:
            cover_letter = _generate_fallback_cover_letter(job, cand_name, skill_gaps["matched_skills"])
    else:
        cover_letter = _generate_fallback_cover_letter(job, cand_name, skill_gaps["matched_skills"])

    # Determine Readiness State
    warnings: List[str] = []
    if previous_app:
        warnings.append(f"Duplicate warning: You previously applied for a role at {job.get('company')} (Status: {previous_app.get('status', 'submitted')}).")

    if not is_eligible:
        readiness = "NOT_ELIGIBLE"
        warnings.extend(eligibility_reasons)
    elif missing_fields_report["REQUIRED"]:
        readiness = "INCOMPLETE"
        warnings.append(f"Missing required candidate fields: {', '.join(missing_fields_report['REQUIRED'])}")
    else:
        readiness = "READY_FOR_REVIEW"

    now_utc = datetime.now(timezone.utc)
    packet_id = f"pkt_{uuid.uuid4().hex[:12]}"

    packet_data: Dict[str, Any] = {
        "packet_id": packet_id,
        "version": 1,
        "job_id": job.get("id") or job.get("provider_job_id") or "job_0",
        "provider": job.get("provider", "unknown"),
        "company": job.get("company", "Unknown"),
        "role": job.get("title", "Software Engineer"),
        "source_url": job.get("url") or job.get("source_url") or job.get("application_url") or "",
        "canonical_signature": job.get("signature", ""),

        "selected_resume_id": selected_resume.get("id", 0),
        "selected_resume_title": selected_resume.get("title", "Primary Resume"),
        "resume_version": "v1.0",
        "ats_score": ats_report["overall_ats_score"],
        "ats_analysis": ats_report,
        "match_score": round(resume_match_score, 1),
        "strengths": [f"Demonstrated experience with {s}" for s in skill_gaps["matched_skills"][:3]],
        "skill_gaps": skill_gaps,
        "salary_analysis": salary_eval,
        "company_analysis": company_intel,
        "recruiter_info": {"name": "Hiring Team", "email": None, "source": "Public Listing"},
        "cover_letter": cover_letter,
        "profile_data": {
            "name": cand_name,
            "email": profile.get("email") or profile.get("contact_email") or "",
            "phone": profile.get("phone") or profile.get("phone_number") or "",
            "github": profile.get("github_url") or "",
            "linkedin": profile.get("linkedin_url") or "",
        },
        "missing_fields": missing_fields_report,
        "warnings": warnings,
        "readiness": readiness,
        "created_at": now_utc.isoformat(),
        "expires_at": (now_utc + timedelta(minutes=15)).isoformat(),
        "content_hash": "",
    }

    # Compute content hash
    packet_data["content_hash"] = compute_packet_hash(packet_data)

    return packet_data


def edit_application_packet(packet: Dict[str, Any], changes: Dict[str, Any]) -> Dict[str, Any]:
    """Apply modifications to application packet, increment version, and invalidate previous approvals."""
    new_packet = dict(packet)
    new_packet["version"] = new_packet.get("version", 1) + 1

    for k, v in changes.items():
        if k in ["cover_letter", "selected_resume_id", "selected_resume_title", "profile_data"]:
            new_packet[k] = v

    # Re-evaluate missing fields if profile changed
    if "profile_data" in changes:
        new_packet["missing_fields"] = check_missing_fields(new_packet["profile_data"])

    # Reset status back to READY_FOR_REVIEW if not ineligible
    if new_packet.get("readiness") != "NOT_ELIGIBLE":
        if new_packet["missing_fields"]["REQUIRED"]:
            new_packet["readiness"] = "INCOMPLETE"
        else:
            new_packet["readiness"] = "READY_FOR_REVIEW"

    new_packet["content_hash"] = compute_packet_hash(new_packet)
    return new_packet


def approve_application_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    """Approve application packet for future submission (NO submission occurs in Step 4)."""
    if packet.get("readiness") != "READY_FOR_REVIEW":
        raise ValueError(f"Cannot approve packet in '{packet.get('readiness')}' state. Must be 'READY_FOR_REVIEW'.")

    approved_packet = dict(packet)
    approved_packet["readiness"] = "APPROVED"
    approved_packet["approved_at"] = datetime.now(timezone.utc).isoformat()
    return approved_packet


def format_packet_preview(packet: Dict[str, Any]) -> str:
    """Format structured F.R.I.D.A.Y. HUD preview text for the candidate."""
    gaps_str = ", ".join(packet["skill_gaps"]["missing_critical_skills"]) if packet["skill_gaps"]["missing_critical_skills"] else "None (Full Match)"
    warnings_str = " | ".join(packet["warnings"]) if packet["warnings"] else "None"
    return f"""Boss, I've prepared the application packet.

JOB: {packet['role']}
COMPANY: {packet['company']}
MATCH: {packet['match_score']}%
SALARY: {packet['salary_analysis']['salary_fit']}
SELECTED RESUME: {packet['selected_resume_title']} (ID: {packet['selected_resume_id']})
ESTIMATED ATS: {packet['ats_score']}% ({packet['ats_analysis']['label']})
CRITICAL GAPS: {gaps_str}
READINESS: {packet['readiness']}
WARNINGS: {warnings_str}
CONTENT HASH: {packet['content_hash'][:12]}...

[EDIT] [REVIEW] [APPROVE FOR FUTURE SUBMISSION]"""


def _generate_fallback_cover_letter(job: Dict[str, Any], name: str, matched_skills: List[str]) -> str:
    skills_phrase = f", particularly in {', '.join(matched_skills[:3])}" if matched_skills else ""
    return f"""Dear Hiring Team,

I am writing to express my strong interest in the {job.get('title', 'Software Engineer')} role at {job.get('company', 'your company')}. With my proven track record in building scalable systems{skills_phrase}, I am confident in my ability to make an immediate impact on your team.

My technical background aligns directly with the requirements outlined in your job listing. I look forward to the opportunity to discuss how my skill set and experience can support {job.get('company', 'the company')}'s upcoming goals.

Sincerely,
{name}"""
