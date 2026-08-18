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

    # 💬 WhatsApp Open Chat & Type Message
    m_open_msg = re.search(r'\b(?:open\s+(?:the\s+)?(?:whatsapp|whats\s*app|wa)\s+(?:and\s+)?)?(?:message|msg|text|ping)\s+(?:to\s+)?(.+?)\s+(?:saying|that|stating|about|ki|say|type|:)\s+(.+)$', lower_text)
    if m_open_msg and not lower_text.startswith(('whatsapp pe', 'whats app pe', 'wa pe')):
        contact = m_open_msg.group(1).replace('whatsapp', '').replace('and message', '').replace('and text', '').strip()
        contact = re.sub(r'^(?:and|to)\s+', '', contact).strip()
        msg = m_open_msg.group(2).strip()
        if contact and msg:
            from services.system_control import open_whatsapp_chat
            open_whatsapp_chat(contact, msg)
            reply_msg = f"Opening chat with '{contact}' and typing your message, Prem."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "open_whatsapp_chat", "target": contact, "message": msg}

    m_type = re.search(r'\b(?:open\s+(?:the\s+)?(?:whatsapp\s+)?chat\s*(?:with|of)?\s*(.+?)\s+and\s+type\s+(.+))\b|\b(?:open\s+(.+?)\s+chat\s+and\s+type\s+(.+))\b', lower_text)
    if m_type:
        c = (m_type.group(1) or m_type.group(3) or '').strip()
        c = re.sub(r'^(?:with|of)\s+', '', c).strip()
        m = (m_type.group(2) or m_type.group(4) or '').strip()
        if c and m:
            from services.system_control import open_whatsapp_chat
            open_whatsapp_chat(c, m)
            reply_msg = f"Opening chat with '{c}' and typing your message, Prem."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "open_whatsapp_chat", "target": c, "message": m}

    m_msg = re.search(r'\b(?:message|whatsapp|whats\s*app|text|ping)\s+(.+?)\s+(?:that|saying|stating|about|ki|say|type|:)\s+(.+)$', lower_text)
    if m_msg and not lower_text.startswith(('whatsapp pe', 'whats app pe', 'wa pe')):
        c = m_msg.group(1).strip()
        m = m_msg.group(2).strip()
        if c and m and not re.match(r'^\+?\d{8,15}$', c):
            from services.system_control import open_whatsapp_chat
            open_whatsapp_chat(c, m)
            reply_msg = f"Opening chat with '{c}' and typing your message, Prem."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "open_whatsapp_chat", "target": c, "message": m}

    m_hin = re.search(r'\b(?:whatsapp|whats\s*app|wa)\s+(?:pe|mein|par)\s+(.+?)\s*(?:ko)?\s+(?:message|msg|text)\s+(?:karo|bhejo|likho)\s*(?:ki|saying|that)?\s*(.+)\b', lower_text)
    if m_hin:
        c = m_hin.group(1).strip()
        m = m_hin.group(2).strip()
        if c and m:
            from services.system_control import open_whatsapp_chat
            open_whatsapp_chat(c, m)
            reply_msg = f"Opening chat with '{c}' and typing your message, Prem."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "open_whatsapp_chat", "target": c, "message": m}

    # 📂 WhatsApp Open Chat Only
    m_open = (
        re.search(r'\b(?:open\s+(?:the\s+)?(?:whatsapp\s+)?chat\s*(?:with|of)\s+(.+))\b', lower_text)
        or re.search(r'\b(?:open\s+(.+?)\s+chat(?:\s+on\s+whatsapp)?)\b', lower_text)
        or re.search(r'\b(?:search\s+(?:for\s+)?(.+?)\s+(?:on\s+whatsapp\s+)?and\s+open\s+chat)\b', lower_text)
    )
    if m_open and not any(w in lower_text for w in ["and type", "saying", "that", "message"]):
        c = (m_open.group(1) or '').replace('on whatsapp', '').replace('with', '').replace('of', '').strip()
        if c and c.lower() not in ["whatsapp", "whats app", "the app"]:
            from services.system_control import open_whatsapp_chat
            open_whatsapp_chat(c)
            reply_msg = f"Opening chat with '{c}' on WhatsApp, Prem."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "open_whatsapp_chat", "target": c}

    # 🚀 Send Pending Message
    if re.search(r'^(?:send\s+it|send\s+(?:the\s+)?message|bhej\s+do|send\s+karo)$', lower_text):
        from services.system_control import press_whatsapp_send_desktop
        press_whatsapp_send_desktop()
        reply_msg = "Message sent on WhatsApp, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "send_it"}

    # 🧹 WhatsApp Clear Search
    if re.search(r'\b(?:clear|remove|reset|close)\s+(?:the\s+)?(?:search|filter)\s+(?:from|in|on)?\s*(?:whatsapp|whats\s*app|wa)\b', lower_text) and not re.search(r'\band\s+(?:search|find)\b', lower_text):
        from services.system_control import clear_whatsapp_search_desktop
        clear_whatsapp_search_desktop()
        reply_msg = "Cleared WhatsApp search filter, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "clear_whatsapp_search"}

    # 🔍 WhatsApp Search Contact / Message (Supports English, Hindi & Hinglish)
    wa_search_match = (
        re.search(r'\b(?:clear\s+(?:the\s+)?(?:whatsapp|whats\s*app|wa)?\s*(?:search|filter)?\s*(?:from|in|on)?\s*(?:whatsapp|whats\s*app|wa)?\s+and\s+(?:search|find|look\s+for)\s*(?:again)?)\s+(?:for\s+)?(.+)\b', lower_text)
        or re.search(r'\b(?:search|find|look\s+for|dhoondo)\s+(?:for\s+)?(.+?)\s+(?:on|in|via|pe)\s+(?:whatsapp|whats\s*app|wa)\b', lower_text)
        or re.search(r'\b(?:on|in|via|pe)\s+(?:whatsapp|whats\s*app|wa)\s*,?\s*(?:search|find|look\s+for|dhoondo)\s+(?:again\s+)?(?:for\s+)?(.+)\b', lower_text)
        or re.search(r'\b(?:whatsapp|whats\s*app|wa)\s+(?:pe|mein|par)\s+(.+?)(?:\s+ko)?\s+(?:dhoondo|search\s+karo|find\s+karo|search|find)\b', lower_text)
        or re.search(r'\b(?:open\s+)?(?:the\s+)?(?:whatsapp|whats\s*app|wa)\s*(?:and|then|,)?\s*(?:search|find|look\s+for|dhoondo)\s*(?:again\s+)?(?:for\s+)?(.+)\b', lower_text)
    )
    if wa_search_match:
        target = next((g.strip() for g in wa_search_match.groups() if g and g.strip()), "")
        target = re.sub(r'^(?:again\s+|for\s+)', '', target).rstrip(".?! ").strip()
        if target:
            from services.system_control import search_whatsapp_desktop
            search_whatsapp_desktop(target)
            try:
                from services.brain.context_manager import update_context
                update_context(domain="WHATSAPP", task="whatsapp_search", intent="search_contact")
            except Exception:
                pass
            reply_msg = f"Searching for '{target}' on WhatsApp, Prem."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "search_whatsapp", "target": target}

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
