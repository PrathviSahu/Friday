"""services/company_intelligence.py — Company Intelligence Agent.

"Tell me about Goldman Sachs" → FRIDAY composes:
  • Company overview + hiring trends (web search, DuckDuckGo)
  • Your application history with this company (Career OS data)
  • Interview prep checklist for the roles you've applied to

LLM composes the final report (Groq, free tier). Fully graceful:
missing web results or no applications → the section is omitted, never an error.
"""

import os
import re

from services.career_db import get_jobs, get_applications


class CompanyIntelUnavailableError(RuntimeError):
    """Raised when nothing can be composed (no web, no LLM, no data)."""


def _normalize(name: str) -> str:
    return (name or "").strip()


def _search_company(name: str) -> str:
    """DuckDuckGo instant answers + top snippets for the company."""
    try:
        from services.web_search import search_web_instant
        result = search_web_instant(f"{name} company overview hiring")
        snippets = []
        if result.get("answer"):
            snippets.append(f"Answer: {result['answer']}")
        for r in (result.get("results") or [])[:4]:
            title = r.get("title") or ""
            body = r.get("snippet") or ""
            if title:
                snippets.append(f"- {title}: {body[:220]}")
        return "\n".join(snippets)[:3000]
    except Exception as exc:
        print(f"[CompanyIntel] web search failed: {exc}")
        return ""


def _your_applications(company: str) -> list:
    """Your application history for this company (case-insensitive match)."""
    company_l = company.lower()
    out = []
    try:
        for app in get_applications() or []:
            job = app.get("job") or {}
            job_company = (job.get("company") or "") if isinstance(job, dict) else ""
            if company_l in job_company.lower():
                out.append({
                    "title": job.get("title") or "—",
                    "status": app.get("status") or "saved",
                    "applied_at": app.get("applied_at") or "",
                    "salary_offered": app.get("salary_offered") or 0,
                    "notes": app.get("notes") or "",
                })
    except Exception:
        pass
    return out


def _roles_at(company: str) -> list:
    """Tracked jobs at this company (for interview-prep suggestions)."""
    company_l = company.lower()
    return [j for j in (get_jobs() or []) if company_l in (j.get("company") or "").lower()]


def _compose(name: str, web: str, applications: list, roles: list) -> str:
    """LLM composes the final report from the gathered pieces."""
    from services.brain import _get_groq_client

    client = _get_groq_client()
    if client is None:
        raise CompanyIntelUnavailableError("GROQ_API_KEY is not configured — can't compose company intel.")

    parts = [f"Company: {name}", "Role(s) I track at this company: " +
             (", ".join(f"{r.get('title')} ({r.get('location') or 'remote?'})" for r in roles[:4]) or "none")]

    if web:
        parts.append(f"WEB RESEARCH:\n{web[:2500]}")
    if applications:
        lines = [f"MY APPLICATION HISTORY ({len(applications)}):"]
        for a in applications[:5]:
            lines.append(f"- {a['title']} — status: {a['status']}"
                         + (f", applied {a['applied_at']}" if a.get("applied_at") else ""))
        parts.append("\n".join(lines))

    prompt = (
        "You are F.R.I.D.A.Y.'s company intelligence engine. Using ONLY the data below, "
        "write a concise company brief for Prem with sections:\n"
        "• Overview & what the company does (2-3 sentences; if web data is missing, say 'no recent web data')\n"
        "• Hiring signals from web research (bullets)\n"
        "• Prem's application history at this company (or 'no applications tracked yet')\n"
        "• Interview-prep checklist based on the roles listed\n"
        "Keep it tight and skimmable. If data is missing, say so plainly — never invent facts.\n\n"
        + "\n\n".join(parts)
    )

    try:
        completion = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[{"role": "user", "content": prompt[:16000]}],
            temperature=0.3,
            max_tokens=700,
        )
        return (getattr(completion.choices[0].message, "content", "") or "").strip()
    except Exception as exc:
        raise CompanyIntelUnavailableError(f"LLM call failed: {exc}") from exc


def get_company_intel(name: str) -> dict:
    """Full pipeline: gather → compose → return {company, report, sections}."""
    name = _normalize(name)
    if not name:
        raise CompanyIntelUnavailableError("Which company should I look up?")

    web = _search_company(name)
    applications = _your_applications(name)
    roles = _roles_at(name)

    if not web and not applications and not roles:
        # Still answer from general knowledge via the LLM
        pass

    report = _compose(name, web, applications, roles)
    return {
        "company": name,
        "report": report,
        "web_found": bool(web),
        "applications": len(applications),
        "roles_tracked": len(roles),
    }


def format_for_speech(intel: dict) -> str:
    """A short spoken summary of a company intel report."""
    report = (intel.get("report") or "").strip()
    # Take first ~2 sections worth of text
    return report[:400] or f"No information found on {intel.get('company')}."
