"""backend/services/career/remoteok_provider.py — RemoteOK Public Job Feed Provider (Read/Search Only).

Provides access to remote developer jobs via public REST API without browser automation or credential scraping.
STRICT READ-ONLY BOUNDARY: No applications, submissions, or messaging.
"""

import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from backend.services.career.provider import BaseJobProvider


class RemoteOKJobProvider(BaseJobProvider):
    """RemoteOK Job Provider using public REST feed.

    STRICT READ-ONLY BOUNDARY: No form-filling, auto-apply, or messaging.
    """

    API_URL = "https://remoteok.com/api"
    USER_AGENT = "FRIDAY-CareerOS/2.0 (Career Intelligence Agent)"

    def __init__(self, timeout: int = 10, max_results: int = 10):
        self.timeout = timeout
        self.max_results = max_results

    def provider_name(self) -> str:
        return "remoteok"

    def check_connection(self) -> Dict[str, Any]:
        """Check RemoteOK public feed availability without sending unnecessary data."""
        try:
            req = urllib.request.Request(
                self.API_URL,
                headers={"User-Agent": self.USER_AGENT}
            )
            # Lightweight head/get check with low timeout
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return {
                        "status": "CONNECTED",
                        "connected": True,
                        "provider": self.provider_name(),
                        "mode": "READ/SEARCH_ONLY",
                        "api_endpoint": self.API_URL,
                    }
                else:
                    return {
                        "status": "TEMPORARILY_UNAVAILABLE",
                        "connected": False,
                        "provider": self.provider_name(),
                        "mode": "READ/SEARCH_ONLY",
                        "reason": f"HTTP status {resp.status}",
                    }
        except Exception as exc:
            return {
                "status": "TEMPORARILY_UNAVAILABLE",
                "connected": False,
                "provider": self.provider_name(),
                "mode": "READ/SEARCH_ONLY",
                "reason": str(exc),
            }

    def search_jobs(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Fetch and normalize jobs from RemoteOK public feed."""
        filters = filters or {}
        q_clean = (query or "").strip().lower()
        tag = filters.get("tag") or (q_clean.split()[0] if q_clean else "")

        url = f"{self.API_URL}?tag={urllib.parse.quote(tag)}" if tag else self.API_URL

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": self.USER_AGENT, "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if not isinstance(data, list):
                return []

            results: List[Dict[str, Any]] = []
            # Skip first element if it's the API legal disclaimer
            job_items = [item for item in data if isinstance(item, dict) and "position" in item or "title" in item]

            for raw in job_items:
                title = raw.get("position") or raw.get("title") or ""
                company = raw.get("company") or ""
                desc = raw.get("description") or ""

                if q_clean and (q_clean not in title.lower() and q_clean not in desc.lower() and q_clean not in company.lower()):
                    continue

                raw_formatted = {
                    "id": f"remoteok_{raw.get('id', '')}",
                    "title": title,
                    "company": company,
                    "location": raw.get("location") or "Worldwide Remote",
                    "remote_type": "remote",
                    "salary_raw": f"${raw.get('salary_min', 0):,}-${raw.get('salary_max', 0):,}" if raw.get("salary_min") else (raw.get("salary") or ""),
                    "salary_min": float(raw.get("salary_min") or 0.0),
                    "salary_max": float(raw.get("salary_max") or 0.0),
                    "skills": raw.get("tags") or [],
                    "description": desc,
                    "url": raw.get("url") or f"https://remoteok.com/remote-jobs/{raw.get('id', '')}",
                    "posted_at": raw.get("date") or "",
                    "application_url": raw.get("apply_url") or raw.get("url") or "",
                }

                results.append(self.normalize_job(raw_formatted))
                if len(results) >= self.max_results:
                    break

            return results
        except Exception as exc:
            exc_str = str(exc).lower()
            if "timeout" in exc_str or "timed out" in exc_str:
                raise RuntimeError("TEMPORARILY_UNAVAILABLE: RemoteOK request timed out.") from exc
            return []

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return None

    # Strict Read-Only Boundary Guards
    def apply_to_job(self, *args, **kwargs):
        raise NotImplementedError("READ/SEARCH ONLY: Automatic applications are strictly disabled.")

    def submit_application_form(self, *args, **kwargs):
        raise NotImplementedError("READ/SEARCH ONLY: Form submissions are strictly disabled.")

    def send_recruiter_message(self, *args, **kwargs):
        raise NotImplementedError("READ/SEARCH ONLY: Recruiter messaging is strictly disabled.")
