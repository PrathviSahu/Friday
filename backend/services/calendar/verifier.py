"""Independent Calendar Verification Module.

Independently verifies event creation against provider state.
"""

from typing import Dict, Any, Optional
from .event import compute_event_hash


class IndependentCalendarVerificationError(Exception):
    """Raised when independent verification of calendar event creation fails."""
    pass


class IndependentCalendarVerifier:
    """Independently verifies created calendar events against provider records."""

    @staticmethod
    def verify_event(
        provider: Any,
        provider_event_id: str,
        expected_title: str,
        expected_start_time: str,
        expected_end_time: str,
        expected_event_hash: str,
        should_simulate_verification_failure: bool = False
    ) -> Dict[str, Any]:
        """Verify created event independently against provider state."""

        if should_simulate_verification_failure:
            raise IndependentCalendarVerificationError(
                "VERIFICATION FAILURE: Provider event state corrupted or missing during independent audit."
            )

        if not provider_event_id:
            raise IndependentCalendarVerificationError("VERIFICATION FAILURE: Missing provider event ID.")

        event_record = provider.get_event(provider_event_id)
        if not event_record:
            raise IndependentCalendarVerificationError(
                f"VERIFICATION FAILURE: Event ID '{provider_event_id}' not found in provider store."
            )

        rec_provider_id = event_record.get("provider_event_id") or event_record.get("event_id") or event_record.get("id")
        if rec_provider_id != provider_event_id:
            raise IndependentCalendarVerificationError("VERIFICATION FAILURE: Provider event ID mismatch.")

        rec_status = event_record.get("status", "")
        if rec_status not in ("RECORDED_CREATED", "confirmed", "created"):
            raise IndependentCalendarVerificationError(
                f"VERIFICATION FAILURE: Event status is '{rec_status}', expected 'RECORDED_CREATED'."
            )

        actual_title = event_record.get("title", "").strip()
        if actual_title != expected_title.strip():
            raise IndependentCalendarVerificationError(
                f"VERIFICATION FAILURE: Title mismatch. Expected '{expected_title}', got '{actual_title}'."
            )

        actual_start = (event_record.get("start_time") or event_record.get("start") or "").strip()
        if actual_start != expected_start_time.strip():
            raise IndependentCalendarVerificationError(
                f"VERIFICATION FAILURE: Start time mismatch. Expected '{expected_start_time}', got '{actual_start}'."
            )

        actual_end = (event_record.get("end_time") or event_record.get("end") or "").strip()
        if actual_end != expected_end_time.strip():
            raise IndependentCalendarVerificationError(
                f"VERIFICATION FAILURE: End time mismatch. Expected '{expected_end_time}', got '{actual_end}'."
            )

        recalculated_hash = compute_event_hash(
            actual_title,
            actual_start,
            actual_end,
            event_record.get("location", ""),
            event_record.get("description", ""),
            event_record.get("attendees", [])
        )

        if recalculated_hash != expected_event_hash:
            raise IndependentCalendarVerificationError(
                f"VERIFICATION FAILURE: Event hash mismatch. Expected '{expected_event_hash}', got '{recalculated_hash}'."
            )

        return {
            "verified": True,
            "provider_event_id": provider_event_id,
            "title": expected_title,
            "start_time": expected_start_time,
            "end_time": expected_end_time,
            "event_hash": expected_event_hash,
            "verification_status": "PASSED_INDEPENDENT_AUDIT",
        }
