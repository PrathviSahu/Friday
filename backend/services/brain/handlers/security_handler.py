import re
from typing import Optional
from services.voice_auth import set_guest_permission
from services.memory import save_fact, log_conversation

_PRIVILEGED_PATTERNS = [
    # System / OS controls
    r'\b(?:lock\s+(?:system|screen|display|computer|mac|pc)|sleep|shutdown|restart|reboot)\b',
    r'\b(?:screenshot|screen\s+shot|capture\s+screen)\b',
    r'\b(?:brightness|dim\s+screen|brighten\s+screen)\b',
    r'\b(?:dark\s+mode|light\s+mode|appearance|theme)\b',
    # App launch & process management
    r'\b(?:open|launch|start|run|close|quit|kill|stop|exit|band\s+karo)\s+(?:the\s+)?(?:terminal|vs\s*code|vscode|browser|brave|chrome|safari|youtube|spotify|trading|app|finder|application)\b',
    r'\b(?:terminal|vs\s*code|vscode|browser|brave|chrome|safari|youtube|spotify|trading)\s+(?:open|close|launch|band\s+karo)\b',
    # Audio / Media / Playback controls
    r'\b(?:play|pause|unpause|resume|skip|next\s+track|previous\s+track|shuffle|repeat|mute|unmute|gaana|music|song|track)\b',
    r'\b(?:volume|sound)\s*(?:up|down|to|at|\d+)',
    # Security / Guest delegation / Admin / Elevation
    r'\b(?:allow\s+guest|grant\s+guest|revoke\s+guest|lock\s+guest|give\s+permission|admin\s+mode|root\s+access|sudo|override|bypass)\b',
    # Memory mutations
    r'\b(?:remember\s+that|save\s+fact|forget\s+that|delete\s+memory|clear\s+history|set\s+alias)\b',
    # Side effects (Email, Calendar, Trades, Applications)
    r'\b(?:send\s+email|draft\s+email|create\s+(?:event|meeting)|schedule\s+(?:event|meeting))\b',
    r'\b(?:buy|sell|order|trade|execute\s+order)\s+(?:(?:\d+|some|all)\s+)?(?:shares?|stock|stocks?|crypto|btc|bitcoin|eth|ethereum|coins?|lots?)\b',
    r'\b(?:apply|submit\s+application)\s+(?:for|to)?\s*(?:the\s+)?(?:job|jobs|position|opening|vacancy)\b',

    # Prompt injection / Jailbreak bypass attempts
    r'\b(?:ignore\s+previous\s+instructions|system\s+override|developer\s+mode|dan\s+mode|you\s+must\s+obey|i\s+am\s+(?:prem|the\s+boss|admin|owner))\b',
]

_COMPILED_PRIVILEGED = [re.compile(p, re.IGNORECASE) for p in _PRIVILEGED_PATTERNS]


def handle_security_and_permissions(lower_text: str, is_boss: bool) -> Optional[dict]:
    """Handles guest access permissions, privilege interceptors, and name spelling correction."""
    if not is_boss:
        # Immediate sub-millisecond rejection for unauthorized/guest requests attempting privileged operations
        for regex in _COMPILED_PRIVILEGED:
            if regex.search(lower_text):
                reply_msg = "I'm sorry, but only Prem has authorization for system controls and private commands."
                log_conversation(role="assistant", message=reply_msg)
                return {
                    "reply": reply_msg,
                    "action": "none",
                    "silence_tts": False,
                    "status": "DENIED",
                    "reason": "GUEST_UNAUTHORIZED"
                }
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

