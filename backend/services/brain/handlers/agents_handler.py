"""services/brain/handlers/agents_handler.py — Specialized voice agent integrations (Meetings, WhatsApp, Docs, Calendar, Email)."""

import re
from typing import Optional
from services.memory import log_conversation


def handle_agents(lower_text: str, is_boss: bool) -> Optional[dict]:
    """Dispatches voice requests to specialized background agents."""
    # 🎙️ MEETING ASSISTANT (read-only voice access)
    if re.search(r'\b(?:meeting|action items?|action-items?)\b', lower_text) and \
       re.search(r'\b(?:summar|last|recent|action|what|any|read|show|list|search)\b', lower_text):
        try:
            from services import meeting_agent
            if re.search(r'\b(?:action\s*items?)\b', lower_text):
                items = meeting_agent.get_action_items()
                if items:
                    reply_msg = "Your meeting action items: " + "; ".join(
                        f"{it['text']}" + (f" ({it['owner']})" if it.get('owner') else "")
                        for it in items[:5]) + "."
                else:
                    reply_msg = "No pending action items from your meetings."
                log_conversation(role="assistant", message=reply_msg)
                return {"reply": reply_msg, "action": "none"}
            meetings = meeting_agent.list_meetings(limit=1)
            if meetings:
                reply_msg = meeting_agent.format_meeting_for_speech(meetings[0])
            else:
                reply_msg = "No meetings recorded yet, Prem."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "none"}
        except Exception:
            pass

    # 💬 WHATSAPP AGENT (experimental driver; approval-first send)
    if re.search(r'\b(?:whatsapp|whats\s*app|wa)\b', lower_text) and \
       re.search(r'\b(?:check|read|any|new|messages?|unread|notif)\b', lower_text):
        try:
            from services import whatsapp_agent
            if whatsapp_agent.ENABLED:
                summary = whatsapp_agent.summarize()
                if summary.get("unread_count"):
                    reply_msg = f"You have {summary['unread_count']} unread WhatsApp messages. " + "; ".join(
                        f"{c['name']} ({c['unread']})" for c in summary.get("chats", [])[:3]) + "."
                else:
                    reply_msg = "No unread WhatsApp messages."
                log_conversation(role="assistant", message=reply_msg)
                return {"reply": reply_msg, "action": "none"}
        except Exception:
            pass

    # WhatsApp send draft
    wa_send_match = re.search(
        r'\b(?:message|whatsapp|whats\s*app|text|ping)\s+(\+?\d{8,15})\s+(?:that|saying|stating|about|re)\s+(.+)$',
        lower_text,
    )
    if wa_send_match:
        try:
            from services import whatsapp_agent
            if whatsapp_agent.ENABLED:
                phone = wa_send_match.group(1)
                message = wa_send_match.group(2).strip()
                draft = whatsapp_agent.create_draft(phone, message)
                preview = f"+{draft['phone']}: \"{draft['message'][:80]}\""
                reply_msg = f"Message ready, Prem — {preview}. I won't send it until you confirm."
                log_conversation(role="assistant", message=reply_msg)
                return {
                    "reply": reply_msg,
                    "action": "whatsapp_confirm",
                    "whatsapp_draft_id": draft["id"],
                    "whatsapp_preview": {
                        "phone": draft["phone"],
                        "message": draft["message"],
                    },
                }
        except Exception:
            pass

    # 📄 DOCUMENT AI
    if re.search(r'\b(?:documents?|pdfs?|docs?|resume files?)\b', lower_text) and \
       re.search(r'\b(?:ask|summar|search|find|read|what|about|list|show)\b', lower_text):
        try:
            from services import document_agent
            reply_msg = document_agent.handle_voice_request(lower_text)
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "none"}
        except Exception:
            pass

    # 📅 CALENDAR AGENT
    if re.search(r'\b(?:calendar|schedule|meetings?|appointments?)\b', lower_text) or \
       re.search(r'\bwhat.*\b(?:today|tomorrow|week|upcoming)\b.*\b(?:plan|on)\b', lower_text):
        try:
            from services import calendar_agent
            if calendar_agent.is_configured():
                if re.search(r'\btomorrow\b', lower_text):
                    events = calendar_agent.get_day(1)
                    reply_msg = calendar_agent.format_events_for_speech(events, "tomorrow")
                elif re.search(r'\b(?:this\s+week|week\b|upcoming)\b', lower_text):
                    events = calendar_agent.get_upcoming(days=7)
                    reply_msg = calendar_agent.format_events_for_speech(events, "this week")
                else:
                    events = calendar_agent.get_today()
                    reply_msg = calendar_agent.format_events_for_speech(events, "today")
                log_conversation(role="assistant", message=reply_msg)
                return {"reply": reply_msg, "action": "none"}
        except Exception:
            pass

    # ✉️ EMAIL AGENT
    if re.search(r'\b(?:check|read|any|new|open|show|summar|what.*in)\b.*\b(?:email|emails|inbox|mail)\b|\b(?:email|mail|inbox)\s+(?:summary|update|status)\b', lower_text):
        try:
            from services import email_agent
            if email_agent.is_configured():
                summary = email_agent.summarize_inbox(limit=15)
                lines = [f"You have {summary['unread_count']} unread emails."]
                if summary["priority"]:
                    lines.append("Priority: " + "; ".join(
                        f"{m['from_name']} — {m['subject'][:40]}" for m in summary["priority"][:3]) + ".")
                if summary["by_sender"]:
                    lines.append("Top senders: " + ", ".join(
                        f"{m['name']} ({m['count']})" for m in summary["by_sender"][:4]) + ".")
                reply_msg = " ".join(lines)
                log_conversation(role="assistant", message=reply_msg)
                return {"reply": reply_msg, "action": "none"}
        except Exception:
            pass

    email_send_match = re.search(
        r'\b(?:email|mail|write|send\s+(?:an?\s+)?email|draft)\s+(?:to\s+)?([a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,})\s+(?:that|saying|stating|about|re|subject)\s+(.+)$',
        lower_text,
    )
    if email_send_match:
        try:
            from services import email_agent
            if email_agent.is_configured():
                to = email_send_match.group(1)
                message = email_send_match.group(2).strip()
                subject = "From F.R.I.D.A.Y." if len(message) > 60 else "Quick note"
                draft = email_agent.create_draft(to, subject, message)
                preview = email_agent.format_email_preview(draft)
                reply_msg = f"Draft ready, Prem — {preview}. I won't send it until you confirm."
                log_conversation(role="assistant", message=reply_msg)
                return {
                    "reply": reply_msg,
                    "action": "email_confirm",
                    "email_draft_id": draft["id"],
                    "email_preview": {
                        "to": draft["to"],
                        "subject": draft["subject"],
                        "body": draft["body"],
                    },
                }
        except Exception:
            pass

    return None
