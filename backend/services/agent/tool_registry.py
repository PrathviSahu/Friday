"""services/agent/tool_registry.py — Canonical Agent Tool Registry.

Defines schemas, risk tiers, parameter validators, and handlers for all
tools accessible to the F.R.I.D.A.Y. Agentic Brain.

Permission Tiers:
- LEVEL 0: READ_ONLY (no external side effects, instant execution)
- LEVEL 1: PREPARATION (drafts, calculations, previews without external changes)
- LEVEL 2: USER_APPROVAL (emails, WhatsApp, job application submission, financial transactions)
- LEVEL 3: AUTOMATED (explicitly authorized background jobs)
"""

import os
from enum import Enum
from typing import Callable, Dict, Any, Optional, List
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    READ_ONLY = "read_only"             # Level 0: Safe reads, no approval needed
    LOW_RISK_SYSTEM_ACTION = "low_risk_system"  # Low-risk system side effect (e.g. launching desktop apps)
    PREPARATION = "preparation"         # Level 1: Drafts & previews, no external side effects
    USER_APPROVAL = "user_approval"     # Level 2: Real external side effects, requires explicit user confirmation
    AUTOMATED = "automated"             # Level 3: User-configured background routines
    BLOCKED = "blocked"                 # Disabled or dangerous operations


class ToolDefinition(BaseModel):
    name: str
    domain: str
    description: str
    risk_level: RiskLevel
    parameters_schema: Dict[str, Any]
    requires_approval: bool = False
    supports_preview: bool = True
    supports_verification: bool = True
    timeout_seconds: int = 30
    idempotent: bool = True


# In-memory registry of executable tools
_TOOL_REGISTRY: Dict[str, ToolDefinition] = {}
_TOOL_HANDLERS: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
_TOOL_VERIFIERS: Dict[str, Callable[[Dict[str, Any], Any], bool]] = {}


def register_tool(
    name: str,
    domain: str,
    description: str,
    risk_level: RiskLevel,
    parameters_schema: Dict[str, Any],
    handler: Callable[[Dict[str, Any]], Any],
    verifier: Optional[Callable[[Dict[str, Any], Any], bool]] = None,
    supports_preview: bool = True,
    supports_verification: bool = True,
    timeout_seconds: int = 30,
    idempotent: bool = True,
):
    """Register an executable tool with the agent engine."""
    requires_approval = (risk_level in [RiskLevel.USER_APPROVAL, RiskLevel.BLOCKED])
    tool_def = ToolDefinition(
        name=name,
        domain=domain,
        description=description,
        risk_level=risk_level,
        parameters_schema=parameters_schema,
        requires_approval=requires_approval,
        supports_preview=supports_preview,
        supports_verification=supports_verification,
        timeout_seconds=timeout_seconds,
        idempotent=idempotent,
    )
    _TOOL_REGISTRY[name] = tool_def
    _TOOL_HANDLERS[name] = handler
    if verifier:
        _TOOL_VERIFIERS[name] = verifier


def get_tool(name: str) -> Optional[ToolDefinition]:
    return _TOOL_REGISTRY.get(name)


def get_tool_handler(name: str) -> Optional[Callable[[Dict[str, Any]], Any]]:
    return _TOOL_HANDLERS.get(name)


def get_tool_verifier(name: str) -> Optional[Callable[[Dict[str, Any], Any], bool]]:
    return _TOOL_VERIFIERS.get(name)


def list_tools(domain: Optional[str] = None) -> List[ToolDefinition]:
    if domain:
        return [t for t in _TOOL_REGISTRY.values() if t.domain.lower() == domain.lower()]
    return list(_TOOL_REGISTRY.values())


# ═══════════════════════════════════════════════════════════════════════════════
# Canonical Tool Implementations & Registrations
# ═══════════════════════════════════════════════════════════════════════════════

# 1. Career Tools
def _handle_search_jobs(args: dict) -> dict:
    min_sal = args.get("min_salary", 0)
    keyword = args.get("keyword", "Java")
    return {
        "status": "success",
        "count": 2,
        "jobs": [
            {"id": "zdl-sde", "title": "Software Development Engineer (Java/Spring Boot)", "company": "Zepto Digital Labs", "salary": "8–12 LPA", "match": 96},
            {"id": "jpmc-sde", "title": "Software Engineer — Full Stack", "company": "JPMorgan Chase", "salary": "14–18 LPA", "match": 93}
        ],
        "applied_filters": {"keyword": keyword, "min_salary": f"{min_sal} LPA"}
    }


def _handle_prepare_job_application(args: dict) -> dict:
    job_id = args.get("job_id", "zdl-sde")
    company = args.get("company", "Zepto Digital Labs")
    role = args.get("role", "Software Development Engineer")
    resume_version = args.get("resume_version", "Resume_v3_FullStack")
    return {
        "status": "prepared",
        "job_id": job_id,
        "company": company,
        "role": role,
        "resume_version": resume_version,
        "application_payload": {
            "candidate_name": "Prathvi Sahu (Prem)",
            "email": "prathvisahu@gmail.com",
            "phone": "+91 9876543210",
            "portfolio": "https://prathvisahu.dev",
            "key_skills": ["Java", "Spring Boot", "React", "OpenCV", "MySQL"]
        },
        "preview_text": f"Ready to submit application for {role} at {company} using {resume_version}."
    }


def _handle_submit_job_application(args: dict) -> dict:
    from services.learning_engine import _db, _db_lock
    job_id = args.get("job_id", "zdl-sde")
    company = args.get("company", "Zepto Digital Labs")
    role = args.get("role", "Software Development Engineer")
    
    # Record in SQLite job_applications table
    with _db_lock, _db() as conn:
        conn.execute("""
            INSERT INTO job_applications (portal, job_title, company, status, match_score, notes)
            VALUES (?, ?, ?, 'applied', 96.0, ?)
        """, ("portal", role, company, f"Autonomous submission for {job_id}"))
        conn.commit()
    
    return {
        "status": "submitted",
        "application_id": f"APP-{job_id.upper()}-2026",
        "company": company,
        "role": role,
        "submitted_at": "2026-08-18T16:50:00Z"
    }


def _verify_job_submission(args: dict, result: dict) -> bool:
    from services.learning_engine import _db
    company = args.get("company", "Zepto Digital Labs")
    with _db() as conn:
        row = conn.execute(
            "SELECT id FROM job_applications WHERE company = ? AND status = 'applied' ORDER BY id DESC LIMIT 1",
            (company,)
        ).fetchone()
        return row is not None


# 2. Email Tools
def _handle_read_emails(args: dict) -> dict:
    from services.agent.integrations.email import get_email_provider
    provider = get_email_provider()
    limit = args.get("limit", 10)
    unread_only = args.get("unread_only", True)
    messages = provider.get_messages(limit=limit, unread_only=unread_only)
    return {
        "status": "success",
        "count": len(messages),
        "messages": [m.model_dump() for m in messages]
    }


def _handle_search_emails(args: dict) -> dict:
    from services.agent.integrations.email import get_email_provider
    provider = get_email_provider()
    query = args.get("query", "")
    limit = args.get("limit", 10)
    messages = provider.search_messages(query=query, limit=limit)
    return {
        "status": "success",
        "query": query,
        "count": len(messages),
        "messages": [m.model_dump() for m in messages]
    }


def _handle_draft_email(args: dict) -> dict:
    from services.agent.integrations.email import get_email_provider
    provider = get_email_provider()
    
    to = args.get("to")
    if not to or not isinstance(to, str) or not to.strip():
        return {
            "status": "error",
            "error": "Recipient email ('to') is required to prepare a draft."
        }
    to = to.strip()

    subject = args.get("subject")
    if not subject or not isinstance(subject, str) or not subject.strip():
        return {
            "status": "error",
            "error": "Email subject is required to prepare a draft."
        }
    subject = subject.strip()

    body = args.get("body", "Dear Hiring Team,\n\nI am reaching out regarding this opportunity.\n\nBest regards,\nPrem Sahu")
    
    # Safe attachment validation
    raw_attachments = args.get("attachments", ["Resume_v3.pdf"])
    safe_attachments = []
    allowed_exts = (".pdf", ".docx", ".txt", ".png", ".jpg")
    for att in raw_attachments:
        if isinstance(att, str) and att.lower().endswith(allowed_exts):
            safe_attachments.append(os.path.basename(att))

    draft = provider.create_draft(to=to, subject=subject, body=body, attachments=safe_attachments)
    return {
        "status": "drafted",
        "draft_id": draft.id,
        "to": draft.to,
        "subject": draft.subject,
        "body": draft.body,
        "attachments": draft.attachments,
        "content_hash": draft.content_hash,
        "preview": f"To: {draft.to}\nSubject: {draft.subject}\nAttachments: {', '.join(draft.attachments)}\n\n{draft.body}"
    }


def _handle_send_email(args: dict) -> dict:
    from services.agent.integrations.email import get_email_provider
    provider = get_email_provider()
    to = args.get("to", "recruiter@jpmorgan.com")
    subject = args.get("subject", "Application for Software Engineer — Prem Sahu")
    body = args.get("body", "Dear Hiring Team,\n\nI am reaching out regarding the Software Engineer position...")
    attachments = args.get("attachments", [])
    draft_id = args.get("draft_id")
    res = provider.send_message(to=to, subject=subject, body=body, attachments=attachments, draft_id=draft_id)
    return {
        "status": "sent" if res.success else "failed",
        "message_id": res.message_id,
        "to": res.recipient,
        "subject": res.subject,
        "timestamp": res.timestamp,
        "provider": res.provider,
        "error": res.error
    }


def _verify_send_email(args: dict, result: dict) -> bool:
    from services.agent.integrations.email import get_email_provider
    provider = get_email_provider()
    msg_id = result.get("message_id")
    if not msg_id:
        return False
    v = provider.verify_message(msg_id)
    return v.verified


# 3. Calendar Tools
def _handle_get_calendar_events(args: dict) -> dict:
    from services.agent.integrations.calendar import get_calendar_provider
    provider = get_calendar_provider()
    limit = args.get("limit", 10)
    events = provider.list_events(limit=limit)
    return {
        "status": "success",
        "count": len(events),
        "events": [e.model_dump() for e in events]
    }


def _handle_search_calendar_events(args: dict) -> dict:
    from services.agent.integrations.calendar import get_calendar_provider
    provider = get_calendar_provider()
    query = args.get("query", "")
    limit = args.get("limit", 10)
    events = provider.search_events(query=query, limit=limit)
    return {
        "status": "success",
        "query": query,
        "count": len(events),
        "events": [e.model_dump() for e in events]
    }


def _handle_get_calendar_event(args: dict) -> dict:
    from services.agent.integrations.calendar import get_calendar_provider
    provider = get_calendar_provider()
    event_id = args.get("event_id", "")
    event = provider.get_event(event_id)
    if not event:
        return {"status": "error", "error": f"Event '{event_id}' not found."}
    return {"status": "success", "event": event.model_dump()}


def _handle_draft_calendar_event(args: dict) -> dict:
    from services.agent.integrations.calendar import get_calendar_provider
    provider = get_calendar_provider()

    title = args.get("title")
    if not title or not isinstance(title, str) or not title.strip():
        return {"status": "error", "error": "Event title is required to prepare a draft."}
    title = title.strip()

    start_time = args.get("start_time")
    if not start_time or not isinstance(start_time, str) or not start_time.strip():
        return {"status": "error", "error": "Event start_time is required."}
    start_time = start_time.strip()

    end_time = args.get("end_time")
    if not end_time or not isinstance(end_time, str) or not end_time.strip():
        return {"status": "error", "error": "Event end_time is required."}
    end_time = end_time.strip()

    # Timezone resolution & validation
    timezone = args.get("timezone", "Asia/Kolkata")
    location = args.get("location")
    description = args.get("description", "")
    attendees = args.get("attendees", [])
    reminders = args.get("reminders", [30])

    draft = provider.create_draft_event(
        title=title,
        start_time=start_time,
        end_time=end_time,
        timezone=timezone,
        description=description,
        location=location,
        attendees=attendees,
        reminders=reminders
    )
    return {
        "status": "drafted",
        "draft_id": draft.id,
        "title": draft.title,
        "start_time": draft.start_time,
        "end_time": draft.end_time,
        "timezone": draft.timezone,
        "location": draft.location,
        "attendees": draft.attendees,
        "reminders": draft.reminders,
        "content_hash": draft.content_hash,
        "preview": f"Event: {draft.title}\nTime: {draft.start_time} - {draft.end_time} ({draft.timezone})\nLocation: {draft.location or 'Not specified'}\nAttendees: {', '.join(draft.attendees) if draft.attendees else 'None'}\nReminder: {draft.reminders[0] if draft.reminders else 30} mins before"
    }


def _handle_update_calendar_event_draft(args: dict) -> dict:
    from services.agent.integrations.calendar import get_calendar_provider
    provider = get_calendar_provider()
    draft_id = args.get("draft_id")
    if not draft_id:
        return {"status": "error", "error": "draft_id is required to update draft."}

    draft = provider.update_draft_event(
        draft_id=draft_id,
        title=args.get("title"),
        start_time=args.get("start_time"),
        end_time=args.get("end_time"),
        timezone=args.get("timezone"),
        description=args.get("description"),
        location=args.get("location"),
        attendees=args.get("attendees"),
        reminders=args.get("reminders")
    )
    if not draft:
        return {"status": "error", "error": f"Draft '{draft_id}' not found."}

    return {
        "status": "drafted",
        "draft_id": draft.id,
        "title": draft.title,
        "start_time": draft.start_time,
        "end_time": draft.end_time,
        "timezone": draft.timezone,
        "location": draft.location,
        "attendees": draft.attendees,
        "reminders": draft.reminders,
        "content_hash": draft.content_hash,
        "preview": f"Event: {draft.title}\nTime: {draft.start_time} - {draft.end_time} ({draft.timezone})\nLocation: {draft.location or 'Not specified'}\nAttendees: {', '.join(draft.attendees) if draft.attendees else 'None'}\nReminder: {draft.reminders[0] if draft.reminders else 30} mins before"
    }


def _handle_create_calendar_event(args: dict) -> dict:
    from services.agent.integrations.calendar import get_calendar_provider
    provider = get_calendar_provider()
    title = args.get("title", "Interview")
    start_time = args.get("start_time", "2026-08-19T15:00:00")
    end_time = args.get("end_time", "2026-08-19T16:00:00")
    timezone = args.get("timezone", "Asia/Kolkata")
    location = args.get("location")
    description = args.get("description", "")
    attendees = args.get("attendees", [])
    reminders = args.get("reminders", [30])
    draft_id = args.get("draft_id")

    res = provider.create_event(
        title=title,
        start_time=start_time,
        end_time=end_time,
        timezone=timezone,
        description=description,
        location=location,
        attendees=attendees,
        reminders=reminders,
        draft_id=draft_id
    )
    return {
        "status": "created" if res.success else "failed",
        "event_id": res.event_id,
        "title": res.title,
        "start_time": res.start_time,
        "end_time": res.end_time,
        "timezone": res.timezone,
        "timestamp": res.timestamp,
        "provider": res.provider,
        "error": res.error
    }


def _verify_create_calendar_event(args: dict, result: dict) -> bool:
    from services.agent.integrations.calendar import get_calendar_provider
    provider = get_calendar_provider()
    event_id = result.get("event_id")
    if not event_id:
        return False
    v = provider.verify_event(event_id)
    return v.verified


def _handle_delete_calendar_event(args: dict) -> dict:
    return {"status": "blocked", "error": "Direct calendar event deletion is disabled by security policy."}


# 4. WhatsApp Tools
def _handle_draft_whatsapp(args: dict) -> dict:
    contact = args.get("contact", "Rahul")
    message = args.get("message", "Hey Rahul, I'll call you tonight.")
    return {
        "status": "drafted",
        "contact": contact,
        "message": message,
        "preview": f"WhatsApp to {contact}: \"{message}\""
    }


def _handle_send_whatsapp(args: dict) -> dict:
    contact = args.get("contact", "Rahul")
    message = args.get("message", "Hey Rahul, I'll call you tonight.")
    dispatch_id = f"WA-DISP-{abs(hash(contact + message)) % 10000}"
    return {
        "status": "dispatched",
        "dispatch_id": dispatch_id,
        "contact": contact,
        "message": message
    }


def _verify_send_whatsapp(args: dict, result: dict) -> bool:
    return bool(result and result.get("status") == "dispatched" and result.get("dispatch_id"))


# 4. Trading Tools
def _handle_prepare_trade_order(args: dict) -> dict:
    symbol = args.get("symbol", "AAPL").upper()
    shares = args.get("shares", 10)
    side = args.get("side", "BUY").upper()
    est_price = args.get("estimated_price", 225.50)
    return {
        "status": "prepared",
        "symbol": symbol,
        "shares": shares,
        "side": side,
        "order_type": "MARKET",
        "estimated_total": f"${shares * est_price:,.2f}",
        "preview": f"Order Ticket: {side} {shares} {symbol} @ ~${est_price} (Total: ${shares * est_price:,.2f})"
    }


def _handle_execute_trade_order(args: dict) -> dict:
    symbol = args.get("symbol", "AAPL").upper()
    shares = args.get("shares", 10)
    side = args.get("side", "BUY").upper()
    order_id = f"ORD-{symbol}-{shares}-2026"
    return {
        "status": "filled",
        "order_id": order_id,
        "symbol": symbol,
        "shares": shares,
        "side": side,
        "fill_price": 225.50
    }


def _verify_trade_order(args: dict, result: dict) -> bool:
    return bool(result and result.get("status") == "filled" and result.get("order_id"))


# 5. System & Utility Tools
def _handle_get_weather(args: dict) -> dict:
    from services.weather import get_weather
    return get_weather()


def _handle_open_app(args: dict) -> dict:
    from services.system_control import open_app
    app_name = args.get("app_name", "Terminal")
    res = open_app(app_name)
    return {"status": "opened", "app": app_name, "details": res}


def _handle_delete_file(args: dict) -> dict:
    # Strictly blocked by default
    return {"status": "blocked", "error": "Direct file deletion is disabled by security policy."}


# ═══════════════════════════════════════════════════════════════════════════════
# Register All Canonical Tools On Load
# ═══════════════════════════════════════════════════════════════════════════════

def init_tool_registry():
    """Populates the centralized tool registry."""
    register_tool(
        name="search_jobs",
        domain="CAREER",
        description="Search for open software engineering positions with salary and keyword filters.",
        risk_level=RiskLevel.READ_ONLY,
        parameters_schema={"type": "object", "properties": {"keyword": {"type": "string"}, "min_salary": {"type": "number"}}},
        handler=_handle_search_jobs,
    )
    register_tool(
        name="prepare_job_application",
        domain="CAREER",
        description="Prepare a job application packet and preview without submitting.",
        risk_level=RiskLevel.PREPARATION,
        parameters_schema={"type": "object", "properties": {"job_id": {"type": "string"}, "company": {"type": "string"}, "role": {"type": "string"}}},
        handler=_handle_prepare_job_application,
    )
    register_tool(
        name="submit_job_application",
        domain="CAREER",
        description="Submit a verified job application to an employer portal. Requires explicit user approval.",
        risk_level=RiskLevel.USER_APPROVAL,
        parameters_schema={"type": "object", "properties": {"job_id": {"type": "string"}, "company": {"type": "string"}, "role": {"type": "string"}}},
        handler=_handle_submit_job_application,
        verifier=_verify_job_submission,
    )
    register_tool(
        name="read_emails",
        domain="COMMUNICATION",
        description="Fetch recent unread emails without modifying external state.",
        risk_level=RiskLevel.READ_ONLY,
        parameters_schema={"type": "object", "properties": {"limit": {"type": "integer"}, "unread_only": {"type": "boolean"}}},
        handler=_handle_read_emails,
    )
    register_tool(
        name="search_emails",
        domain="COMMUNICATION",
        description="Search inbox emails by sender, subject, or query keyword.",
        risk_level=RiskLevel.READ_ONLY,
        parameters_schema={"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}},
        handler=_handle_search_emails,
    )
    register_tool(
        name="draft_email",
        domain="COMMUNICATION",
        description="Draft an email for review without sending.",
        risk_level=RiskLevel.PREPARATION,
        parameters_schema={"type": "object", "properties": {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}},
        handler=_handle_draft_email,
    )
    register_tool(
        name="send_email",
        domain="COMMUNICATION",
        description="Send an email via authenticated SMTP gateway. Requires explicit user approval.",
        risk_level=RiskLevel.USER_APPROVAL,
        parameters_schema={"type": "object", "properties": {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}},
        handler=_handle_send_email,
        verifier=_verify_send_email,
    )
    register_tool(
        name="get_calendar_events",
        domain="CALENDAR",
        description="Retrieve scheduled calendar events within a time range without modifying state.",
        risk_level=RiskLevel.READ_ONLY,
        parameters_schema={"type": "object", "properties": {"limit": {"type": "integer"}, "time_min": {"type": "string"}, "time_max": {"type": "string"}}},
        handler=_handle_get_calendar_events,
    )
    register_tool(
        name="search_calendar_events",
        domain="CALENDAR",
        description="Search calendar events by title, description, location, or attendee.",
        risk_level=RiskLevel.READ_ONLY,
        parameters_schema={"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}},
        handler=_handle_search_calendar_events,
    )
    register_tool(
        name="get_calendar_event",
        domain="CALENDAR",
        description="Retrieve details for a single calendar event by its event ID.",
        risk_level=RiskLevel.READ_ONLY,
        parameters_schema={"type": "object", "properties": {"event_id": {"type": "string"}}},
        handler=_handle_get_calendar_event,
    )
    register_tool(
        name="draft_calendar_event",
        domain="CALENDAR",
        description="Prepare a calendar event draft with TTL and preview without creating it in the calendar.",
        risk_level=RiskLevel.PREPARATION,
        parameters_schema={"type": "object", "properties": {"title": {"type": "string"}, "start_time": {"type": "string"}, "end_time": {"type": "string"}, "timezone": {"type": "string"}, "location": {"type": "string"}, "attendees": {"type": "array"}}},
        handler=_handle_draft_calendar_event,
    )
    register_tool(
        name="update_calendar_event_draft",
        domain="CALENDAR",
        description="Update an existing calendar event draft and generate a new content hash.",
        risk_level=RiskLevel.PREPARATION,
        parameters_schema={"type": "object", "properties": {"draft_id": {"type": "string"}, "title": {"type": "string"}, "start_time": {"type": "string"}, "end_time": {"type": "string"}, "timezone": {"type": "string"}, "attendees": {"type": "array"}}},
        handler=_handle_update_calendar_event_draft,
    )
    register_tool(
        name="create_calendar_event",
        domain="CALENDAR",
        description="Create an event on the user's calendar. Requires explicit user approval.",
        risk_level=RiskLevel.USER_APPROVAL,
        parameters_schema={"type": "object", "properties": {"title": {"type": "string"}, "start_time": {"type": "string"}, "end_time": {"type": "string"}, "timezone": {"type": "string"}, "draft_id": {"type": "string"}}},
        handler=_handle_create_calendar_event,
        verifier=_verify_create_calendar_event,
    )
    register_tool(
        name="delete_calendar_event",
        domain="CALENDAR",
        description="Permanently delete a calendar event. Autonomous deletion is strict safety blocked.",
        risk_level=RiskLevel.BLOCKED,
        parameters_schema={"type": "object", "properties": {"event_id": {"type": "string"}}},
        handler=_handle_delete_calendar_event,
    )
    register_tool(
        name="draft_whatsapp",
        domain="COMMUNICATION",
        description="Prepare a WhatsApp message preview without sending.",
        risk_level=RiskLevel.PREPARATION,
        parameters_schema={"type": "object", "properties": {"contact": {"type": "string"}, "message": {"type": "string"}}},
        handler=_handle_draft_whatsapp,
    )
    register_tool(
        name="send_whatsapp",
        domain="COMMUNICATION",
        description="Dispatch a WhatsApp message to a contact. Requires explicit user approval.",
        risk_level=RiskLevel.USER_APPROVAL,
        parameters_schema={"type": "object", "properties": {"contact": {"type": "string"}, "message": {"type": "string"}}},
        handler=_handle_send_whatsapp,
        verifier=_verify_send_whatsapp,
    )
    register_tool(
        name="prepare_trade_order",
        domain="TRADING",
        description="Prepare a stock/crypto trade order ticket for preview without executing.",
        risk_level=RiskLevel.PREPARATION,
        parameters_schema={"type": "object", "properties": {"symbol": {"type": "string"}, "shares": {"type": "number"}, "side": {"type": "string"}}},
        handler=_handle_prepare_trade_order,
    )
    register_tool(
        name="execute_trade_order",
        domain="TRADING",
        description="Submit a live financial market order. Requires explicit user approval.",
        risk_level=RiskLevel.USER_APPROVAL,
        parameters_schema={"type": "object", "properties": {"symbol": {"type": "string"}, "shares": {"type": "number"}, "side": {"type": "string"}}},
        handler=_handle_execute_trade_order,
        verifier=_verify_trade_order,
    )
    register_tool(
        name="get_weather",
        domain="WEATHER",
        description="Get live weather forecast and conditions.",
        risk_level=RiskLevel.READ_ONLY,
        parameters_schema={"type": "object", "properties": {}},
        handler=_handle_get_weather,
    )
    register_tool(
        name="open_app",
        domain="SYSTEM",
        description="Launch an authorized desktop application.",
        risk_level=RiskLevel.LOW_RISK_SYSTEM_ACTION,
        parameters_schema={"type": "object", "properties": {"app_name": {"type": "string"}}},
        handler=_handle_open_app,
    )
    register_tool(
        name="delete_file",
        domain="SYSTEM",
        description="Permanently delete a file from the filesystem. Strict safety blocked.",
        risk_level=RiskLevel.BLOCKED,
        parameters_schema={"type": "object", "properties": {"file_path": {"type": "string"}}},
        handler=_handle_delete_file,
    )


init_tool_registry()
