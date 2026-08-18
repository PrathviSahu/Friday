"""backend/services/career/portal/mock_portal.py — Deterministic Mock Application Portal.

Simulates realistic job application forms, multi-page flows, field discovery, validation,
CAPTCHA/OTP challenge detection, simulated submission, and independent verification.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from backend.services.career.portal.base import (
    BaseApplicationPortal,
    FieldSensitivity,
    classify_field_sensitivity,
)


class MockApplicationPortal(BaseApplicationPortal):
    """Deterministic Mock Application Portal for Testing Safety Architecture."""

    def __init__(self, simulate_challenge: Optional[str] = None):
        self.simulate_challenge = simulate_challenge  # "CAPTCHA", "OTP", "MFA", "CHECKPOINT"
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._submissions: Dict[str, Dict[str, Any]] = {}

    def provider_name(self) -> str:
        return "mock_portal"

    def allowed_domains(self) -> List[str]:
        return ["mockportal.local", "careers.mockcorp.io", "localhost", "127.0.0.1"]

    def check_connection(self) -> Dict[str, Any]:
        return {
            "status": "CONNECTED",
            "connected": True,
            "provider": self.provider_name(),
            "mode": "MOCK_PORTAL_SAFE",
        }

    def open_application(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Open application page and initialize session."""
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        app_url = job.get("url") or job.get("application_url") or f"https://careers.mockcorp.io/apply/{job.get('id', '1')}"

        # Challenge simulation check
        if self.simulate_challenge:
            return {
                "session_id": session_id,
                "status": "CHALLENGE_REQUIRED",
                "challenge_type": self.simulate_challenge,
                "url": app_url,
                "job": job,
            }

        session_state = {
            "session_id": session_id,
            "job": job,
            "url": app_url,
            "status": "OPENED",
            "form_data": {},
            "submitted": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._sessions[session_id] = session_state

        return {
            "session_id": session_id,
            "status": "READY",
            "url": app_url,
            "job": job,
        }

    def discover_form(self, session_id: str) -> Dict[str, Any]:
        """Inspect form and return schema with sensitivity classification."""
        if session_id not in self._sessions:
            raise KeyError(f"Session '{session_id}' not found.")

        # Standard realistic application form fields
        raw_fields = [
            # Personal Info
            {"name": "first_name", "label": "First Name", "type": "text", "required": True},
            {"name": "last_name", "label": "Last Name", "type": "text", "required": True},
            {"name": "email", "label": "Email Address", "type": "email", "required": True},
            {"name": "phone", "label": "Phone Number", "type": "tel", "required": True},
            {"name": "location", "label": "Current City/Location", "type": "text", "required": False},

            # Education
            {"name": "university", "label": "University / College", "type": "text", "required": False},
            {"name": "degree", "label": "Degree / Major", "type": "text", "required": False},
            {"name": "graduation_year", "label": "Graduation Year", "type": "number", "required": False},

            # Career & Work Authorization
            {"name": "years_experience", "label": "Years of Relevant Experience", "type": "number", "required": False},
            {"name": "current_title", "label": "Current Job Title", "type": "text", "required": False},
            {"name": "notice_period", "label": "Notice Period (Days)", "type": "text", "required": False},
            {"name": "work_authorization", "label": "Are you authorized to work in this location?", "type": "select", "required": True},

            # Application Documents & Profiles
            {"name": "resume", "label": "Upload Resume", "type": "file", "required": True},
            {"name": "cover_letter", "label": "Cover Letter", "type": "textarea", "required": False},
            {"name": "linkedin", "label": "LinkedIn Profile URL", "type": "url", "required": False},
            {"name": "github", "label": "GitHub Profile URL", "type": "url", "required": False},
            {"name": "portfolio", "label": "Portfolio URL", "type": "url", "required": False},

            # Custom Questions
            {"name": "expected_salary", "label": "Expected Annual Salary", "type": "text", "required": False},
            {"name": "sponsorship", "label": "Will you now or in future require visa sponsorship?", "type": "select", "required": True},
            {"name": "relocation", "label": "Are you open to relocation?", "type": "select", "required": False},
        ]

        classified_fields = []
        for f in raw_fields:
            sensitivity = classify_field_sensitivity(f["name"], f["label"])
            classified_fields.append({
                **f,
                "sensitivity": sensitivity.value,
            })

        return {
            "session_id": session_id,
            "provider": self.provider_name(),
            "fields_count": len(classified_fields),
            "fields": classified_fields,
        }

    def map_fields(self, form_schema: Dict[str, Any], packet: Dict[str, Any]) -> Dict[str, Any]:
        """Map form fields to trusted packet data according to sensitivity policies."""
        profile = packet.get("profile_data") or {}
        name_parts = (profile.get("name") or "Candidate").split(maxsplit=1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        trusted_sources = {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": profile.get("name") or "",
            "email": profile.get("email") or "",
            "phone": profile.get("phone") or "",
            "location": packet.get("company_analysis", {}).get("location") or "India",
            "github": profile.get("github") or "",
            "linkedin": profile.get("linkedin") or "",
            "portfolio": profile.get("portfolio") or "",
            "resume": f"Resume_{packet.get('selected_resume_title', 'Master')}.pdf",
            "cover_letter": packet.get("cover_letter") or "",
            "expected_salary": packet.get("salary_analysis", {}).get("salary_fit") or "Market Standard",
            "work_authorization": "Yes",
            "sponsorship": "No",
            "relocation": "Yes",
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

            # Security Guard: NEVER autofill forbidden fields
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
        """Populate form fields in session state for preview."""
        if session_id not in self._sessions:
            raise KeyError(f"Session '{session_id}' not found.")

        self._sessions[session_id]["form_data"] = mapped_data
        self._sessions[session_id]["status"] = "PREPARED"

        return {
            "session_id": session_id,
            "status": "PREPARED",
            "fields_populated": len(mapped_data.get("mapped_fields", {})),
        }

    def preview_form(self, session_id: str) -> Dict[str, Any]:
        """Retrieve preview data of populated form."""
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

    def submit_form(self, session_id: str, approval_token: str) -> Dict[str, Any]:
        """Simulate submission with single-use approval verification."""
        if session_id not in self._sessions:
            raise KeyError(f"Session '{session_id}' not found.")

        sess = self._sessions[session_id]
        if sess.get("submitted"):
            raise RuntimeError(f"Duplicate submission blocked: Session '{session_id}' was already submitted.")

        if not approval_token or not approval_token.startswith("appr_"):
            raise ValueError("Invalid or missing single-use approval token.")

        app_id = f"mock_app_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        submission_record = {
            "application_id": app_id,
            "session_id": session_id,
            "provider": self.provider_name(),
            "job_id": sess.get("job", {}).get("id"),
            "company": sess.get("job", {}).get("company"),
            "role": sess.get("job", {}).get("title"),
            "status": "CONFIRMED",
            "confirmation_message": "Thank you for applying! Your application has been received.",
            "submitted_at": now_iso,
        }

        sess["submitted"] = True
        sess["application_id"] = app_id
        sess["status"] = "SUBMITTED"
        self._submissions[app_id] = submission_record

        return {
            "success": True,
            "application_id": app_id,
            "provider": self.provider_name(),
            "status": "CONFIRMED",
            "confirmation_message": submission_record["confirmation_message"],
            "submitted_at": now_iso,
        }

    def verify_submission(self, application_id: str) -> Dict[str, Any]:
        """Independently verify application state in mock portal registry."""
        if application_id in self._submissions:
            rec = self._submissions[application_id]
            return {
                "verified": True,
                "application_id": application_id,
                "company": rec["company"],
                "role": rec["role"],
                "status": "VERIFIED_ON_PORTAL",
                "submitted_at": rec["submitted_at"],
            }
        return {
            "verified": False,
            "application_id": application_id,
            "status": "NOT_FOUND",
            "reason": "Application ID not registered on portal.",
        }
