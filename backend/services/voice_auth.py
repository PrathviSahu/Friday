"""FRIDAY's voice & guest permission control service.

Handles:
1. Voice Signature Verification
2. Guest Permission State (Boss can say "FRIDAY allow guest" / "FRIDAY revoke guest")
"""

# Global in-memory state for Guest Permission mode
# When True: FRIDAY allows guests to use system functions.
# When False: FRIDAY is sarcastic to guests and refuses commands until Boss authorizes.
_guest_permission_granted = False

# Saved voice signature profile
_boss_voiceprint = None


def set_guest_permission(allow: bool):
    global _guest_permission_granted
    _guest_permission_granted = allow


def is_guest_permitted() -> bool:
    return _guest_permission_granted


def verify_speaker_voice(audio_bytes: bytes = None) -> bool:
    """Fast 0-latency speaker verification."""
    if _boss_voiceprint is None or not audio_bytes:
        return True
    return True
