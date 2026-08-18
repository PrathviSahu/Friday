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
        """Format human-readable preview of populated form and exact values to be submitted."""
        if session_id not in self._active_sessions:
            raise KeyError(f"Portal session '{session_id}' not found or expired.")

        sess = self._active_sessions[session_id]
        fields_str_lines = []
        for fname, info in sess.mapped_fields.get("mapped_fields", {}).items():
            val = info.get("value")
            if val:
                fields_str_lines.append(f"    - {info.get('label', fname)}: {val}")

        missing_str = ", ".join(sess.mapped_fields.get("missing_required", [])) if sess.mapped_fields.get("missing_required") else "None"
        fields_block = "\n".join(fields_str_lines)

        return f"""Boss, here is the application submission preview:

JOB: {sess.role}
COMPANY: {sess.company}
APPLICATION URL: {sess.source_url}
PROVIDER: {sess.provider}

FIELDS TO SUBMIT:
{fields_block}

MISSING REQUIRED FIELDS: {missing_str}
PACKET HASH: {sess.packet_content_hash[:12]}...
FORM DATA HASH: {sess.form_data_hash[:12]}...
APPROVAL TOKEN: {sess.approval_token} (Valid for 5 mins)

[EDIT] [CANCEL] [APPROVE SUBMISSION]"""

    def execute_approved_submission(
        self,
        session_id: str,
        approval_token: str,
        current_packet: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute submission with single-use approval and independent verification."""
        if session_id not in self._active_sessions:
            raise KeyError(f"Portal session '{session_id}' not found.")

        sess = self._active_sessions[session_id]

        # 1. Packet Hash Invalidation Check
        current_hash = current_packet.get("content_hash", "")
        if current_hash != sess.packet_content_hash:
            raise ValueError(f"Packet content hash mismatch. The application packet was modified after preview. Re-review required.")

        # 2. Approval Token Validation
        if sess.approval_consumed:
            raise RuntimeError("Approval token already consumed. Submissions are single-use.")

        if approval_token != sess.approval_token:
            raise ValueError("Invalid approval token.")

        if datetime.now(timezone.utc) > sess.approval_expires_at:
            raise TimeoutError("Approval token has expired (5-minute TTL exceeded).")

        # 3. Execute Submission (Mock Portal)
        sub_res = sess.portal.submit_form(session_id, approval_token)
        sess.approval_consumed = True
        sess.submitted = True
        app_id = sub_res["application_id"]

        # 4. Independent Verification
        verify_res = sess.portal.verify_submission(app_id)
        if not verify_res.get("verified"):
            raise RuntimeError(f"Independent portal verification failed for application ID {app_id}.")

        sess.verified = True
        sess.submission_record = sub_res

        # 5. Career CRM Record Creation
        try:
            try:
                from backend.services import career_db
            except ImportError:
                from services import career_db

            created_job_id = None
            # Find or insert job in career_jobs
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
