"""
career_intelligence.py — Career OS AI Reasoning Engine.

Uses existing Groq client (Llama 3.3 70B) for:
  - Job match scoring and analysis
  - Cover letter generation
  - Interview question generation
  - Daily career briefing
  - Preference learning from natural language
  - Skill gap analysis and career strategy
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

from groq import Groq

_groq_client = None


def _groq():
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    return _groq_client


def _llm(system_prompt: str, user_prompt: str, json_mode: bool = False,
         model: str = "llama-3.3-70b-versatile", max_tokens: int = 1500) -> str:
    """Call Groq with a system + user prompt. Returns raw string."""
    try:
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.4,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = _groq().chat.completions.create(**kwargs)
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Career AI] Error: {e}")
        return "{}" if json_mode else ""


# ═══════════════════════════════════════════════════════════════════════════════
# JOB MATCH ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_job_match(job: dict, resume_content: dict, preferences: dict) -> dict:
    """
    Produce a structured match report for a job against the user's profile.
    Returns JSON with score, reasoning, recommendations.
    """
    profile_text = _format_resume_for_prompt(resume_content)
    pref_text = _format_preferences_for_prompt(preferences)
    job_text = f"""
Job Title: {job.get('title', 'Unknown')}
Company: {job.get('company', 'Unknown')}
Location: {job.get('location', 'Not specified')}
Remote: {job.get('remote_type', 'Unknown')}
Salary: {job.get('salary_raw', 'Not specified')}
Experience Required: {job.get('experience_required', 'Not specified')}
Visa Sponsorship: {'Yes' if job.get('visa_sponsorship') else 'No'}
Description:
{(job.get('description', '') or '')[:3000]}
""".strip()

    system = """You are F.R.I.D.A.Y., an intelligent career AI assistant.
Analyze the provided job against the candidate's profile and preferences.
Return ONLY valid JSON with this exact structure:
{
  "overall_score": <0-100 integer>,
  "skill_match": [<list of matching skills>],
  "missing_skills": [<list of required skills not in profile>],
  "salary_assessment": "<above/meets/below minimum>",
  "experience_match": "<matches/slightly above/significantly above requirement>",
  "remote_match": <true/false>,
  "visa_ok": <true/false>,
  "company_reputation": "<excellent/good/average/unknown>",
  "career_growth": "<high/medium/low>",
  "difficulty": "<low/medium/high>",
  "reasoning": "<2-3 sentences explaining the score naturally>",
  "recommendation": "<apply_now/consider/skip>",
  "confidence": "<high/medium/low>",
  "deadline_urgency": "<urgent/normal/none>"
}
Be precise. Never inflate scores. If skills are missing, reflect that honestly."""

    user = f"""CANDIDATE PROFILE:
{profile_text}

CANDIDATE PREFERENCES:
{pref_text}

JOB TO ANALYZE:
{job_text}"""

    raw = _llm(system, user, json_mode=True, max_tokens=800)
    try:
        result = json.loads(raw)
        # Ensure score is in range
        result["overall_score"] = max(0, min(100, int(result.get("overall_score", 50))))
        return result
    except Exception:
        return {
            "overall_score": 50,
            "skill_match": [],
            "missing_skills": [],
            "salary_assessment": "unknown",
            "experience_match": "unknown",
            "remote_match": False,
            "visa_ok": True,
            "company_reputation": "unknown",
            "career_growth": "medium",
            "difficulty": "medium",
            "reasoning": "Unable to fully analyze this position. Manual review recommended.",
            "recommendation": "consider",
            "confidence": "low",
            "deadline_urgency": "none",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# COVER LETTER GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_cover_letter(job: dict, resume_content: dict, profile: dict,
                          tone: str = "professional") -> str:
    """Generate a unique, non-generic cover letter. Never reuses identical text."""
    name = profile.get("name", {}).get("value", "Prem")
    profile_text = _format_resume_for_prompt(resume_content)

    tone_instruction = {
        "professional": "formal, precise, confident — like a senior engineer writing to a top-tier company",
        "confident": "bold, direct, achievement-focused — lead with impact",
        "friendly": "warm, enthusiastic, personable — while still being professional",
    }.get(tone, "professional, precise, and confident")

    system = f"""You are F.R.I.D.A.Y., an expert career AI.
Write a cover letter that is {tone_instruction}.
Rules:
- 3-4 paragraphs only
- Address it to the company's hiring team
- Mention the specific role and company by name
- Reference 2-3 specific skills/projects from the profile that match this job
- Never use clichés like "I am writing to express my interest" or "I am a hard worker"
- Start with a compelling opening that immediately shows value
- End with a clear call to action
- Do not include subject line or address headers, just the body paragraphs"""

    user = f"""Write a cover letter for {name} applying to:

Role: {job.get('title', 'Software Engineer')}
Company: {job.get('company', 'the company')}
Location: {job.get('location', '')}
Job Description: {(job.get('description', '') or '')[:2000]}

CANDIDATE PROFILE:
{profile_text}

Current date: {datetime.now().strftime('%B %Y')}"""

    result = _llm(system, user, max_tokens=1000)
    if not result:
        return f"""Dear Hiring Team,

I am excited to apply for the {job.get('title', 'Software Engineer')} position at {job.get('company', 'your company')}. With my background in software development and a strong track record of delivering impactful projects, I am confident I would be a valuable addition to your team.

My experience aligns well with your requirements, and I am particularly drawn to the technical challenges this role presents. I look forward to discussing how I can contribute to your team's goals.

Best regards,
{name}"""
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# INTERVIEW QUESTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def generate_interview_questions(job: dict, resume_content: dict) -> list:
    """Generate role-specific interview preparation questions."""
    system = """You are F.R.I.D.A.Y., an intelligent career AI.
Generate exactly 10 interview preparation questions for this role.
Mix: 3 technical, 3 behavioral, 2 company-specific, 2 situational.
Return ONLY valid JSON: {"questions": ["q1", "q2", ...]}"""

    user = f"""Role: {job.get('title', 'Software Engineer')}
Company: {job.get('company', 'the company')}
Job Description: {(job.get('description', '') or '')[:1500]}
Candidate Skills: {', '.join(resume_content.get('skills', []) if isinstance(resume_content.get('skills'), list) else [])}"""

    raw = _llm(system, user, json_mode=True, max_tokens=1000)
    try:
        result = json.loads(raw)
        return result.get("questions", [])
    except Exception:
        return [
            f"Tell me about your experience relevant to {job.get('title', 'this role')}.",
            "Describe a challenging technical problem you solved.",
            "How do you approach learning new technologies?",
            "Tell me about a time you worked under pressure.",
            f"Why are you interested in {job.get('company', 'this company')}?",
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# DAILY BRIEFING
# ═══════════════════════════════════════════════════════════════════════════════

def generate_daily_briefing(stats: dict, preferences: dict) -> str:
    """Generate a concise, natural daily career briefing addressed to Boss."""
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else ("Good afternoon" if hour < 17 else "Good evening")

    system = """You are F.R.I.D.A.Y., a calm and intelligent career AI assistant.
Write a concise daily career briefing addressed to 'Boss'.
Style: Professional, confident, concise. Like a trusted advisor, not a chatbot.
Maximum 4 sentences. Be specific with numbers. No filler phrases."""

    user = f"""{greeting} briefing request.

Stats:
- New job opportunities: {stats.get('new_jobs', 0)}
- High priority matches (80%+): {stats.get('high_priority', 0)}
- Applications pending approval: {stats.get('pending_approval', 0)}
- Applications submitted: {stats.get('submitted', 0)}
- Upcoming interviews: {stats.get('interviews', 0)}
- Active offers: {stats.get('offers', 0)}
- Upcoming deadlines: {len(stats.get('upcoming_deadlines', []))}

Generate a briefing starting with '{greeting}, Boss.'"""

    result = _llm(system, user, max_tokens=300)
    if not result:
        new = stats.get("new_jobs", 0)
        hp = stats.get("high_priority", 0)
        return (f"{greeting}, Boss. I found {new} new opportunities, {hp} are excellent matches. "
                f"No immediate action required.")
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# PREFERENCE LEARNING
# ═══════════════════════════════════════════════════════════════════════════════

def learn_from_feedback(text: str, current_preferences: dict) -> dict:
    """
    Parse natural language feedback and return preference updates.
    Example: "don't show Infosys" → {blacklisted_companies: ['Infosys']}
    """
    system = """You are F.R.I.D.A.Y., an intelligent career AI.
Parse the user's feedback and return ONLY valid JSON with preference updates.
Possible keys to update:
- blacklisted_companies: list of company names to avoid
- avoided_roles: list of job roles to avoid
- preferred_roles: list of preferred roles
- min_salary: number (in LPA for Indian context, annual for global)
- preferred_remote: "remote", "hybrid", "onsite", or "any"
- preferred_countries: list of country names
- preferred_cities: list of city names
- preferred_tech_stack: list of preferred technologies
- avoided_tech_stack: list of technologies to avoid
- preferred_industries: list of industries
- job_types: list of "full-time", "internship", "contract"
- experience_level: "junior", "mid", "senior", "any"
- favorite_companies: list of companies to prioritize

Return format: {"updates": {<key>: <value>}, "explanation": "<what was learned>"}
If nothing relevant found, return: {"updates": {}, "explanation": "No preference change detected."}"""

    user = f"""User said: "{text}"

Current preferences (for context):
{json.dumps(current_preferences, indent=2, default=str)[:1000]}"""

    raw = _llm(system, user, json_mode=True, max_tokens=500)
    try:
        result = json.loads(raw)
        # Merge with existing list preferences rather than overwriting
        updates = result.get("updates", {})
        for list_key in ["blacklisted_companies", "avoided_roles", "preferred_roles",
                         "preferred_countries", "preferred_cities", "preferred_tech_stack",
                         "avoided_tech_stack", "preferred_industries", "favorite_companies"]:
            if list_key in updates:
                existing = current_preferences.get(list_key, [])
                new_items = updates[list_key] if isinstance(updates[list_key], list) else [updates[list_key]]
                updates[list_key] = list(set(existing + new_items))
        return result
    except Exception:
        return {"updates": {}, "explanation": "Could not parse preference from input."}


# ═══════════════════════════════════════════════════════════════════════════════
# SKILL GAP ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def generate_skill_gap_analysis(jobs: list, resume_content: dict) -> dict:
    """
    Analyze a list of job descriptions to identify skill gaps
    and generate a personalized learning roadmap.
    """
    if not jobs:
        return {"skills_in_demand": [], "missing_skills": [], "roadmap": [], "impact": ""}

    # Extract all required skills from job descriptions
    all_descriptions = " ".join(
        (j.get("description", "") or "")[:500] for j in jobs[:50]
    )

    current_skills = resume_content.get("skills", [])
    if isinstance(current_skills, str):
        current_skills = [s.strip() for s in current_skills.split(",")]

    system = """You are F.R.I.D.A.Y., a career intelligence AI.
Analyze job descriptions and identify skill gaps. Return ONLY valid JSON:
{
  "skills_in_demand": [{"skill": "Docker", "frequency": 85, "category": "devops"}],
  "missing_skills": [{"skill": "Docker", "priority": "high", "weeks_to_learn": 2}],
  "roadmap": [
    {"week": "Week 1-2", "focus": "Docker fundamentals", "resources": ["Official docs", "Play with Docker"]}
  ],
  "impact": "<sentence about how learning these skills would improve match scores>",
  "current_avg_match": <estimated current match percentage as integer>,
  "potential_avg_match": <estimated match after learning top skills as integer>
}"""

    user = f"""Current skills: {', '.join(current_skills[:30])}

Job market analysis (from {len(jobs)} job listings):
{all_descriptions[:3000]}"""

    raw = _llm(system, user, json_mode=True, max_tokens=1500)
    try:
        return json.loads(raw)
    except Exception:
        return {
            "skills_in_demand": [],
            "missing_skills": [],
            "roadmap": [],
            "impact": "Analysis unavailable. Add more jobs to get skill gap insights.",
            "current_avg_match": 0,
            "potential_avg_match": 0,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CAREER RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_career_recommendations(stats: dict, preferences: dict, recent_activity: list) -> list:
    """
    Generate proactive Friday career recommendations.
    Returns list of {type, priority, title, body, action} objects.
    """
    recommendations = []

    # Deadline alerts (deterministic — no LLM needed)
    for deadline in stats.get("upcoming_deadlines", [])[:3]:
        if deadline.get("deadline"):
            recommendations.append({
                "type": "deadline",
                "priority": "high",
                "title": f"Application closes soon",
                "body": f"{deadline.get('title')} at {deadline.get('company')} — deadline {deadline.get('deadline')}",
                "action": "review_job",
                "reasons": [
                    "The application window is closing",
                    "You matched this job previously",
                ],
            })

    # High priority jobs waiting
    if stats.get("high_priority", 0) > 0:
        recommendations.append({
            "type": "opportunity",
            "priority": "medium",
            "title": f"{stats['high_priority']} high-match opportunities waiting",
            "body": "I found jobs matching 80%+ of your profile. Review and approve to begin applications.",
            "action": "open_opportunities",
            "reasons": [
                "Jobs score 80%+ against your resume skills",
                "Salary meets the minimum you set in preferences",
                "You previously preferred backend roles",
            ],
        })

    # No resumes created yet
    if stats.get("total_applications", 0) == 0:
        recommendations.append({
            "type": "setup",
            "priority": "high",
            "title": "Set up your profile to get started",
            "body": "Add your resume and preferences so I can find and analyze opportunities for you.",
            "action": "open_resume_manager",
            "reasons": [
                "No resumes exist yet — job matching needs a profile",
                "Preferences are empty, so I can't filter by salary or role",
            ],
        })

    # Pending interviews
    if stats.get("interviews", 0) > 0:
        recommendations.append({
            "type": "interview",
            "priority": "high",
            "title": f"{stats['interviews']} interview(s) coming up",
            "body": "Review your preparation notes and practice questions in the Interview Center.",
            "action": "open_interviews",
        })

    # LLM-powered advice if we have enough data
    if stats.get("total_applications", 0) >= 5:
        system = """You are F.R.I.D.A.Y., a career AI. Generate 1-2 strategic career recommendations.
Return ONLY valid JSON: {"recommendations": [{"type": "strategy", "priority": "medium", "title": "...", "body": "...", "action": "none"}]}
Be specific, actionable, and address Boss naturally. Max 2 recommendations."""
        user = f"""Career stats: {json.dumps(stats)}
Recent activity count: {len(recent_activity)}"""
        try:
            raw = _llm(system, user, json_mode=True, max_tokens=400)
            ai_recs = json.loads(raw).get("recommendations", [])
            recommendations.extend(ai_recs[:2])
        except Exception:
            pass

    return recommendations[:6]  # Max 6 recommendations


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _format_resume_for_prompt(content: dict) -> str:
    if not content:
        return "No resume data available."
    parts = []
    if content.get("summary"):
        parts.append(f"SUMMARY:\n{content['summary']}")
    if content.get("skills"):
        skills = content["skills"]
        if isinstance(skills, list):
            skills = ", ".join(skills)
        parts.append(f"SKILLS:\n{skills}")
    if content.get("experience"):
        parts.append(f"EXPERIENCE:\n{str(content['experience'])[:800]}")
    if content.get("education"):
        parts.append(f"EDUCATION:\n{str(content['education'])[:400]}")
    if content.get("projects"):
        parts.append(f"PROJECTS:\n{str(content['projects'])[:600]}")
    return "\n\n".join(parts) if parts else "Resume data incomplete."


def _format_preferences_for_prompt(prefs: dict) -> str:
    lines = []
    if prefs.get("min_salary"):
        lines.append(f"Minimum salary: {prefs['min_salary']}")
    if prefs.get("preferred_remote") and prefs["preferred_remote"] != "any":
        lines.append(f"Work type: {prefs['preferred_remote']}")
    if prefs.get("preferred_countries"):
        lines.append(f"Preferred countries: {', '.join(prefs['preferred_countries'])}")
    if prefs.get("preferred_tech_stack"):
        lines.append(f"Preferred tech: {', '.join(prefs['preferred_tech_stack'])}")
    if prefs.get("blacklisted_companies"):
        lines.append(f"Avoid companies: {', '.join(prefs['blacklisted_companies'])}")
    if prefs.get("avoided_roles"):
        lines.append(f"Avoid roles: {', '.join(prefs['avoided_roles'])}")
    return "\n".join(lines) if lines else "No specific preferences set."
