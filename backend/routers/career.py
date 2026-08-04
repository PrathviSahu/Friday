"""
career.py — Career Intelligence Center: FastAPI Router.

All endpoints under /api/career/*
"""

import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from auth import require_boss
from ratelimit import rate_limit

from services.career_db import (
    get_all_preferences, upsert_preference, update_preferences_bulk,
    get_profile, update_profile_bulk,
    get_all_resumes, get_resume, create_resume, update_resume,
    duplicate_resume, set_recommended_resume,
    get_jobs, get_job, create_job, update_job,
    get_applications, create_application, update_application,
    save_cover_letter, get_cover_letters,
    get_recruiters, create_recruiter, update_recruiter,
    get_interviews, create_interview, update_interview,
    get_companies, upsert_company, blacklist_company,
    get_activity_log, log_activity,
    get_dashboard_stats, get_analytics,
)
from services.career_intelligence import (
    analyze_job_match, generate_cover_letter, generate_interview_questions,
    generate_daily_briefing, learn_from_feedback,
    generate_skill_gap_analysis, get_career_recommendations,
)
from services.job_scraper import fetch_live_linkedin_jobs

# Career OS is fully personal data + expensive Groq calls: owner-only router.
router = APIRouter(
    prefix="/api/career",
    tags=["career"],
    dependencies=[Depends(require_boss)],
)

# Shared limiter for the Groq-consuming AI endpoints (credits cost money).
_ai_limit = rate_limit(limit=20, window=60)


# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ══════════════════════════════════════════════════════════════════════════════

class PreferencesUpdate(BaseModel):
    updates: dict
    source: str = "user"


class ProfileUpdate(BaseModel):
    fields: dict


class ResumeCreate(BaseModel):
    title: str
    content: dict = {}


class ResumeUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[dict] = None
    ats_score: Optional[float] = None
    is_archived: Optional[int] = None
    is_recommended: Optional[int] = None


class JobCreate(BaseModel):
    title: str
    company: str
    description: str = ""
    source: str = "manual"
    url: str = ""
    location: str = ""
    remote_type: str = "unknown"
    salary_raw: str = ""
    salary_min: float = 0
    salary_max: float = 0
    experience_required: str = ""
    visa_sponsorship: int = 0
    deadline: str = ""


class JobStatusUpdate(BaseModel):
    status: str
    notes: str = ""


class ApplicationCreate(BaseModel):
    job_id: int
    resume_id: Optional[int] = None


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    resume_id: Optional[int] = None
    notes: Optional[str] = None
    follow_up_date: Optional[str] = None
    deadline: Optional[str] = None
    recruiter_id: Optional[int] = None
    salary_offered: Optional[float] = None
    offer_details: Optional[str] = None


class AnalyzeJobRequest(BaseModel):
    job_id: int
    resume_id: Optional[int] = None


class CoverLetterRequest(BaseModel):
    job_id: int
    resume_id: Optional[int] = None
    tone: str = "professional"


class RecruiterCreate(BaseModel):
    name: str
    company: str = ""
    email: str = ""
    linkedin: str = ""
    phone: str = ""
    notes: str = ""


class RecruiterUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    linkedin: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    last_contact: Optional[str] = None


class InterviewCreate(BaseModel):
    application_id: int
    stage: str = "phone"
    scheduled_at: str = ""
    meeting_link: str = ""
    interviewer_name: str = ""
    notes: str = ""


class InterviewUpdate(BaseModel):
    stage: Optional[str] = None
    scheduled_at: Optional[str] = None
    meeting_link: Optional[str] = None
    interviewer_name: Optional[str] = None
    notes: Optional[str] = None
    outcome: Optional[str] = None


class CompanyBlacklist(BaseModel):
    name: str
    reason: str = "User preference"


class LearnRequest(BaseModel):
    text: str


class InterviewQuestionsRequest(BaseModel):
    job_id: int
    resume_id: Optional[int] = None


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/dashboard", dependencies=[Depends(_ai_limit)])
def get_dashboard():
    """Dashboard summary: stats + briefing + recommendations + activity."""
    stats = get_dashboard_stats()
    prefs = get_all_preferences()
    activity = get_activity_log(10)
    briefing = generate_daily_briefing(stats, prefs)
    recommendations = get_career_recommendations(stats, prefs, activity)
    return {
        "stats": stats,
        "briefing": briefing,
        "recommendations": recommendations,
        "recent_activity": activity,
    }


# ══════════════════════════════════════════════════════════════════════════════
# PREFERENCES
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/preferences")
def get_preferences():
    return {"preferences": get_all_preferences()}


@router.put("/preferences")
def update_preferences(req: PreferencesUpdate):
    update_preferences_bulk(req.updates, source=req.source)
    return {"status": "ok", "preferences": get_all_preferences()}


@router.post("/learn", dependencies=[Depends(_ai_limit)])
def learn_preference(req: LearnRequest):
    """Parse natural language feedback and update career preferences."""
    prefs = get_all_preferences()
    result = learn_from_feedback(req.text, prefs)
    updates = result.get("updates", {})
    if updates:
        update_preferences_bulk(updates, source="ai_inferred")
        log_activity("preference_learned",
                     "Preference updated",
                     result.get("explanation", ""))
    return {
        "status": "ok",
        "updates": updates,
        "explanation": result.get("explanation", ""),
        "preferences": get_all_preferences() if updates else {},
    }


# ══════════════════════════════════════════════════════════════════════════════
# PROFILE (Personal Vault)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/profile")
def get_career_profile():
    return {"profile": get_profile()}


@router.put("/profile")
def update_career_profile(req: ProfileUpdate):
    update_profile_bulk(req.fields)
    return {"status": "ok", "profile": get_profile()}


# ══════════════════════════════════════════════════════════════════════════════
# RESUMES
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/resumes")
def list_resumes(include_archived: bool = False):
    return {"resumes": get_all_resumes(include_archived)}


@router.get("/resumes/{resume_id}")
def read_resume(resume_id: int):
    r = get_resume(resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"status": "ok", "resume": r}


@router.delete("/resumes/{resume_id}")
@router.post("/resumes/{resume_id}/delete")
def remove_resume(resume_id: str):
    from services.career_db import delete_resume
    res = delete_resume(resume_id)
    return {"status": "ok", "deleted": res}


@router.get("/candidate-intelligence/{resume_id}", dependencies=[Depends(_ai_limit)])
def get_candidate_intelligence_endpoint(resume_id: str):
    """Retrieve complete Candidate Intelligence report for a specific resume."""
    resume = get_resume(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    content = resume.get("content", {})
    raw_text = resume.get("raw_text", "") or json.dumps(content)
    
    from services.candidate_intelligence import analyze_candidate_profile
    return {
        "status": "ok",
        "resume_id": resume_id,
        "intelligence": analyze_candidate_profile(raw_text, content)
    }


from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
import io
import re

@router.post("/resumes/upload", dependencies=[Depends(_ai_limit)])
async def upload_resume_file(file: UploadFile = File(...)):
    filename = file.filename or "Uploaded Resume"
    # Cap upload size (5 MB) to avoid unbounded memory + parse cost.
    contents = await file.read(5 * 1024 * 1024 + 1)
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Upload too large (max 5 MB).")
    extracted_text = ""

    if filename.lower().endswith(".pdf"):
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(contents))
            pages_text = []
            for page in reader.pages:
                txt = page.extract_text()
                if txt:
                    pages_text.append(txt)
            extracted_text = "\n".join(pages_text)
        except Exception as e:
            extracted_text = contents.decode("utf-8", errors="ignore")
    elif filename.lower().endswith(".docx"):
        try:
            import zipfile
            from xml.etree import ElementTree as ET
            with zipfile.ZipFile(io.BytesIO(contents)) as z:
                xml_content = z.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                extracted_text = "".join(tree.itertext())
        except Exception:
            extracted_text = contents.decode("utf-8", errors="ignore")
    else:
        extracted_text = contents.decode("utf-8", errors="ignore")

    # Tier 1: Try AI extraction via Groq LLM first for 100% accurate parsing
    sections = None
    try:
        from services.career_intelligence import _llm
        system_prompt = (
            "You are an expert resume parser. Analyze the provided resume text and categorize its contents into JSON with EXACTLY these 7 keys:\n"
            "- summary: Brief summary, title, or contact/intro details\n"
            "- skills: Technical skills, tools, languages, frameworks, databases\n"
            "- experience: Work experience, company names, job titles, dates, achievements\n"
            "- education: Degrees, universities, graduation years, GPA/scores\n"
            "- projects: Project titles, descriptions, tech used, links\n"
            "- achievements: Awards, honors, competitive rankings, key accomplishments\n"
            "- certifications: Certifications, licenses, credentials\n\n"
            "DO NOT dump all text into summary! Divide content accurately. Return ONLY valid JSON."
        )
        parsed_json = _llm(system_prompt, f"Resume Text:\n{extracted_text[:6500]}", json_mode=True)
        if isinstance(parsed_json, dict):
            sec = {
                "summary": str(parsed_json.get("summary") or "").strip(),
                "skills": str(parsed_json.get("skills") or "").strip(),
                "experience": str(parsed_json.get("experience") or "").strip(),
                "education": str(parsed_json.get("education") or "").strip(),
                "projects": str(parsed_json.get("projects") or "").strip(),
                "achievements": str(parsed_json.get("achievements") or "").strip(),
                "certifications": str(parsed_json.get("certifications") or "").strip()
            }
            if sum(1 for v in sec.values() if len(v) > 5) >= 2:
                sections = sec
    except Exception as err:
        print("[Resume Upload Parser] LLM parsing fallback to regex:", err)

    # Tier 2: Enhanced smart section matcher fallback
    if not sections or not any(sections.values()):
        sec_keywords = [
            ("skills", [r"technical\s+skills", r"skills\s*&\s*tools", r"core\s+competencies", r"skills", r"tech\s+stack", r"technologies", r"programming\s+languages"]),
            ("experience", [r"work\s+experience", r"professional\s+experience", r"employment\s+history", r"experience", r"work\s+history", r"internships"]),
            ("education", [r"education", r"academic\s+background", r"academic\s+qualifications", r"degrees", r"scholastic\s+achievements"]),
            ("projects", [r"projects", r"key\s+projects", r"personal\s+projects", r"academic\s+projects", r"portfolio"]),
            ("achievements", [r"achievements", r"awards\s*&\s*achievements", r"honors", r"accomplishments", r"awards", r"hackathons"]),
            ("certifications", [r"certifications", r"certificates", r"licenses", r"credentials", r"courses\s*&\s*certifications"]),
            ("summary", [r"summary", r"professional\s+summary", r"profile\s+summary", r"about\s+me", r"career\s+objective", r"overview", r"profile"])
        ]

        lines = [l.strip() for l in extracted_text.splitlines() if l.strip()]
        sec_buffers = {
            "summary": [], "skills": [], "experience": [],
            "education": [], "projects": [], "achievements": [], "certifications": []
        }

        current_sec = "summary"
        for line in lines:
            matched_sec = None
            clean_line = line.lower().strip(":#*- ")
            header_rest = ""
            for sec_key, patterns in sec_keywords:
                for pat in patterns:
                    m = re.match(r"^" + pat + r"(?:\s*[:\-–—]\s*(.*))?$", clean_line, re.IGNORECASE)
                    if m:
                        matched_sec = sec_key
                        header_rest = m.group(1) if m.lastindex and m.group(1) else ""
                        break
                if matched_sec:
                    break
            if matched_sec:
                current_sec = matched_sec
                if header_rest:
                    sec_buffers[current_sec].append(header_rest)
            else:
                sec_buffers[current_sec].append(line)

        sections = {sec: "\n".join(sec_buffers[sec]).strip() for sec in sec_buffers}

    # Fallback safety if all empty
    if not any(sections.values()):
        sections["summary"] = extracted_text.strip()

    clean_title = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
    resume_id = create_resume(clean_title, sections)
    log_activity("resume_uploaded", f"Uploaded resume file: {filename}", f"Resume ID: {resume_id}")

    return {
        "status": "ok",
        "resume_id": resume_id,
        "title": clean_title,
        "content": sections
    }


@router.post("/resumes")
def create_new_resume(req: ResumeCreate):
    resume_id = create_resume(req.title, req.content)
    return {"status": "ok", "resume_id": resume_id}


@router.put("/resumes/{resume_id}")
def update_resume_endpoint(resume_id: int, req: ResumeUpdate):
    updates = {}
    if req.title is not None:
        updates["title"] = req.title
    if req.content is not None:
        updates["content_json"] = req.content
    if req.ats_score is not None:
        updates["ats_score"] = req.ats_score
    if req.is_archived is not None:
        updates["is_archived"] = req.is_archived
    if req.is_recommended is not None:
        updates["is_recommended"] = req.is_recommended
    if not updates:
        raise HTTPException(400, "No valid fields to update")
    ok = update_resume(resume_id, updates)
    return {"status": "ok" if ok else "no_change"}


@router.post("/resumes/{resume_id}/duplicate")
def duplicate_resume_endpoint(resume_id: int):
    new_id = duplicate_resume(resume_id)
    if not new_id:
        raise HTTPException(404, "Resume not found")
    return {"status": "ok", "new_resume_id": new_id}


@router.post("/resumes/{resume_id}/recommend")
def recommend_resume(resume_id: int):
    set_recommended_resume(resume_id)
    return {"status": "ok"}


# ══════════════════════════════════════════════════════════════════════════════
# JOBS (Opportunities)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/jobs")
def list_jobs(
    status: Optional[str] = None,
    min_score: float = 0,
    source: Optional[str] = None,
):
    jobs = get_jobs(status=status, min_score=min_score, source=source)
    # Parse match_json
    for job in jobs:
        try:
            job["match"] = json.loads(job.get("match_json") or "{}")
        except Exception:
            job["match"] = {}
    return {"jobs": jobs, "count": len(jobs)}


@router.get("/jobs/{job_id}")
def get_job_detail(job_id: int):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    try:
        job["match"] = json.loads(job.get("match_json") or "{}")
    except Exception:
        job["match"] = {}
    return {"job": job}


@router.post("/jobs")
def add_job(req: JobCreate):
    job_data = req.model_dump()
    job_id = create_job(job_data)
    return {"status": "ok", "job_id": job_id}


@router.post("/jobs/fetch-linkedin", dependencies=[Depends(_ai_limit)])
async def fetch_linkedin_jobs(
    query: Optional[str] = "Java Software Engineer",
    location: Optional[str] = "India",
    exp_level: Optional[str] = "fresher"
):
    """Fetches and AI-analyzes 100% real live LinkedIn developer jobs with dynamic experience level filtering."""
    try:
        live_jobs = await fetch_live_linkedin_jobs(query, location, exp_level)
        return {"status": "ok", "count": len(live_jobs), "jobs": live_jobs}
    except Exception as e:
        print("[LinkedIn Fetch Error]:", e)
        return {"status": "error", "message": str(e), "jobs": []}


@router.put("/jobs/{job_id}")
def update_job_endpoint(job_id: int, req: JobStatusUpdate):
    updates: dict = {"status": req.status}
    ok = update_job(job_id, updates)
    log_activity("job_status_changed",
                 f"Job status: {req.status}",
                 req.notes)
    return {"status": "ok" if ok else "no_change"}


@router.post("/jobs/analyze", dependencies=[Depends(_ai_limit)])
def analyze_job(req: AnalyzeJobRequest):
    """Run AI match analysis for a job against a resume."""
    job = get_job(req.job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    resume_content = {}
    if req.resume_id:
        r = get_resume(req.resume_id)
        if r:
            try:
                resume_content = json.loads(r.get("content_json") or "{}")
            except Exception:
                pass

    prefs = get_all_preferences()
    match = analyze_job_match(job, resume_content, prefs)
    update_job(req.job_id, {
        "match_json": match,
        "match_score": match.get("overall_score", 0),
        "analyzed_at": datetime.utcnow().isoformat(),
    })
    log_activity("job_analyzed",
                 f"Analyzed: {job['title']} at {job['company']}",
                 f"Score: {match.get('overall_score', 0)}%")
    return {"status": "ok", "match": match}


# ══════════════════════════════════════════════════════════════════════════════
# APPLICATIONS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/applications")
def list_applications(status: Optional[str] = None):
    apps = get_applications(status)
    return {"applications": apps, "count": len(apps)}


@router.post("/applications")
def create_new_application(req: ApplicationCreate):
    app_id = create_application(req.job_id, req.resume_id)
    return {"status": "ok", "application_id": app_id}


@router.put("/applications/{app_id}")
def update_application_endpoint(app_id: int, req: ApplicationUpdate):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")
    ok = update_application(app_id, updates)
    return {"status": "ok" if ok else "no_change"}


# ══════════════════════════════════════════════════════════════════════════════
# COVER LETTERS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/cover-letter", dependencies=[Depends(_ai_limit)])
def generate_cover_letter_endpoint(req: CoverLetterRequest):
    """Generate a unique AI cover letter for a job."""
    job = get_job(req.job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    resume_content = {}
    if req.resume_id:
        r = get_resume(req.resume_id)
        if r:
            try:
                resume_content = json.loads(r.get("content_json") or "{}")
            except Exception:
                pass

    profile = {k: v["value"] for k, v in get_profile().items()}
    content = generate_cover_letter(job, resume_content, profile, req.tone)
    cover_id = save_cover_letter(req.job_id, req.resume_id, content, req.tone)
    return {"status": "ok", "cover_letter_id": cover_id, "content": content}


@router.get("/cover-letters")
def list_cover_letters(job_id: Optional[int] = None):
    return {"cover_letters": get_cover_letters(job_id)}


# ══════════════════════════════════════════════════════════════════════════════
# RECRUITERS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/recruiters")
def list_recruiters():
    return {"recruiters": get_recruiters()}


@router.post("/recruiters")
def add_recruiter(req: RecruiterCreate):
    recruiter_id = create_recruiter(req.model_dump())
    return {"status": "ok", "recruiter_id": recruiter_id}


@router.put("/recruiters/{recruiter_id}")
def update_recruiter_endpoint(recruiter_id: int, req: RecruiterUpdate):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    ok = update_recruiter(recruiter_id, updates)
    return {"status": "ok" if ok else "no_change"}


# ══════════════════════════════════════════════════════════════════════════════
# INTERVIEWS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/interviews")
def list_interviews(upcoming_only: bool = False):
    return {"interviews": get_interviews(upcoming_only)}


@router.post("/interviews")
def add_interview(req: InterviewCreate):
    interview_id = create_interview(req.model_dump())
    return {"status": "ok", "interview_id": interview_id}


@router.put("/interviews/{interview_id}")
def update_interview_endpoint(interview_id: int, req: InterviewUpdate):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    ok = update_interview(interview_id, updates)
    return {"status": "ok" if ok else "no_change"}


@router.post("/interviews/questions", dependencies=[Depends(_ai_limit)])
def get_interview_questions(req: InterviewQuestionsRequest):
    """Generate AI interview prep questions for a job."""
    job = get_job(req.job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    resume_content = {}
    if req.resume_id:
        r = get_resume(req.resume_id)
        if r:
            try:
                resume_content = json.loads(r.get("content_json") or "{}")
            except Exception:
                pass
    questions = generate_interview_questions(job, resume_content)
    return {"status": "ok", "questions": questions}


# ══════════════════════════════════════════════════════════════════════════════
# COMPANIES
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/companies")
def list_companies(blacklisted_only: bool = False):
    return {"companies": get_companies(blacklisted_only)}


@router.post("/companies/blacklist")
def blacklist_company_endpoint(req: CompanyBlacklist):
    blacklist_company(req.name, req.reason)
    return {"status": "ok", "company": req.name, "blacklisted": True}


@router.post("/companies")
def add_company(name: str, data: dict = {}):
    company_id = upsert_company(name, data)
    return {"status": "ok", "company_id": company_id}


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/analytics")
def get_career_analytics():
    return {"analytics": get_analytics()}


@router.get("/skill-gap", dependencies=[Depends(_ai_limit)])
def get_skill_gap(resume_id: Optional[int] = None):
    """Analyze skill gaps from available job listings."""
    jobs = get_jobs(min_score=0)
    resume_content = {}
    if resume_id:
        r = get_resume(resume_id)
        if r:
            try:
                resume_content = json.loads(r.get("content_json") or "{}")
            except Exception:
                pass
    analysis = generate_skill_gap_analysis(jobs, resume_content)
    return {"analysis": analysis}


# ══════════════════════════════════════════════════════════════════════════════
# ACCOUNTS & SESSION VERIFICATION
# ══════════════════════════════════════════════════════════════════════════════

from services.platform_session import launch_real_browser_login, get_platform_session_status

@router.post("/accounts/verify/{platform_key}")
def verify_account_endpoint(platform_key: str):
    """Returns verified session status and live profile metrics."""
    return get_platform_session_status(platform_key)

@router.post("/accounts/connect/{platform_key}")
async def connect_account_live_browser(platform_key: str):
    """Launches real browser (headless=False) so user can log in ONCE and capture session cookies."""
    return await launch_real_browser_login(platform_key)

# ══════════════════════════════════════════════════════════════════════════════
# ACTIVITY
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/activity")
def get_activity(limit: int = 20):
    return {"activity": get_activity_log(limit)}
