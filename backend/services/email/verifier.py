"""Independent Email Dispatch Verification Module.

Never trust send_result.success alone. Independently verifies message dispatch
against provider state.
"""

from typing import Dict, Any, Optional
from .draft import compute_content_hash


class IndependentVerificationError(Exception):
    """Raised when independent verification of email dispatch fails."""
    pass


class IndependentVerifier:
    """Independently verifies dispatched email messages against provider outbox records."""

    @staticmethod
    def verify_delivery(
        provider: Any,
        provider_message_id: str,
        expected_recipient: str,
        expected_subject: str,
        expected_content_hash: str,
        should_simulate_verification_failure: bool = False
    ) -> Dict[str, Any]:
        """Verify dispatched message independently against provider state."""

        if should_simulate_verification_failure:
            raise IndependentVerificationError(
                "VERIFICATION FAILURE: Provider record state corrupted or missing during independent audit."
            )

        if not provider_message_id:
            raise IndependentVerificationError("VERIFICATION FAILURE: Missing provider message ID.")

        # Query provider outbox independently
        message_record = provider.get_message(provider_message_id)
        if not message_record:
            raise IndependentVerificationError(
                f"VERIFICATION FAILURE: Message ID '{provider_message_id}' not found in provider outbox."
            )

        # 1. Message ID exists
        if message_record.get("provider_message_id") != provider_message_id:
            raise IndependentVerificationError("VERIFICATION FAILURE: Provider message ID mismatch.")

        # 2. Status is RECORDED_SENT
        if message_record.get("status") != "RECORDED_SENT":
            raise IndependentVerificationError(
                f"VERIFICATION FAILURE: Provider message status is '{message_record.get('status')}', expected 'RECORDED_SENT'."
            )

        # 3. Recipient matches
        actual_recipient = message_record.get("recipient", "").strip().lower()
        if actual_recipient != expected_recipient.strip().lower():
            raise IndependentVerificationError(
                f"VERIFICATION FAILURE: Recipient mismatch. Expected '{expected_recipient}', got '{actual_recipient}'."
            )

        # 4. Subject matches
        actual_subject = message_record.get("subject", "").strip()
        if actual_subject != expected_subject.strip():
            raise IndependentVerificationError(
                f"VERIFICATION FAILURE: Subject mismatch. Expected '{expected_subject}', got '{actual_subject}'."
            )

        # 5. Content Hash matches
        actual_body = message_record.get("body", "")
        actual_attachments = message_record.get("attachments", [])
        recalculated_hash = compute_content_hash(actual_recipient, actual_subject, actual_body, actual_attachments)

        if recalculated_hash != expected_content_hash:
            raise IndependentVerificationError(
                f"VERIFICATION FAILURE: Content hash mismatch. Expected '{expected_content_hash}', got '{recalculated_hash}'."
            )

        return {
            "verified": True,
            "provider_message_id": provider_message_id,
            "recipient": expected_recipient,
            "subject": expected_subject,
            "content_hash": expected_content_hash,
            "verification_status": "PASSED_INDEPENDENT_AUDIT",
        }
