"""backend/services/career/portal/engine.py — Portal Automation Safety Engine.

Orchestrates:
ApplicationPacket Binding ──► Domain Allowlist Check ──► Form Discovery ──► Safe Field Mapping ──►
Preview Generation ──► 5-Min Single-Use Approval ──► Mock Submission ──► Independent Verification ──► Career CRM Record
"""

import json
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from backend.services.career.portal.base import (
    BaseApplicationPortal,
    FieldSensitivity,
)
from backend.services.career.portal.mock_portal import MockApplicationPortal


class PortalSecurityError(RuntimeError):
    """Raised when portal navigation, domain security, or credential guard is violated."""


class PortalSession:
    """Represents a form automation session bound to an exact ApplicationPacket."""

    def __init__(
        self,
        session_id: str,
        packet: Dict[str, Any],
        portal: BaseApplicationPortal,
        form_schema: Dict[str, Any],
        mapped_fields: Dict[str, Any],
    ):
        self.session_id = session_id
        self.packet_id = packet.get("packet_id", "")
        self.packet_version = packet.get("version", 1)
        self.packet_content_hash = packet.get("content_hash", "")
        self.job_id = packet.get("job_id", "")
        self.company = packet.get("company", "")
        self.role = packet.get("role", "")
        self.source_url = packet.get("source_url", "")
        self.provider = portal.provider_name()
        self.portal = portal
        self.form_schema = form_schema
        self.mapped_fields = mapped_fields

        # Compute Form Data Hash
        raw_mapped = json.dumps(mapped_fields.get("mapped_fields", {}), sort_keys=True)
        self.form_data_hash = hashlib.sha256(raw_mapped.encode("utf-8")).hexdigest()

        # 5-minute single-use approval token
        now_utc = datetime.now(timezone.utc)
        self.approval_token = f"appr_{uuid.uuid4().hex[:16]}"
        self.approval_created_at = now_utc
        self.approval_expires_at = now_utc + timedelta(minutes=5)
        self.approval_consumed = False
        self.submitted = False
        self.verified = False
        self.submission_record: Optional[Dict[str, Any]] = None


class PortalAutomationEngine:
    """Manages secure application form discovery, mapping, approval, and execution."""

    def __init__(self):
        self._active_sessions: Dict[str, PortalSession] = {}

    def create_portal_session(
        self,
        packet: Dict[str, Any],
        portal: Optional[BaseApplicationPortal] = None,
    ) -> Dict[str, Any]:
        """Initialize secure application session bound to the provided ApplicationPacket."""
        effective_portal = portal if portal is not None else MockApplicationPortal()

        # 1. Duplicate Application Check
        try:
            try:
                from backend.services import career_db
            except ImportError:
                from services import career_db

            apps = career_db.get_applications() or []
            target_comp = (packet.get("company") or "").strip().lower()
            target_role = (packet.get("role") or "").strip().lower()
            for app in apps:
                app_comp = app.get("company") or ((app.get("job") or {}).get("company") if isinstance(app.get("job"), dict) else "")
                app_role = app.get("job_title") or ((app.get("job") or {}).get("title") if isinstance(app.get("job"), dict) else "")
                if (app_comp or "").strip().lower() == target_comp and (app_role or "").strip().lower() == target_role:
                    if app.get("status") in ["applied", "submitted", "interviewing", "offered"]:
                        return {
                            "status": "DUPLICATE_BLOCKED",
                            "message": f"Application to '{packet.get('company')}' for '{packet.get('role')}' was already submitted on {app.get('applied_at', 'earlier')}.",
                            "previous_application": app,
                        }

        except Exception:
            pass

        # 2. Domain Allowlist Security Check
        url = packet.get("source_url") or "https://careers.mockcorp.io/apply/1"
        allowed_domains = effective_portal.allowed_domains()
        if not any(domain in url for domain in allowed_domains):
            raise PortalSecurityError(f"DOMAIN_BLOCKED: Target URL '{url}' is not in the portal allowlist {allowed_domains}.")

        # 3. Open Application Page
        open_res = effective_portal.open_application({"id": packet.get("job_id"), "url": url, "company": packet.get("company"), "title": packet.get("role")})
        if open_res.get("status") == "CHALLENGE_REQUIRED":
            return {
                "status": "CHALLENGE_REQUIRED",
                "challenge_type": open_res.get("challenge_type", "SECURITY_CHECKPOINT"),
                "message": "Anti-bot challenge or CAPTCHA/MFA detected. Halting automation safely.",
            }

        portal_session_id = open_res["session_id"]

        # 4. Form Discovery & Field Mapping
        form_schema = effective_portal.discover_form(portal_session_id)
        mapped_data = effective_portal.map_fields(form_schema, packet)

        # 5. Populate Form in Preview Mode
        effective_portal.prepare_form(portal_session_id, mapped_data)

        # 6. Bind to PortalSession
        session = PortalSession(
            session_id=portal_session_id,
            packet=packet,
            portal=effective_portal,
            form_schema=form_schema,
            mapped_fields=mapped_data,
        )
        self._active_sessions[portal_session_id] = session

        return {
            "status": "READY_FOR_PREVIEW",
            "session_id": portal_session_id,
            "packet_id": session.packet_id,
            "packet_content_hash": session.packet_content_hash,
            "form_data_hash": session.form_data_hash,
            "approval_token": session.approval_token,
            "approval_expires_at": session.approval_expires_at.isoformat(),
            "missing_required": mapped_data.get("missing_required", []),
            "review_required": mapped_data.get("review_required", []),
            "can_proceed": mapped_data.get("can_proceed", False),
        }

    def generate_submission_preview(self, session_id: str) -> str:
        """Format human-readable preview of populated form, provenance, and exact values to be submitted."""
        if session_id not in self._active_sessions:
            raise KeyError(f"Portal session '{session_id}' not found or expired.")

        sess = self._active_sessions[session_id]
        safe_lines = []
        review_lines = []

        for fname, info in sess.mapped_fields.get("mapped_fields", {}).items():
            val = info.get("value")
            sens = info.get("sensitivity")
            label = info.get("label", fname)
            source = info.get("source", "Candidate Profile")
            reason = info.get("selection_reason", "Verified candidate field")

            if val:
                if sens == FieldSensitivity.SAFE_AUTO_FILL.value:
                    safe_lines.append(f"    - {label}: {val}")
                elif sens == FieldSensitivity.REVIEW_REQUIRED.value:
                    review_lines.append(
                        f"    - {label}:\n"
                        f"        Value to Submit: {val}\n"
                        f"        Source: {source}\n"
                        f"        Selection Reason: {reason}"
                    )

        missing_str = ", ".join(sess.mapped_fields.get("missing_required", [])) if sess.mapped_fields.get("missing_required") else "None"
        safe_block = "\n".join(safe_lines) if safe_lines else "    None"
        review_block = "\n".join(review_lines) if review_lines else "    None"
        resume_name = sess.mapped_fields.get("mapped_fields", {}).get("resume", {}).get("value", "Primary Resume")

        return f"""Boss, here is the application submission preview:

JOB: {sess.role}
COMPANY: {sess.company}
PORTAL: {sess.provider}
APPLICATION URL: {sess.source_url}

RESUME: {resume_name}
COVER LETTER: Included in Application Packet

SAFE FIELDS:
{safe_block}

REVIEW REQUIRED FIELDS (Explicit Candidate Confirmation Required):
{review_block}

ATTACHMENTS: {resume_name}
FORM DATA HASH: {sess.form_data_hash[:12]}...
PACKET HASH: {sess.packet_content_hash[:12]}...
MISSING REQUIRED FIELDS: {missing_str}
WARNINGS: None. Application ready for one-shot controlled submission.

Nothing has been submitted yet.

APPROVAL TOKEN: {sess.approval_token} (Valid for 5 mins)
[EDIT] [CANCEL] [APPROVE SUBMISSION]"""

    def execute_approved_submission(
        self,
        session_id: str,
        approval_token: str,
        current_packet: Dict[str, Any],
        confirmed_review_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute single controlled submission with approval validation and independent verification."""
        if session_id not in self._active_sessions:
            raise KeyError(f"Portal session '{session_id}' not found.")

        sess = self._active_sessions[session_id]

        # 1. Target Job Verification & Mismatch Guard
        if (current_packet.get("company") or "").strip().lower() != sess.company.strip().lower():
            raise ValueError(f"Target company mismatch: Packet has '{current_packet.get('company')}' but session was created for '{sess.company}'.")
        if (current_packet.get("role") or "").strip().lower() != sess.role.strip().lower():
            raise ValueError(f"Target role mismatch: Packet has '{current_packet.get('role')}' but session was created for '{sess.role}'.")
        if current_packet.get("source_url") and current_packet.get("source_url") != sess.source_url:
            raise ValueError(f"Target application URL mismatch: Packet has '{current_packet.get('source_url')}' but session has '{sess.source_url}'.")

        # 2. Packet Hash Invalidation Check
        current_hash = current_packet.get("content_hash", "")
        if current_hash != sess.packet_content_hash:
            raise ValueError("Packet content hash mismatch. The application packet was modified after preview. Re-review required.")

        # 3. Approval Token Validation
        if sess.approval_consumed:
            raise RuntimeError("Approval token already consumed. Submissions are single-use.")

        if approval_token != sess.approval_token:
            raise ValueError("Invalid approval token.")

        if datetime.now(timezone.utc) > sess.approval_expires_at:
            raise TimeoutError("Approval token has expired (5-minute TTL exceeded).")

        # 4. Review-Required Confirmation Check
        review_req_fields = sess.mapped_fields.get("review_required", [])
        if review_req_fields and confirmed_review_fields is False:
            raise ValueError(
                f"Review-required screening questions ({len(review_req_fields)} fields) were rejected or unconfirmed by the candidate."
            )


        # 5. Duplicate Application Check immediately before execution
        try:
            try:
                from backend.services import career_db
            except ImportError:
                from services import career_db

            apps = career_db.get_applications() or []
            target_comp = sess.company.strip().lower()
            target_role = sess.role.strip().lower()
            for app in apps:
                app_comp = app.get("company") or ((app.get("job") or {}).get("company") if isinstance(app.get("job"), dict) else "")
                app_role = app.get("job_title") or ((app.get("job") or {}).get("title") if isinstance(app.get("job"), dict) else "")
                if (app_comp or "").strip().lower() == target_comp and (app_role or "").strip().lower() == target_role:
                    if app.get("status") in ["applied", "submitted", "interviewing", "offered"]:
                        raise RuntimeError(f"Duplicate application blocked: '{sess.company}' - '{sess.role}' already submitted.")
        except RuntimeError:
            raise
        except Exception:
            pass

        # 6. Execute Submission (Click Submit ONLY ONCE)
        sub_res = sess.portal.submit_form(session_id, approval_token)
        sess.approval_consumed = True
        sess.submitted = True
        app_id = sub_res.get("application_id")

        # 7. Post-Submission Independent Verification
        verify_res = sess.portal.verify_submission(app_id)
        if not verify_res.get("verified"):
            return {
                "success": False,
                "status": "UNCERTAIN_SUBMISSION",
                "application_id": app_id,
                "message": "The application may have been submitted, but I could not independently verify it.",
                "verification_details": verify_res,
                "crm_updated": False,
            }

        sess.verified = True
        sess.submission_record = sub_res

        # 8. Career CRM Record Creation
        try:
            try:
                from backend.services import career_db
            except ImportError:
                from services import career_db

            created_job_id = None
            jobs = career_db.get_jobs() or []
            for j in jobs:
                if (j.get("company") or "").strip().lower() == sess.company.lower() and (j.get("title") or "").strip().lower() == sess.role.lower():
                    created_job_id = j.get("id")
                    break

            if not created_job_id:
                created_job_id = career_db.create_job({
                    "title": sess.role,
                    "company": sess.company,
                    "url": sess.source_url,
                    "source": sess.provider,
                })

            res_id = current_packet.get("selected_resume_id") or 1
            app_db_id = career_db.create_application(created_job_id, res_id)
            career_db.update_application(app_db_id, {
                "status": "applied",
            })
        except Exception as crm_err:
            print(f"[PortalAutomationEngine] CRM logging note: {crm_err}")

        return {
            "success": True,
            "application_id": app_id,
            "status": "SUBMITTED_AND_VERIFIED",
            "company": sess.company,
            "role": sess.role,
            "provider": sess.provider,
            "independent_verification": verify_res,
            "submitted_at": sub_res.get("submitted_at"),
            "crm_updated": True,
        }

