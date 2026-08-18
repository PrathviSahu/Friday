"""backend/services/career/portal/base.py — Base Application Portal Abstract Interface and Field Sensitivity Classification.

Defines the contract for portal discovery, form mapping, autofill, preview, submission, and independent verification.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional


class FieldSensitivity(str, Enum):
    """Field sensitivity classification policy."""
    SAFE_AUTO_FILL = "SAFE_AUTO_FILL"        # Standard verified contact & profile info
    REVIEW_REQUIRED = "REVIEW_REQUIRED"      # Salary expectation, notice period, work auth, sponsorship
    NEVER_AUTO_FILL = "NEVER_AUTO_FILL"      # Passwords, OTP, MFA, CAPTCHAs, banking, security questions


# Categorization mappings
SAFE_AUTOFILL_FIELDS = {
    "first_name", "last_name", "full_name", "email", "preferred_email", "phone",
    "phone_number", "preferred_phone", "location", "city", "address", "github",
    "github_url", "linkedin", "linkedin_url", "portfolio", "portfolio_url",
    "resume", "resume_file", "cover_letter", "cover_letter_text", "university",
    "degree", "graduation_year", "skills"
}

REVIEW_REQUIRED_FIELDS = {
    "expected_salary", "target_salary", "min_salary", "notice_period",
    "notice_period_days", "work_authorization", "visa_sponsorship", "visa_required",
    "relocation", "remote_preference", "years_experience", "current_title"
}

NEVER_AUTOFILL_FIELDS = {
    "password", "pwd", "otp", "one_time_password", "mfa", "mfa_code", "2fa", "2fa_code",
    "captcha", "captcha_code", "security_answer", "security_question", "bank_account",
    "routing_number", "ssn", "aadhaar", "pan_card", "api_key", "secret_key", "vault_key"
}


def classify_field_sensitivity(field_name: str, field_label: str = "") -> FieldSensitivity:
    """Classify form field into SAFE_AUTO_FILL, REVIEW_REQUIRED, or NEVER_AUTO_FILL."""
    combined = f"{field_name.lower()} {field_label.lower()}".strip()

    for forbidden in NEVER_AUTOFILL_FIELDS:
        if forbidden in combined:
            return FieldSensitivity.NEVER_AUTO_FILL

    for review_kw in REVIEW_REQUIRED_FIELDS:
        if review_kw in combined:
            return FieldSensitivity.REVIEW_REQUIRED

    for safe_kw in SAFE_AUTOFILL_FIELDS:
        if safe_kw in combined:
            return FieldSensitivity.SAFE_AUTO_FILL

    # Default unknown fields to REVIEW_REQUIRED for safety
    return FieldSensitivity.REVIEW_REQUIRED


class BaseApplicationPortal(ABC):
    """Abstract Base Interface for Application Portals."""

    @abstractmethod
    def provider_name(self) -> str:
        """Unique portal identifier string."""
        pass

    @abstractmethod
    def allowed_domains(self) -> List[str]:
        """List of allowed domain names for this portal."""
        pass

    @abstractmethod
    def check_connection(self) -> Dict[str, Any]:
        """Check portal connectivity and session readiness."""
        pass

    @abstractmethod
    def open_application(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize application session on portal page."""
        pass

    @abstractmethod
    def discover_form(self, session_id: str) -> Dict[str, Any]:
        """Inspect the current application form and produce structured schema."""
        pass

    @abstractmethod
    def map_fields(self, form_schema: Dict[str, Any], packet: Dict[str, Any]) -> Dict[str, Any]:
        """Map form fields to trusted Career OS packet data."""
        pass

    @abstractmethod
    def prepare_form(self, session_id: str, mapped_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fill form in preview mode without executing submission."""
        pass

    @abstractmethod
    def preview_form(self, session_id: str) -> Dict[str, Any]:
        """Retrieve preview representation of populated form."""
        pass

    @abstractmethod
    def submit_form(self, session_id: str, approval_token: str) -> Dict[str, Any]:
        """Execute submission with verified single-use approval."""
        pass

    @abstractmethod
    def verify_submission(self, application_id: str) -> Dict[str, Any]:
        """Independently verify submitted application status on the portal."""
        pass
