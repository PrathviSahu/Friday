"""services/brain/handlers/security_handler.py — Guest permissions and identity corrections."""

from typing import Optional
from services.voice_auth import set_guest_permission
from services.memory import save_fact, log_conversation


def handle_security_and_permissions(lower_text: str, is_boss: bool) -> Optional[dict]:
    """Handles guest access permissions and name spelling correction."""
    if not is_boss:
        return None

    if any(kw in lower_text for kw in ["allow guest", "grant guest", "let them speak", "give permission"]):
        set_guest_permission(True)
        reply_msg = "Guest access granted, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "allow_guest"}

    if any(kw in lower_text for kw in ["revoke guest", "stop guest", "lock guest"]):
        set_guest_permission(False)
        reply_msg = "Guest access revoked, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "revoke_guest"}

    # Auto-correct name spelling in incoming transcript before memory or processing
    if any(kw in lower_text for kw in ["prithvi", "p r i t h v i", "r a not i", "spelling is"]):
        save_fact("boss_name", "Prathvi Sahu", "identity")
        save_fact("boss_name_spelling", "P-R-A-T-H-V-I S-A-H-U", "identity")

    return None
