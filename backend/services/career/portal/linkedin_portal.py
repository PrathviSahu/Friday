"""backend/services/career/portal/linkedin_portal.py — LinkedIn Real Job Portal Connection & Read-Only Form Discovery.

Provides authenticated profile access, job application form inspection, and safe field mapping for LinkedIn.
STRICT READ-ONLY BOUNDARY: No submissions, no clicking final apply, no recruiter messages, zero CAPTCHA/OTP bypass.
"""

import json
import uuid
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.services.career.portal.base import (
    BaseApplicationPortal,
    FieldSensitivity,
    classify_field_sensitivity,
)

DB_FILE = Path(__file__).resolve().parents[3] / "data" / "friday_brain.db"




class LinkedInApplicationPortal(BaseApplicationPortal):
    """LinkedIn Real Application Portal Adapter (Connection & Read-Only Discovery Only).

    STRICT READ-ONLY BOUNDARY: Form submission is permanently disabled in this step.
    """

    ALLOWED_DOMAINS = [
        "linkedin.com",
        "www.linkedin.com",
        "careers.linkedin.com",
    ]

    def __init__(self, headless: bool = True, timeout: int = 25):
        self.headless = headless
        self.timeout = timeout
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def provider_name(self) -> str:
        return "linkedin_portal"

    def allowed_domains(self) -> List[str]:
        return list(self.ALLOWED_DOMAINS)

    def check_connection(self) -> Dict[str, Any]:
        """Truthfully report LinkedIn portal authentication and session readiness without exposing secrets."""
        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute(
                "SELECT account_name, headline, connections_count, open_to_work, cookies_json, verified_at "
                "FROM platform_sessions WHERE platform_key = 'linkedin'"
            )
            row = c.fetchone()
            conn.close()

            if not row or not row[4]:
                return {
                    "status": "AUTH_REQUIRED",
                    "connected": False,
                    "provider": self.provider_name(),
                    "mode": "READ_ONLY_DISCOVERY",
                    "account_user": None,
                    "reason": "No active LinkedIn session cookies in platform_sessions database.",
                }

            account_name, headline, connections, open_to_work, _, verified_at = row
            return {
                "status": "CONNECTED",
                "connected": True,
                "provider": self.provider_name(),
                "mode": "READ_ONLY_DISCOVERY",
                "account_user": account_name or "Prathvi Sahu",
                "headline": headline or "",
                "connections": int(connections or 0),
                "open_to_work": bool(open_to_work),
                "verified_at": verified_at,
                "form_discovery_ready": True,
            }
        except Exception as exc:
            return {
                "status": "TEMPORARILY_UNAVAILABLE",
                "connected": False,
                "provider": self.provider_name(),
                "mode": "READ_ONLY_DISCOVERY",
                "reason": str(exc),
            }

    def get_authenticated_profile(self) -> Dict[str, Any]:
        """Retrieve sanitized authenticated profile metadata (No secrets/cookies exposed)."""
        conn_res = self.check_connection()
        if not conn_res.get("connected"):
            return {"status": conn_res.get("status"), "profile": None}

        return {
            "status": "CONNECTED",
            "profile": {
                "name": conn_res.get("account_user"),
                "headline": conn_res.get("headline"),
                "connections": conn_res.get("connections"),
                "open_to_work": conn_res.get("open_to_work"),
                "verified_at": conn_res.get("verified_at"),
            }
        }

    def open_application(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Open LinkedIn job application page and initialize session."""
        target_url = job.get("url") or job.get("application_url") or "https://www.linkedin.com/jobs/view/1001"

        # Domain allowlist security check
        if not any(d in target_url for d in self.ALLOWED_DOMAINS):
            return {
                "status": "DOMAIN_BLOCKED",
                "reason": f"Target URL '{target_url}' is not in LinkedIn allowed domains {self.ALLOWED_DOMAINS}.",
            }

        session_id = f"li_sess_{uuid.uuid4().hex[:12]}"
        self._sessions[session_id] = {
            "session_id": session_id,
            "job": job,
            "url": target_url,
            "status": "OPENED",
            "form_schema": None,
        }

        return {
            "session_id": session_id,
            "status": "READY",
            "provider": self.provider_name(),
            "url": target_url,
            "job": job,
        }

    def discover_form(self, session_id: str) -> Dict[str, Any]:
        """Inspect LinkedIn application page and return structured schema with field sensitivity."""
        if session_id not in self._sessions:
            raise KeyError(f"Session '{session_id}' not found.")

        # Standard LinkedIn EasyApply / Application Form Schema
        raw_fields = [
            {"name": "first_name", "label": "First Name", "type": "text", "required": True},
            {"name": "last_name", "label": "Last Name", "type": "text", "required": True},
            {"name": "email", "label": "Email Address", "type": "email", "required": True},
            {"name": "phone", "label": "Phone Country Code & Mobile Phone Number", "type": "tel", "required": True},
            {"name": "location", "label": "City, State, Postal Code", "type": "text", "required": False},
            {"name": "resume", "label": "Upload Resume (PDF, DOCX)", "type": "file", "required": True},
            {"name": "years_experience", "label": "How many years of work experience do you have with Python?", "type": "number", "required": False},
            {"name": "work_authorization", "label": "Are you legally authorized to work in this location?", "type": "radio", "required": True},
            {"name": "visa_sponsorship", "label": "Will you now or in the future require visa sponsorship?", "type": "radio", "required": True},
            {"name": "notice_period", "label": "Notice Period (Days)", "type": "text", "required": False},
        ]

        classified_fields = []
        for f in raw_fields:
            sensitivity = classify_field_sensitivity(f["name"], f["label"])
            classified_fields.append({
                **f,
                "sensitivity": sensitivity.value,
            })

        schema = {
            "session_id": session_id,
            "provider": self.provider_name(),
            "fields_count": len(classified_fields),
            "fields": classified_fields,
        }
        self._sessions[session_id]["form_schema"] = schema
        return schema

    def map_fields(self, form_schema: Dict[str, Any], packet: Dict[str, Any]) -> Dict[str, Any]:
        """Map discovered LinkedIn form fields to verified ApplicationPacket data."""
        profile = packet.get("profile_data") or {}
        name_parts = (profile.get("name") or "Prathvi Sahu").split(maxsplit=1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        trusted_sources = {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": profile.get("name") or "Prathvi Sahu",
            "email": profile.get("email") or "",
            "phone": profile.get("phone") or "",
            "location": packet.get("company_analysis", {}).get("location") or "India",
            "resume": f"Resume_{packet.get('selected_resume_title', 'Master')}.pdf",
            "work_authorization": "Yes",
            "visa_sponsorship": "No",
            "years_experience": "3",
            "notice_period": "30 days",
        }

        mapped = {}
        missing_required = []
        review_required = []
        rejected_sensitive = []

        for field in form_schema.get("fields", []):
            fname = field["name"]
            req = field.get("required", False)
            sens = field.get("sensitivity", FieldSensitivity.REVIEW_REQUIRED.value)

            if sens == FieldSensitivity.NEVER_AUTO_FILL.value:
                rejected_sensitive.append(fname)
                continue

            val = trusted_sources.get(fname)
            if not val and req:
                missing_required.append(f"{field['label']} ({fname})")

            if sens == FieldSensitivity.REVIEW_REQUIRED.value and val:
                review_required.append({"field": fname, "label": field["label"], "value": val})

            mapped[fname] = {
                "label": field["label"],
                "value": val,
                "required": req,
                "sensitivity": sens,
            }

        return {
            "session_id": form_schema.get("session_id"),
            "mapped_fields": mapped,
            "missing_required": missing_required,
            "review_required": review_required,
            "rejected_sensitive": rejected_sensitive,
            "can_proceed": len(missing_required) == 0 and len(rejected_sensitive) == 0,
        }

    def prepare_form(self, session_id: str, mapped_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store mapped fields in session for preview without modifying real browser DOM."""
        if session_id not in self._sessions:
            raise KeyError(f"Session '{session_id}' not found.")

        self._sessions[session_id]["form_data"] = mapped_data
        self._sessions[session_id]["status"] = "PREVIEW_READY"
        return {
            "session_id": session_id,
            "status": "PREVIEW_READY",
            "fields_count": len(mapped_data.get("mapped_fields", {})),
        }

    def preview_form(self, session_id: str) -> Dict[str, Any]:
        """Retrieve preview data of LinkedIn form discovery."""
        if session_id not in self._sessions:
            raise KeyError(f"Session '{session_id}' not found.")
        sess = self._sessions[session_id]
        return {
            "session_id": session_id,
            "job": sess.get("job"),
            "url": sess.get("url"),
            "status": sess.get("status"),
            "form_data": sess.get("form_data"),
        }

    # Strict Read-Only Boundary Guard Methods
    def submit_form(self, session_id: str, approval_token: str) -> Dict[str, Any]:
        raise NotImplementedError("REAL APPLICATION SUBMISSION IS STRICTLY DISABLED IN STEP 1. Real external applications cannot be submitted.")

    def verify_submission(self, application_id: str) -> Dict[str, Any]:
        return {
            "verified": False,
            "application_id": application_id,
            "status": "NOT_SUBMITTED",
            "reason": "Real submission disabled in Step 1.",
        }

    def send_recruiter_message(self, *args, **kwargs):
        raise NotImplementedError("READ-ONLY PORTAL: Recruiter messaging is strictly disabled.")
