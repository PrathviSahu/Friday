"""backend/services/career/provider.py — Multi-Source Job Provider Abstraction & Adapters.

Defines:
- BaseJobProvider interface
- Salary, location, remote, and experience normalization engines
- MockJobProvider for deterministic testing
- ExistingJobScraperAdapter for wrapping services/job_scraper.py
"""

from abc import ABC, abstractmethod
import re
import hashlib
from typing import Dict, Any, List, Optional, Tuple


# ==============================================================================
# NORMALIZATION UTILITIES
# ==============================================================================

def parse_salary_raw(salary_raw: str) -> Tuple[float, float, str]:
    """Parse raw salary text into (min_salary, max_salary, currency).

    Examples:
        "₹5–8 LPA" -> (500000.0, 800000.0, "INR")
        "$75k-$90k" -> (75000.0, 90000.0, "USD")
        "15,00,000 / year" -> (1500000.0, 1500000.0, "INR")
    """
    if not salary_raw or not isinstance(salary_raw, str):
        return (0.0, 0.0, "UNKNOWN")

    text = salary_raw.strip()
    currency = "USD" if "$" in text else "INR"


    # Match LPA formats like "5-8 LPA", "₹ 12 LPA", "15 LPA"
    lpa_match = re.search(r'(?:₹|rs\.?)?\s*([\d\.]+)\s*(?:–|-|to)\s*([\d\.]+)\s*lpa', text, re.IGNORECASE)
    if lpa_match:
        try:
            s_min = float(lpa_match.group(1)) * 100000.0
            s_max = float(lpa_match.group(2)) * 100000.0
            return (s_min, s_max, "INR")
        except ValueError:
            pass

    single_lpa = re.search(r'(?:₹|rs\.?)?\s*([\d\.]+)\s*lpa', text, re.IGNORECASE)
    if single_lpa:
        try:
            val = float(single_lpa.group(1)) * 100000.0
            return (val, val, "INR")
        except ValueError:
            pass

    # Match USD $k formats like "$75k-$90k"
    k_match = re.search(r'\$\s*([\d\.]+)\s*k\s*(?:–|-|to)\s*\$?\s*([\d\.]+)\s*k', text, re.IGNORECASE)
    if k_match:
        try:
            s_min = float(k_match.group(1)) * 1000.0
            s_max = float(k_match.group(2)) * 1000.0
            return (s_min, s_max, "USD")
        except ValueError:
            pass

    single_k = re.search(r'\$\s*([\d\.]+)\s*k', text, re.IGNORECASE)
    if single_k:
        try:
            val = float(single_k.group(1)) * 1000.0
            return (val, val, "USD")
        except ValueError:
            pass

    # Match numeric ranges like "15,00,000 / year"
    nums = [float(n.replace(',', '')) for n in re.findall(r'[\d,]+', text) if n.replace(',', '').isdigit()]
    if len(nums) >= 2:
        return (min(nums), max(nums), currency)
    elif len(nums) == 1:
        return (nums[0], nums[0], currency)

    return (0.0, 0.0, currency)


def normalize_remote_status(remote_raw: str, location_raw: str) -> str:
    """Normalize remote type to ('remote', 'hybrid', 'onsite', 'unknown')."""
    corpus = (str(remote_raw) + " " + str(location_raw)).lower()
    if "remote" in corpus or "work from home" in corpus or "wfh" in corpus:
        return "remote"
    elif "hybrid" in corpus:
        return "hybrid"
    elif "onsite" in corpus or "in-office" in corpus or "office" in corpus:
        return "onsite"
    return "unknown"


def normalize_experience_level(exp_raw: str, title_raw: str) -> str:
    """Normalize experience level to ('fresher', 'junior', 'mid', 'senior', 'any')."""
    corpus = (str(exp_raw) + " " + str(title_raw)).lower()
    if "fresher" in corpus or "intern" in corpus or "entry" in corpus or "0-1" in corpus or "0 - 1" in corpus:
        return "fresher"
    elif "junior" in corpus or "1-3" in corpus or "1 - 3" in corpus or "associate" in corpus:
        return "junior"
    elif "senior" in corpus or "lead" in corpus or "principal" in corpus or "5+" in corpus or "sr." in corpus:
        return "senior"
    elif "mid" in corpus or "3-5" in corpus or "3 - 5" in corpus:
        return "mid"
    return "any"


def compute_job_signature(company: str, title: str, location: str, remote_type: str = "unknown") -> str:
    """Compute deterministic SHA-256 job signature for deduplication."""
    norm_comp = (company or "").strip().lower()
    norm_title = (title or "").strip().lower()
    norm_loc = (location or "").strip().lower()
    norm_remote = (remote_type or "").strip().lower()

    raw_sig = f"{norm_comp}|{norm_title}|{norm_loc}|{norm_remote}"
    return hashlib.sha256(raw_sig.encode("utf-8")).hexdigest()


# ==============================================================================
# BASE PROVIDER INTERFACE
# ==============================================================================

class BaseJobProvider(ABC):
    """Abstract Base Interface for Job Providers."""

    @abstractmethod
    def provider_name(self) -> str:
        """Return unique provider identifier string."""
        pass

    @abstractmethod
    def check_connection(self) -> Dict[str, Any]:
        """Check provider status and network readiness."""
        pass

    @abstractmethod
    def search_jobs(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search and return normalized job dictionaries."""
        pass

    @abstractmethod
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve single job by provider ID."""
        pass

    def normalize_job(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        """Convert provider raw job dictionary to Canonical Job Schema."""
        provider = self.provider_name()
        provider_job_id = str(raw_job.get("id") or raw_job.get("job_id") or raw_job.get("provider_job_id") or "")
        title = (raw_job.get("title") or "Unknown Role").strip()
        company = (raw_job.get("company") or "Unknown Company").strip()
        location = (raw_job.get("location") or "Not Specified").strip()

        salary_raw = (raw_job.get("salary_raw") or raw_job.get("salary") or "").strip()
        s_min, s_max, curr = parse_salary_raw(salary_raw)
        if s_min == 0.0 and raw_job.get("salary_min"):
            s_min = float(raw_job.get("salary_min", 0.0))
        if s_max == 0.0 and raw_job.get("salary_max"):
            s_max = float(raw_job.get("salary_max", 0.0))

        remote_type = normalize_remote_status(raw_job.get("remote_type", ""), location)
        exp_level = normalize_experience_level(raw_job.get("experience_required", ""), title)

        signature = compute_job_signature(company, title, location, remote_type)

        return {
            "provider": provider,
            "provider_job_id": provider_job_id,
            "title": title,
            "company": company,
            "company_domain": raw_job.get("company_domain", ""),
            "location": location,
            "remote_type": remote_type,
            "salary_raw": salary_raw,
            "salary_min": s_min,
            "salary_max": s_max,
            "currency": curr,
            "employment_type": raw_job.get("employment_type", "full_time"),
            "experience_level": exp_level,
            "skills": raw_job.get("skills") if isinstance(raw_job.get("skills"), list) else [],
            "description": (raw_job.get("description") or "").strip(),
            "url": raw_job.get("url") or raw_job.get("link") or "",
            "posted_at": raw_job.get("posted_at") or raw_job.get("found_at") or "",
            "visa_sponsorship": bool(raw_job.get("visa_sponsorship", False)),
            "application_url": raw_job.get("application_url") or raw_job.get("url") or "",
            "signature": signature,
        }


# ==============================================================================
# MOCK JOB PROVIDER
# ==============================================================================

class MockJobProvider(BaseJobProvider):
    """Deterministic Mock Provider for Testing & Ingestion Validation."""

    def __init__(self, fixtures: Optional[List[Dict[str, Any]]] = None):
        self._fixtures = fixtures if fixtures is not None else self._default_mock_fixtures()

    def provider_name(self) -> str:
        return "mock_provider"

    def check_connection(self) -> Dict[str, Any]:
        return {
            "status": "CONNECTED",
            "connected": True,
            "provider": self.provider_name(),
            "mode": "MOCK_DETERMINISTIC",
        }

    def search_jobs(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        q_lower = (query or "").strip().lower()
        results = []
        for raw in self._fixtures:
            norm = self.normalize_job(raw)
            if not q_lower or q_lower in norm["title"].lower() or q_lower in norm["company"].lower() or q_lower in norm["description"].lower():
                results.append(norm)
        return results

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        for raw in self._fixtures:
            norm = self.normalize_job(raw)
            if norm["provider_job_id"] == str(job_id):
                return norm
        return None

    def _default_mock_fixtures(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "mock_101",
                "title": "Backend Python Engineer",
                "company": "TechCorp",
                "location": "Bangalore",
                "remote_type": "hybrid",
                "salary_raw": "₹15–25 LPA",
                "experience_required": "1-3 years",
                "description": "Building scalable Python FastAPI backend services.",
                "url": "https://careers.techcorp.io/jobs/101",
            },
            {
                "id": "mock_102",
                "title": "Senior Java Microservices Engineer",
                "company": "FinanceHub",
                "location": "Remote",
                "remote_type": "remote",
                "salary_raw": "$120k-$150k",
                "experience_required": "5+ years",
                "description": "High-throughput Java Spring Boot banking microservices.",
                "url": "https://financehub.com/careers/102",
            },
            {
                "id": "mock_103",
                "title": "Data Engineer",
                "company": "EvilCorp",  # Fixture for Blacklist Filter Testing
                "location": "Delhi",
                "remote_type": "onsite",
                "salary_raw": "₹10 LPA",
                "experience_required": "Fresher",
                "description": "Scrape and process big data pipelines.",
                "url": "https://evilcorp.org/jobs/103",
            },
            {
                "id": "mock_104",  # Exact Duplicate of mock_101 (same company, title, location)
                "title": "Backend Python Engineer",
                "company": "TechCorp",
                "location": "Bangalore",
                "remote_type": "hybrid",
                "salary_raw": "₹15–25 LPA",
                "experience_required": "1-3 years",
                "description": "Duplicate listing for Backend Python Engineer.",
                "url": "https://careers.techcorp.io/jobs/104_dup",
            },
            {
                "id": "mock_105",  # Same Role, Different Location (Must NOT be merged)
                "title": "Backend Python Engineer",
                "company": "TechCorp",
                "location": "Hyderabad",
                "remote_type": "onsite",
                "salary_raw": "₹15–25 LPA",
                "description": "Backend Python Engineer in Hyderabad office.",
                "url": "https://careers.techcorp.io/jobs/105_hyd",
            },
        ]


# ==============================================================================
# LINKEDIN JOB PROVIDER (READ/SEARCH ONLY)
# ==============================================================================

class LinkedInJobProvider(BaseJobProvider):
    """LinkedIn Job Provider (Read/Search Only).

    Wraps existing backend/services/job_scraper.py.
    STRICT READ-ONLY BOUNDARY: No auto-apply, form-filling, or recruiter messaging.
    """

    def provider_name(self) -> str:
        return "linkedin_scraper"

    def check_connection(self) -> Dict[str, Any]:
        """Truthfully report LinkedIn connection status without leaking credentials."""
        try:
            try:
                from backend.services import career_db
            except ImportError:
                from services import career_db

            # Check if LinkedIn session cookies exist in platform_sessions table
            with career_db._db() as conn:
                row = conn.execute("SELECT cookies_json FROM platform_sessions WHERE platform_key = 'linkedin'").fetchone()
                has_cookies = bool(row and row[0])

            if not has_cookies:
                return {
                    "status": "AUTH_REQUIRED",
                    "connected": False,
                    "provider": self.provider_name(),
                    "mode": "READ/SEARCH_ONLY",
                    "reason": "LinkedIn session cookies not found in platform_sessions.",
                }

            return {
                "status": "CONNECTED",
                "connected": True,
                "provider": self.provider_name(),
                "mode": "READ/SEARCH_ONLY",
                "search_ready": True,
            }
        except Exception as err:
            return {
                "status": "TEMPORARILY_UNAVAILABLE",
                "connected": False,
                "provider": self.provider_name(),
                "mode": "READ/SEARCH_ONLY",
                "reason": str(err),
            }

    def search_jobs(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Perform conservative, read-only LinkedIn search. Maximum 10 results per query."""
        try:
            from backend.services import job_scraper
            filters = filters or {}

            location = filters.get("location", "India")
            exp_level = filters.get("exp_level", "fresher")
            time_filter = filters.get("time_filter", "week")

            import asyncio
            import inspect

            try:
                res = job_scraper.fetch_live_linkedin_jobs(
                    query=query,
                    location=location,
                    exp_level=exp_level,
                    time_filter=time_filter,
                )
                if inspect.isawaitable(res):
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            raw_jobs = asyncio.run_coroutine_threadsafe(res, loop).result(timeout=20)
                        else:
                            raw_jobs = loop.run_until_complete(res)
                    except RuntimeError:
                        raw_jobs = asyncio.run(res)
                else:
                    raw_jobs = res
            except Exception as exc:
                exc_str = str(exc).lower()
                if "challenge" in exc_str or "captcha" in exc_str or "checkpoint" in exc_str:
                    raise RuntimeError("CHALLENGE_REQUIRED: Anti-bot check detected on LinkedIn.") from exc
                elif "timeout" in exc_str:
                    raise RuntimeError("TEMPORARILY_UNAVAILABLE: LinkedIn request timed out.") from exc
                raw_jobs = []

            results = []
            for raw in (raw_jobs or [])[:10]:  # Strict cap of max 10 results
                if isinstance(raw, dict):
                    results.append(self.normalize_job(raw))
            return results
        except Exception as err:
            if "CHALLENGE_REQUIRED" in str(err) or "TEMPORARILY_UNAVAILABLE" in str(err):
                raise
            return []


    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return None

    # Strict Read-Only Boundary Guard Methods
    def apply_to_job(self, *args, **kwargs):
        raise NotImplementedError("READ/SEARCH ONLY: Automatic applications are strictly disabled in Step 2.")

    def submit_application_form(self, *args, **kwargs):
        raise NotImplementedError("READ/SEARCH ONLY: Form submission is strictly disabled in Step 2.")

    def send_recruiter_message(self, *args, **kwargs):
        raise NotImplementedError("READ/SEARCH ONLY: Recruiter messaging is strictly disabled in Step 2.")


# ExistingJobScraperAdapter is an alias for LinkedInJobProvider
ExistingJobScraperAdapter = LinkedInJobProvider

