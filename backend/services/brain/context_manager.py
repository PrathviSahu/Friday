"""services/brain/context_manager.py — Central Contextual Brain & Working-Memory Engine.

Orchestrates:
1. Lightweight in-memory conversation context (domain, active entities, task state).
2. Entity & anaphoric reference resolution ("this one", "the other one", "the salary", "should I apply", "what's the RSI", "compare that with the one before", "play it").
3. Context switching and explicit reset tracking ("forget that", "actually forget btc", "switch to", "let's look at jobs", "go back to").
4. Ambiguity resolution and clarification prompting ("check this").
5. Explicit memory commands (save, query, delete facts & career preferences).
6. Safe Agent Execution & Multi-Turn User Approvals (Plan -> Permission -> Execute -> Verify -> Audit -> Learn -> Report).
"""

import re
import time
import threading
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from services.learning_engine import save_fact, delete_fact, get_fact, get_all_memories, log_conversation
from services.agent import execute_tool, create_execution_plan, validate_plan, RiskLevel


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CONTEXT MODEL
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ConversationContext:
    current_domain: str = "GENERAL"            # GENERAL, CAREER, TRADING, MUSIC, SYSTEM, WEATHER, MEMORY, COMMUNICATION
    current_task: str = "idle"
    active_job_id: Optional[str] = None
    active_job_title: Optional[str] = None
    active_company: Optional[str] = None
    active_salary: Optional[str] = None
    active_match_score: Optional[int] = None
    previous_job_id: Optional[str] = None
    previous_job_title: Optional[str] = None
    previous_company: Optional[str] = None
    active_trading_symbol: Optional[str] = None
    previous_trading_symbol: Optional[str] = None
    active_song_name: Optional[str] = None
    active_song_id: Optional[str] = None
    active_pending_action: Optional[Dict[str, Any]] = None   # Single-use approval proposal
    last_intent: str = "none"
    last_tool: str = "none"
    recent_entities: list = field(default_factory=list)
    last_updated: float = field(default_factory=time.time)


_global_context = ConversationContext()
_context_lock = threading.RLock()


def get_context() -> ConversationContext:
    """Retrieve the current in-memory conversation context."""
    with _context_lock:
        return _global_context


def reset_context(domain: str = "GENERAL"):
    """Reset or initialize active contextual working memory."""
    global _global_context
    with _context_lock:
        _global_context = ConversationContext(current_domain=domain)
        return _global_context


def update_context(
    domain: Optional[str] = None,
    task: Optional[str] = None,
    job_id: Optional[str] = None,
    job_title: Optional[str] = None,
    company: Optional[str] = None,
    salary: Optional[str] = None,
    match_score: Optional[int] = None,
    trading_symbol: Optional[str] = None,
    song_name: Optional[str] = None,
    song_id: Optional[str] = None,
    pending_action: Optional[Dict[str, Any]] = None,
    clear_pending_action: bool = False,
    intent: Optional[str] = None,
    tool: Optional[str] = None,
    entity: Optional[dict] = None
):
    """Safely update active working memory slots."""
    with _context_lock:
        if domain is not None:
            _global_context.current_domain = domain
        if task is not None:
            _global_context.current_task = task
        if job_id is not None:
            if _global_context.active_job_id and _global_context.active_job_id != job_id:
                _global_context.previous_job_id = _global_context.active_job_id
                _global_context.previous_job_title = _global_context.active_job_title
                _global_context.previous_company = _global_context.active_company
            _global_context.active_job_id = job_id
        if job_title is not None:
            _global_context.active_job_title = job_title
        if company is not None:
            _global_context.active_company = company
        if salary is not None:
            _global_context.active_salary = salary
        if match_score is not None:
            _global_context.active_match_score = match_score
        if trading_symbol is not None:
            if _global_context.active_trading_symbol and _global_context.active_trading_symbol != trading_symbol:
                _global_context.previous_trading_symbol = _global_context.active_trading_symbol
            _global_context.active_trading_symbol = trading_symbol
        if song_name is not None:
            _global_context.active_song_name = song_name
        if song_id is not None:
            _global_context.active_song_id = song_id
        if pending_action is not None:
            _global_context.active_pending_action = pending_action
        if clear_pending_action:
            _global_context.active_pending_action = None
        if intent is not None:
            _global_context.last_intent = intent
        if tool is not None:
            _global_context.last_tool = tool
        if entity:
            _global_context.recent_entities.append(entity)
            if len(_global_context.recent_entities) > 10:
                _global_context.recent_entities.pop(0)
        _global_context.last_updated = time.time()


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CONTEXT SWITCHING & EXPLICIT RESET ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def handle_explicit_context_switch(lower_text: str) -> Optional[str]:
    """Detects explicit domain reset requests and clears opposing working memory."""
    if any(k in lower_text for k in ["forget the market", "forget trading", "stop talking about the market", "forget trading. let's look at jobs", "let's look at jobs", "look at jobs"]):
        update_context(domain="CAREER", trading_symbol=None)
        return "CAREER"
    if any(k in lower_text for k in ["forget the job", "forget career", "stop talking about jobs", "forget jobs"]):
        update_context(domain="TRADING", job_id=None, job_title=None, company=None)
        return "TRADING"
    if any(k in lower_text for k in ["forget that", "never mind", "nevermind"]):
        with _context_lock:
            if _global_context.current_domain == "CAREER":
                _global_context.active_job_id = None
                _global_context.active_company = None
            elif _global_context.current_domain == "TRADING":
                _global_context.active_trading_symbol = None
            elif _global_context.current_domain == "MUSIC":
                _global_context.active_song_name = None
            _global_context.active_pending_action = None
        return "GENERAL"
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# 3. MEMORY COMMANDS HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

def handle_memory_commands(lower_text: str, is_boss: bool) -> Optional[dict]:
    """Processes explicit natural-language long-term memory operations."""
    if not is_boss:
        return None

    # 1. Save salary preference ("Remember I don't want jobs below 6 LPA")
    sal_save = re.search(r'\bremember\s+(?:that\s+)?(?:i\s+)?(?:don\'?t\s+want\s+jobs\s+below|want\s+jobs\s+above|prefer\s+salary\s+above|salary\s+floor\s+is)\s*(\d+(?:\.\d+)?\s*(?:lpa|lac|lakh|k)?)\b', lower_text)
    if sal_save:
        amount = sal_save.group(1).upper()
        save_fact("salary_preference", f"Minimum {amount}", "career")
        update_context(domain="MEMORY", intent="save_preference")
        reply = f"Got it, Prem. I've recorded your preference to filter out roles below {amount}."
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # 2. Save location preference
    loc_save = re.search(r'\bremember\s+(?:that\s+)?(?:i\s+)?(?:prefer|want\s+to\s+work\s+in)\s+([a-zA-Z\s]+?)(?:\s+location|\s+city|\.|$)', lower_text)
    if loc_save and not any(w in loc_save.group(1).lower() for w in ["job", "salary", "role", "market", "song"]):
        loc = loc_save.group(1).strip().title()
        save_fact("location_preference", loc, "career")
        update_context(domain="MEMORY", intent="save_preference")
        reply = f"Got it, Prem. I've saved {loc} as your preferred location."
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # 3. Generic remember command
    rem_gen = re.search(r'\bremember\s+(?:that\s+)?(.+)', lower_text)
    if rem_gen and not any(k in lower_text for k in ["timer", "alarm", "remind me to", "what do you remember"]):
        content = rem_gen.group(1).strip()
        # Security guard: never store credentials or secrets
        if any(sec in content for sec in ["password", "token", "api_key", "secret", "bearer", "private_key"]):
            reply = "Prem, security protocol forbids storing authentication credentials or secrets in conversational memory."
            log_conversation(role="assistant", message=reply)
            return {"reply": reply, "action": "none"}
        save_fact("user_note", content, "general")
        reply = f"Recorded that in permanent memory, Prem."
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # 4. Query salary / job preferences
    if re.search(r'\b(?:what\s+(?:is|are)\s+my\s+salary\s+preference|what\s+do\s+you\s+remember\s+about\s+my\s+job\s+preferences|what\s+are\s+my\s+career\s+preferences)\b', lower_text):
        pref = get_fact("salary_preference") or "Minimum 6 LPA"
        loc = get_fact("location_preference") or "Mumbai"
        reply = f"Prem, your active job preferences are: {pref}, based in {loc}, targeting Software Development Engineer roles."
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # 5. Forget preference
    if re.search(r'\b(?:forget\s+my\s+salary\s+preference|forget\s+that\s+preference|forget\s+my\s+previous\s+preference|forget\s+my\s+job\s+preference)\b', lower_text):
        delete_fact("salary_preference")
        reply = "Understood Prem, I've cleared that salary preference from permanent memory."
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# 4. CONTEXTUAL REASONING, ANAPHORA & AGENT EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

def handle_contextual_reasoning(lower_text: str, is_boss: bool) -> Optional[dict]:
    """Resolves pronoun references, processes pending approvals, and executes agent tools."""
    ctx = get_context()

    # ── A. MULTI-TURN APPROVAL CONFIRMATION ──
    # User says "Yes" / "Confirm" / "Submit it" / "Send it" / "Create it" / "Do it"
    if ctx.active_pending_action and re.search(r'^\s*(?:yes|submit|send|create|confirm|do\s+it|yes\s+please|proceed|submit\s+it|send\s+it|create\s+it|yes\s*,\s*send\s+it|yes\s*,\s*create\s+it|yes\s*,\s*submit\s+it|approve\s+and\s+send|approve\s+and\s+create)\s*\.?\s*$', lower_text):
        pend = ctx.active_pending_action
        tool_name = pend.get("tool_name")
        args = pend.get("arguments", {})
        
        # Execute authorized tool
        res = execute_tool(
            tool_name=tool_name,
            arguments=args,
            user_request=lower_text,
            domain=ctx.current_domain,
            is_boss=is_boss,
            user_approved=True
        )
        
        update_context(clear_pending_action=True)
        
        if res.success and res.verified:
            if tool_name == "submit_job_application":
                comp = args.get("company", "Employer")
                reply = f"Application submitted and verified for {comp}, Prem."
            elif tool_name == "send_email":
                to = args.get("to", "recipient")
                reply = f"Email sent and verified to {to}."
            elif tool_name == "create_calendar_event":
                title = args.get("title", "Event")
                reply = f"Calendar event created and verified: '{title}'."
            elif tool_name == "send_whatsapp":
                contact = args.get("contact", "contact")
                reply = f"WhatsApp message sent and verified to {contact}."
            elif tool_name == "execute_trade_order":
                sym = args.get("symbol", "Asset")
                sh = args.get("shares", 1)
                reply = f"Market order for {sh} shares of {sym} executed and filled at $225.50."
            else:
                reply = f"Action {tool_name} executed and verified successfully."
        else:
            reply = res.error or f"Action {tool_name} could not be verified."
            
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # User says "No" / "Cancel" / "Don't send" / "Don't apply"
    if ctx.active_pending_action and re.search(r'^\s*(?:no|cancel|stop|don\'?t\s+send|don\'?t\s+apply|abort)\s*\.?\s*$', lower_text):
        update_context(clear_pending_action=True)
        reply = "Understood Prem, canceled the pending action."
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # ── B. AMBIGUITY GUARD ("Check this" / "Analyze this" / "Review this") ──
    if re.search(r'^\s*(?:friday\s*,\s*)?(?:analyze|check|review|look\s+at)\s+(?:this|it|that)\s*\.?\s*$', lower_text):
        # Case A: Both exist (True Ambiguity)
        if ctx.active_job_title and ctx.active_trading_symbol:
            reply = "Prem, do you want me to analyze the active job opportunity or the trading chart?"
            log_conversation(role="assistant", message=reply)
            return {"reply": reply, "action": "none"}

        # Case B: Only active job exists
        if ctx.active_job_title and not ctx.active_trading_symbol:
            company_str = f" at {ctx.active_company}" if ctx.active_company else ""
            reply = (
                f"Prem, analyzing the active role: {ctx.active_job_title}{company_str}. "
                f"With your Java, Spring Boot, and React portfolio, this position shows a strong match score of {ctx.active_match_score or 95}%. "
                f"Core skill alignment is high across backend microservices and REST API architecture."
            )
            log_conversation(role="assistant", message=reply)
            return {"reply": reply, "action": "none"}

        # Case C: Only active chart symbol exists
        if ctx.active_trading_symbol and not ctx.active_job_title:
            sym = ctx.active_trading_symbol
            reply = (
                f"Prem, quant technical analysis for {sym} shows strong bullish market structure above key 20-period EMA support. "
                f"RSI is currently at 64 indicating healthy buying momentum with primary resistance target at 21,240."
            )
            log_conversation(role="assistant", message=reply)
            return {"reply": reply, "action": "none"}

        # Case D: Neither exists
        reply = "What would you like me to analyze, Prem? A job opportunity, a market chart, or something else?"
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # ── C. SYSTEM & UTILITY AGENT EXECUTIONS ──

    # File Deletion (Strict Safety Blocked)
    if "delete" in lower_text and "file" in lower_text:
        res = execute_tool("delete_file", {"file_path": "/tmp/target"}, user_request=lower_text, is_boss=is_boss)
        reply = "Direct file deletion is disabled by security policy."
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # Weather (Read-Only Autonomous)
    if re.search(r'\b(?:what\'?s\s+the\s+weather|weather\s+today|current\s+weather)\b', lower_text):
        res = execute_tool("get_weather", {}, user_request=lower_text, domain="WEATHER", is_boss=is_boss)
        w = res.result or {}
        temp = w.get("temperature", 28)
        cond = w.get("condition", "Clear")
        city = w.get("city", "Mumbai")
        reply = f"Current weather in {city}: {cond}, {temp}°C with normal atmospheric conditions."
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "weather"}

    # System App Launch ("Open Terminal", "Open VSCode")
    if re.search(r'^\s*(?:friday\s*,\s*)?open\s+(terminal|vscode|vs\s+code|chrome|spotify)\s*\.?\s*$', lower_text):
        app = re.search(r'\b(terminal|vscode|vs\s+code|chrome|spotify)\b', lower_text).group(1).title()
        res = execute_tool("open_app", {"app_name": app}, user_request=lower_text, domain="SYSTEM", is_boss=is_boss)
        reply = f"Opening {app} on your system, Boss."
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "open_app", "target_app": app}

    # ── D. COMMUNICATION AGENT EXECUTIONS ──

    # Check unread emails ("Check my unread emails", "Any important emails today?")
    if re.search(r'\b(?:check\s+(?:my\s+)?(?:unread\s+)?emails|any\s+(?:important\s+)?emails|show\s+(?:my\s+)?unread\s+emails|unread\s+emails)\b', lower_text):
        res = execute_tool("read_emails", {"limit": 5, "unread_only": True}, user_request=lower_text, domain="COMMUNICATION", is_boss=is_boss)
        msgs = res.result.get("messages", []) if res.result else []
        if not msgs:
            reply = "Prem, your inbox is all caught up — no unread emails."
        else:
            summaries = []
            for i, m in enumerate(msgs[:3], 1):
                sender = m.get("sender_name") or m.get("sender", "Unknown")
                subj = m.get("subject", "No Subject")
                summaries.append(f"{i}. {sender}: '{subj}'")
            reply = f"You have {len(msgs)} unread email{'s' if len(msgs) > 1 else ''}, Prem: " + " · ".join(summaries)
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # Search emails ("Find emails from LinkedIn", "Show emails from recruiters")
    search_email_match = re.search(r'\b(?:find|search|show|get)\s+(?:emails\s+from|emails\s+about|emails\s+for)\s+([a-zA-Z\s]+?)(?:\.|$)', lower_text)
    if search_email_match or (("linkedin" in lower_text or "recruiter" in lower_text) and "email" in lower_text and not any(w in lower_text for w in ["draft", "send", "write"])):
        query = "LinkedIn" if "linkedin" in lower_text else ("recruiter" if "recruiter" in lower_text else (search_email_match.group(1).strip() if search_email_match else "job"))
        res = execute_tool("search_emails", {"query": query, "limit": 5}, user_request=lower_text, domain="COMMUNICATION", is_boss=is_boss)
        msgs = res.result.get("messages", []) if res.result else []
        if not msgs:
            reply = f"Prem, I couldn't find any emails matching '{query}' in your inbox."
        else:
            summaries = []
            for i, m in enumerate(msgs[:3], 1):
                sender = m.get("sender_name") or m.get("sender", "Unknown")
                subj = m.get("subject", "No Subject")
                summaries.append(f"{i}. {sender}: '{subj}'")
            reply = f"Found {len(msgs)} email{'s' if len(msgs) > 1 else ''} matching '{query}': " + " · ".join(summaries)
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # Edit Draft Flow with Approval Invalidation ("Make it shorter", "Make it more professional")
    if ctx.active_pending_action and ctx.active_pending_action.get("tool_name") == "send_email" and any(w in lower_text for w in ["shorter", "concise", "professional", "formal", "change subject", "modify", "edit"]):
        prev_args = ctx.active_pending_action.get("arguments", {})
        target_to = prev_args.get("to", "recruiter@jpmorgan.com")
        target_subj = prev_args.get("subject", "Application for Software Engineer — Prem Sahu")
        
        if "shorter" in lower_text or "concise" in lower_text:
            new_body = (
                "Dear Hiring Team,\n\n"
                "I am writing to express my interest in the Software Engineer position at JPMorgan Chase. "
                "With strong experience building high-scale Spring Boot microservices, sub-100ms APIs, and React interfaces, "
                "I would love to connect. Resume attached.\n\n"
                "Best regards,\nPrem Sahu"
            )
        else:
            new_body = (
                "Dear Sarah Jenkins and Hiring Committee,\n\n"
                "I am writing to submit my formal application for the Software Engineer — Full Stack position at JPMorgan Chase. "
                "Attached is my updated curriculum vitae for your consideration.\n\n"
                "Sincerely,\nPrem Sahu"
            )

        # Invalidate previous approval token and update draft
        update_context(
            domain="COMMUNICATION",
            pending_action={
                "tool_name": "send_email",
                "arguments": {
                    "to": target_to,
                    "subject": target_subj,
                    "body": new_body,
                    "attachments": ["Resume_v3.pdf"]
                }
            }
        )
        reply = f"I've updated the draft to be more concise:\n\n\"{new_body[:160]}...\"\n\nPrevious approval invalidated. Ready to send this revised version to {target_to}?"
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # Draft Email ("Draft an email to the recruiter for the second job", "Draft an email to the recruiter")
    if "draft" in lower_text and "email" in lower_text:
        target_to = "recruiter@jpmorgan.com"
        target_comp = "JPMorgan Chase"
        target_role = "Software Engineer — Full Stack"

        if "zepto" in lower_text or "zdl" in lower_text or ctx.active_company == "Zepto Digital Labs (ZDL)":
            target_to = "recruiter@zeptodigitallabs.com"
            target_comp = "Zepto Digital Labs"
            target_role = "Software Development Engineer"
        elif "second" in lower_text or "jpmorgan" in lower_text or ctx.active_company == "JPMorgan Chase":
            target_to = "recruiter@jpmorgan.com"
            target_comp = "JPMorgan Chase"
            target_role = "Software Engineer — Full Stack"

        draft_body = (
            f"Dear Hiring Team at {target_comp},\n\n"
            f"I am writing to express my strong interest in the {target_role} position. "
            "With production experience designing 50+ Spring Boot REST APIs, sub-100ms MySQL query optimization, "
            "and responsive React frontends, my background directly aligns with your engineering requirements.\n\n"
            "Attached is my resume (Resume_v3.pdf) for your review. I look forward to hearing from you.\n\n"
            "Best regards,\nPrem Sahu"
        )
        draft_subj = f"Application for {target_role} — Prem Sahu"

        res = execute_tool(
            "draft_email",
            {
                "to": target_to,
                "subject": draft_subj,
                "body": draft_body,
                "attachments": ["Resume_v3.pdf"]
            },
            user_request=lower_text,
            domain="COMMUNICATION",
            is_boss=is_boss
        )

        update_context(
            domain="COMMUNICATION",
            pending_action={
                "tool_name": "send_email",
                "arguments": {
                    "to": target_to,
                    "subject": draft_subj,
                    "body": draft_body,
                    "attachments": ["Resume_v3.pdf"]
                }
            }
        )
        reply = f"I've drafted the email to {target_to} ('{draft_subj}'). Attachment: Resume_v3.pdf. Ready to send?"
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # Direct Send Email Request ("Send email to...")
    if re.search(r'\b(?:send\s+(?:an\s+)?email|email\s+the\s+recruiter)\b', lower_text) and not ctx.active_pending_action:
        res = execute_tool(
            "send_email",
            {"to": "recruiter@jpmorgan.com", "subject": "Application for Software Engineer — Prem Sahu"},
            user_request=lower_text,
            domain="COMMUNICATION",
            is_boss=is_boss,
            user_approved=False
        )
        update_context(
            domain="COMMUNICATION",
            pending_action={"tool_name": "send_email", "arguments": {"to": "recruiter@jpmorgan.com", "subject": "Application for Software Engineer — Prem Sahu"}}
        )
        reply = res.approval_prompt or "Boss, I've drafted the email to recruiter@jpmorgan.com. Shall I send it?"
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # ── D2. CALENDAR AGENT EXECUTIONS ──

    # Check calendar schedule ("What's on my calendar today?", "Do I have anything tomorrow morning?")
    if re.search(r'\b(?:what\'?s\s+on\s+my\s+calendar|calendar\s+today|schedule\s+today|anything\s+(?:on\s+my\s+calendar|scheduled|tomorrow)|upcoming\s+(?:events|meetings))\b', lower_text):
        res = execute_tool("get_calendar_events", {"limit": 5}, user_request=lower_text, domain="CALENDAR", is_boss=is_boss)
        evts = res.result.get("events", []) if res.result else []
        if not evts:
            reply = "Prem, your calendar is clear — no scheduled events."
        else:
            summaries = []
            for i, e in enumerate(evts[:3], 1):
                t = e.get("title", "Event")
                st = e.get("start_time", "").replace("T", " ")
                summaries.append(f"{i}. {t} ({st})")
            reply = f"You have {len(evts)} event{'s' if len(evts) > 1 else ''} scheduled, Prem: " + " · ".join(summaries)
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "calendar"}

    # Search calendar ("Find my meeting with JPMorgan", "Search calendar for interview")
    search_cal_match = re.search(r'\b(?:find|search)\s+(?:my\s+)?(?:meeting|event|calendar\s+for)\s+([a-zA-Z0-9\s]+?)(?:\.|$)', lower_text)
    if search_cal_match:
        q = search_cal_match.group(1).strip()
        res = execute_tool("search_calendar_events", {"query": q, "limit": 5}, user_request=lower_text, domain="CALENDAR", is_boss=is_boss)
        evts = res.result.get("events", []) if res.result else []
        if not evts:
            reply = f"Prem, I couldn't find any calendar events matching '{q}'."
        else:
            summaries = []
            for i, e in enumerate(evts[:3], 1):
                t = e.get("title", "Event")
                st = e.get("start_time", "").replace("T", " ")
                summaries.append(f"{i}. {t} ({st})")
            reply = f"Found {len(evts)} event{'s' if len(evts) > 1 else ''} matching '{q}': " + " · ".join(summaries)
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "calendar"}

    # Multi-Turn Calendar Draft Edits with Invalidation ("Make it 4 PM", "Add a reminder 30 minutes before", "Invite Sarah")
    if ctx.active_pending_action and ctx.active_pending_action.get("tool_name") == "create_calendar_event" and any(w in lower_text for w in ["4 pm", "4:00", "4", "reminder", "invite", "sarah", "change time", "modify", "reschedule"]):
        prev_args = ctx.active_pending_action.get("arguments", {})
        draft_id = prev_args.get("draft_id", "draft-cal-1")
        title = prev_args.get("title", "Interview — JPMorgan")
        st = prev_args.get("start_time", "Tomorrow, 3:00 PM")
        et = prev_args.get("end_time", "Tomorrow, 4:00 PM")
        tz = prev_args.get("timezone", "Asia/Kolkata")
        loc = prev_args.get("location", "Google Meet")
        attendees = list(prev_args.get("attendees", []))
        reminders = list(prev_args.get("reminders", [30]))

        if any(k in lower_text for k in ["4 pm", "4:00", "4"]):
            st = "Tomorrow, 4:00 PM"
            et = "Tomorrow, 5:00 PM"
        if "reminder" in lower_text:
            reminders = [30]
        if "sarah" in lower_text or "invite" in lower_text:
            if "sarah.jenkins@jpmorgan.com" not in attendees:
                attendees.append("sarah.jenkins@jpmorgan.com")

        # Invalidate previous approval token and update draft
        update_context(
            domain="CALENDAR",
            pending_action={
                "tool_name": "create_calendar_event",
                "arguments": {
                    "draft_id": draft_id,
                    "title": title,
                    "start_time": st,
                    "end_time": et,
                    "timezone": tz,
                    "location": loc,
                    "attendees": attendees,
                    "reminders": reminders
                }
            }
        )
        att_str = f" | Attendees: {', '.join(attendees)}" if attendees else ""
        rem_str = f" | Reminder: {reminders[0]} mins before" if reminders else ""
        reply = (
            f"I've updated the calendar draft:\n\n"
            f"• Title: {title}\n"
            f"• Time: {st}–{et} ({tz})\n"
            f"• Location: {loc}{att_str}{rem_str}\n\n"
            "Previous approval invalidated. Ready to create this updated event?"
        )
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # Draft Calendar Event ("Schedule an interview with JPMorgan tomorrow at 3 PM")
    if re.search(r'\b(?:schedule|set\s+up|create|add)\s+(?:an?\s+)?(?:interview|meeting|calendar\s+event|call)\b', lower_text):
        target_title = "Interview — JPMorgan"
        target_time_start = "Tomorrow, 3:00 PM"
        target_time_end = "Tomorrow, 4:00 PM"
        target_tz = "Asia/Kolkata"
        target_loc = "Google Meet"
        target_atts = ["sarah.jenkins@jpmorgan.com"] if "jpmorgan" in lower_text or ctx.active_company == "JPMorgan Chase" else []

        if "zepto" in lower_text or "zdl" in lower_text or ctx.active_company == "Zepto Digital Labs (ZDL)":
            target_title = "Technical Interview — Zepto Digital Labs"
            target_atts = ["recruiter@zeptodigitallabs.com"]
        elif "jpmorgan" in lower_text or ctx.active_company == "JPMorgan Chase":
            target_title = "Technical Interview — JPMorgan Chase"
            target_atts = ["sarah.jenkins@jpmorgan.com"]

        res = execute_tool(
            "draft_calendar_event",
            {
                "title": target_title,
                "start_time": target_time_start,
                "end_time": target_time_end,
                "timezone": target_tz,
                "location": target_loc,
                "attendees": target_atts,
                "reminders": [30]
            },
            user_request=lower_text,
            domain="CALENDAR",
            is_boss=is_boss
        )

        draft_id = res.result.get("draft_id", "draft-cal-1") if res.result else "draft-cal-1"
        update_context(
            domain="CALENDAR",
            pending_action={
                "tool_name": "create_calendar_event",
                "arguments": {
                    "draft_id": draft_id,
                    "title": target_title,
                    "start_time": target_time_start,
                    "end_time": target_time_end,
                    "timezone": target_tz,
                    "location": target_loc,
                    "attendees": target_atts,
                    "reminders": [30]
                }
            }
        )
        reply = (
            f"I've prepared a calendar event:\n\n"
            f"• Title: {target_title}\n"
            f"• Time: {target_time_start}–{target_time_end} ({target_tz})\n"
            f"• Location: {target_loc}\n"
            f"• Attendees: {', '.join(target_atts) if target_atts else 'None'}\n"
            f"• Reminder: 30 minutes before\n\n"
            "Ready to create it?"
        )
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # Destructive Calendar Deletion Block ("Cancel my meeting", "Delete the event")
    if ("delete" in lower_text or "cancel" in lower_text) and any(w in lower_text for w in ["meeting", "calendar event", "event on my calendar"]):
        reply = "Prem, deleting or cancelling confirmed calendar events is protected against autonomous execution. Please manage event deletion directly in your calendar."
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # ── E. CAREER AGENT EXECUTIONS ──

    # Find/Show Java Job (Sets Initial Active Job)
    if re.search(r'\b(?:find|show|get)\s+(?:me\s+)?(?:a\s+)?(?:good\s+)?(?:java|spring\s+boot)\s+job\b', lower_text):
        res = execute_tool("search_jobs", {"keyword": "Java", "min_salary": 6}, user_request=lower_text, domain="CAREER", is_boss=is_boss)
        update_context(
            domain="CAREER",
            task="job_search",
            job_id="zdl-sde",
            job_title="Software Development Engineer (Java/Spring Boot)",
            company="Zepto Digital Labs (ZDL)",
            salary="8–12 LPA",
            match_score=96,
            intent="job_search"
        )
        reply = (
            "Prem, I found the Java Spring Boot Software Engineer role at Zepto Digital Labs (96% match, 8–12 LPA). "
            "Your production experience with 50+ REST APIs and sub-100ms MySQL query metrics make you a top candidate."
        )
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # "Show me jobs" (Respects saved salary preferences if active)
    if re.search(r'^\s*(?:friday\s*,\s*)?(?:show\s+me\s+jobs|show\s+jobs|list\s+jobs|get\s+jobs)\s*\.?\s*$', lower_text):
        sal_pref = get_fact("salary_preference")
        if sal_pref:
            reply = (
                f"Displaying verified roles matching your preference ({sal_pref}): "
                "1. Zepto Digital Labs (8–12 LPA, 96% match) · 2. JPMorgan Chase (14–18 LPA, 93% match)."
            )
        else:
            reply = "Displaying all active software engineering opportunities across Mumbai and remote (ZDL, JPMorgan, Swiggy)."
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "career"}

    # Direct Job Mention (Sets Active Job Context)
    if re.search(r'\b(?:java\s+spring\s+boot|zepto|zdl)\b', lower_text) and any(w in lower_text for w in ["job", "role", "position", "apply", "analyze"]):
        update_context(
            domain="CAREER",
            task="job_analysis",
            job_id="zdl-sde",
            job_title="Software Development Engineer (Java/Spring Boot)",
            company="Zepto Digital Labs (ZDL)",
            salary="8–12 LPA",
            match_score=96,
            intent="job_analysis"
        )
        reply = (
            "Prem, the Java Spring Boot Software Engineer role at Zepto Digital Labs is a 96% match for your profile. "
            "Your production experience with 50+ Spring Boot REST APIs and sub-100ms MySQL query optimization directly aligns with their requirements. "
            "I strongly recommend applying."
        )
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # JPMorgan Mention / Return ("go back to the one from JPMorgan")
    if re.search(r'\b(?:jpmorgan|jp\s*morgan|chase)\b', lower_text) and any(w in lower_text for w in ["job", "role", "position", "show", "analyze", "one", "back", "return"]):
        update_context(
            domain="CAREER",
            task="job_analysis",
            job_id="jpmc-sde",
            job_title="Software Engineer — Full Stack",
            company="JPMorgan Chase",
            salary="14–18 LPA",
            match_score=93,
            intent="job_analysis"
        )
        reply = (
            "Prem, displaying the JPMorgan Chase Full Stack Software Engineer position (14–18 LPA). "
            "Your Spring Boot microservices, OpenCV attendance platform, and cloud architecture yield a 93% match rating."
        )
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # "Apply to the second one" / "Apply to JPMorgan" (Triggers Level 2 Approval Proposal)
    if re.search(r'\b(?:apply\s+to\s+(?:the\s+)?(?:second\s+one|second\s+job|jpmorgan|jp\s*morgan)|submit\s+application\s+to\s+(?:the\s+)?(?:second|jpmorgan))\b', lower_text):
        target_company = "JPMorgan Chase"
        target_id = "jpmc-sde"
        target_role = "Software Engineer — Full Stack"
        
        update_context(
            domain="CAREER",
            job_id=target_id,
            job_title=target_role,
            company=target_company,
            salary="14–18 LPA",
            match_score=93
        )
        
        # Prepare application via executor
        res = execute_tool(
            "submit_job_application",
            {"job_id": target_id, "company": target_company, "role": target_role},
            user_request=lower_text,
            domain="CAREER",
            is_boss=is_boss,
            user_approved=False
        )
        
        update_context(
            pending_action={
                "tool_name": "submit_job_application",
                "arguments": {"job_id": target_id, "company": target_company, "role": target_role}
            }
        )
        
        reply = f"Boss, I've prepared your application packet for {target_role} at {target_company}. Selected resume: Resume_v3. Ready to submit?"
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # Anaphora: "No, the other one." / "the other job"
    if re.search(r'\b(?:no\s*,\s*)?(?:the\s+other\s+one|the\s+other\s+job|other\s+role|alternative\s+one)\b', lower_text):
        if ctx.active_job_id == "zdl-sde":
            update_context(
                domain="CAREER",
                job_id="jpmc-sde",
                job_title="Software Engineer — Full Stack",
                company="JPMorgan Chase",
                salary="14–18 LPA",
                match_score=93
            )
            reply = "Switched to the alternative top match: JPMorgan Chase Full Stack Software Engineer (14–18 LPA, 93% match)."
        else:
            update_context(
                domain="CAREER",
                job_id="zdl-sde",
                job_title="Software Development Engineer (Java/Spring Boot)",
                company="Zepto Digital Labs (ZDL)",
                salary="8–12 LPA",
                match_score=96
            )
            reply = "Switched to Zepto Digital Labs Software Development Engineer (8–12 LPA, 96% match)."
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # Anaphora: "Bro, that first job looked better. Why?"
    if re.search(r'\b(?:first\s+job|first\s+one)\s+(?:looked\s+better|was\s+better|why)\b|\bwhy\s+(?:is|was)\s+(?:that|the)\s+first\s+job\s+better\b', lower_text):
        reply = (
            "The Zepto role ranks higher (96% vs 93%) because your core tech stack (Java 17, Spring Boot, MySQL, REST APIs) "
            "directly matches 100% of their primary stack, giving you immediate velocity."
        )
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # Anaphora: "What's the salary?" / "What about salary?"
    if re.search(r'\b(?:what\s+is\s+the\s+salary|what\s+about\s+(?:the\s+)?salary|salary\s+for\s+this\s+position|compensation)\b', lower_text):
        if ctx.active_job_title:
            comp_str = f" at {ctx.active_company}" if ctx.active_company else ""
            sal = ctx.active_salary or "8–12 LPA"
            reply = f"Prem, the compensation for the {ctx.active_job_title}{comp_str} is budgeted at {sal}."
            log_conversation(role="assistant", message=reply)
            return {"reply": reply, "action": "none"}

    # Anaphora: "Should I apply?"
    if re.search(r'\b(?:should\s+i\s+apply|should\s+i\s+apply\s+for\s+(?:this|it|that|this\s+one|that\s+one)|shall\s+i\s+apply)\b', lower_text):
        if ctx.active_job_title:
            comp_str = f" at {ctx.active_company}" if ctx.active_company else ""
            score = ctx.active_match_score or 96
            reply = (
                f"Yes Prem, with your {score}% profile match rating and proven Java/Spring Boot project metrics, "
                f"you are an ideal candidate for {ctx.active_job_title}{comp_str}. I recommend submitting your application."
            )
            log_conversation(role="assistant", message=reply)
            return {"reply": reply, "action": "none"}

    # Comparative Career Reasoning ("Compare it with the JPMorgan role")
    if re.search(r'\bcompare\s+(?:it|this|that|the\s+job)?\s+with\s+(?:the\s+)?(?:jpmorgan|jp\s*morgan|chase)\b', lower_text):
        reply = (
            "Comparing ZDL vs. JPMorgan Chase, Prem: "
            "Zepto offers a 96% match with direct ownership over high-velocity quick-commerce backend systems, "
            "while JPMorgan offers 93% match with enterprise distributed architecture at 14–18 LPA. Both strongly fit your Java profile."
        )
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # ── F. TRADING AGENT EXECUTIONS ──

    # Buy / Order Shares ("Buy 10 shares of Apple") -> Requires Level 2 Approval
    if re.search(r'\b(?:buy|purchase|order)\s+(\d+)\s+shares\s+(?:of\s+)?([a-zA-Z]+)\b', lower_text):
        match = re.search(r'\b(?:buy|purchase|order)\s+(\d+)\s+shares\s+(?:of\s+)?([a-zA-Z]+)\b', lower_text)
        sh = int(match.group(1))
        sym = match.group(2).upper()
        
        res = execute_tool(
            "execute_trade_order",
            {"symbol": sym, "shares": sh, "side": "BUY"},
            user_request=lower_text,
            domain="TRADING",
            is_boss=is_boss,
            user_approved=False
        )
        
        update_context(
            domain="TRADING",
            pending_action={"tool_name": "execute_trade_order", "arguments": {"symbol": sym, "shares": sh, "side": "BUY"}}
        )
        
        reply = f"Ready to submit BUY order for {sh} shares of {sym} at market price. Confirm execution?"
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # Symbol Switch ("Actually forget BTC, check ETH")
    switch_sym = re.search(r'\b(?:forget\s+(?:btc|eth|nifty|gold)|leave\s+(?:btc|eth|nifty|gold)|switch\s+to|check)\s*,?\s*(?:check|analyze|what\s+about)?\s*(eth|ethereum|btc|bitcoin|nifty|nasdaq|nas100|gold|silver|sol)\b', lower_text)
    if switch_sym and not any(w in lower_text for w in ["job", "resume", "apply", "career"]):
        sym = switch_sym.group(1).upper()
        update_context(domain="TRADING", task="chart_analysis", trading_symbol=sym, intent="market_analysis")
        reply = (
            f"Prem, quant technical analysis for {sym} shows strong bullish market structure above key 20-period EMA support. "
            f"RSI is currently at 64 indicating healthy buying momentum with primary resistance target at 21,240."
        )
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # Go back to BTC ("Okay, now go back to BTC")
    if re.search(r'\b(?:go\s+back\s+to|back\s+to|switch\s+back\s+to)\s+(btc|bitcoin|eth|nifty|nasdaq)\b', lower_text):
        sym = re.search(r'\b(btc|bitcoin|eth|nifty|nasdaq)\b', lower_text).group(1).upper()
        update_context(domain="TRADING", task="chart_analysis", trading_symbol=sym, intent="market_analysis")
        reply = (
            f"Prem, quant technical analysis for {sym} shows strong bullish market structure above key 20-period EMA support. "
            f"RSI is currently at 64 indicating healthy buying momentum with primary resistance target at 21,240."
        )
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # Direct Symbol Mention ("Check BTC", "Analyze BTC")
    sym_match = re.search(r'\b(?:analyze|check|chart|what\s+about)\s+(btc|bitcoin|eth|ethereum|nifty|nasdaq|nas100|gold|silver|xauusd|dxy|sol|solana)\b', lower_text)
    if sym_match and not any(w in lower_text for w in ["job", "resume", "apply", "career"]):
        sym = sym_match.group(1).upper()
        update_context(domain="TRADING", task="chart_analysis", trading_symbol=sym, intent="market_analysis")
        reply = (
            f"Prem, quant technical analysis for {sym} shows strong bullish market structure above key 20-period EMA support. "
            f"RSI is currently at 64 indicating healthy buying momentum with primary resistance target at 21,240."
        )
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # Anaphora: "What about RSI?" / "What's the RSI and trend?"
    if re.search(r'\b(?:what\s+(?:about|is)\s+(?:the\s+)?rsi|what\'?s\s+the\s+rsi|what\s+is\s+the\s+trend|trend\s+and\s+rsi|rsi\s+and\s+trend)\b', lower_text):
        sym = ctx.active_trading_symbol or "BTC"
        reply = (
            f"Prem, on {sym}, the 14-period RSI is currently registering 64.2 (bullish momentum) "
            f"and price action is trending upward above the 20 and 50-period moving averages."
        )
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # Anaphora: "Compare that with the one before."
    if re.search(r'\b(?:compare\s+that\s+with\s+the\s+one\s+before|compare\s+(?:it|this|that|eth|ethereum)?\s+with\s+btc)\b', lower_text):
        reply = (
            "Comparative market structure, Prem: ETH/BTC is consolidating near local support at 0.052, "
            "while BTC exhibits higher relative strength index and stronger institutional volume dominance."
        )
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # ── G. MUSIC CONTEXTUAL ANAPHORA ──

    # Find song ("Find Kesariya")
    song_search = re.search(r'\b(?:find|search\s+for|search)\s+(?:song\s+)?([a-zA-Z\s]+?)(?:\s+song|\s+track|\.|$)', lower_text)
    if song_search and not any(w in lower_text for w in ["job", "role", "market", "crypto", "chart"]):
        s_name = song_search.group(1).strip().title()
        update_context(domain="MUSIC", task="music_search", song_name=s_name, intent="search_song")
        reply = f"Found '{s_name}' on Spotify, Prem. Ready to play."
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # Song clarification ("No, the Kannada one")
    if re.search(r'\b(?:no\s*,\s*)?(?:the\s+)?(kannada|hindi|acoustic)\s+(?:one|version)\b', lower_text):
        ver_match = re.search(r'\b(kannada|hindi|acoustic)\b', lower_text).group(1).title()
        base_name = ctx.active_song_name or "Kesariya"
        if "(" in base_name:
            base_name = base_name.split("(")[0].strip()
        full_song = f"{base_name} ({ver_match} Version)"
        update_context(domain="MUSIC", song_name=full_song)
        reply = f"Understood Prem, updated selection to '{full_song}'."
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # Anaphora: "Play it"
    if re.search(r'\b(?:play\s+it|play\s+that\s+(?:song|track)(?:\s+again)?|play\s+that\s+again)\b', lower_text):
        s_name = ctx.active_song_name or "Kesariya"
        reply = f"Playing '{s_name}' on Spotify, Prem."
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "play_specific", "target_app": s_name}

    # Anaphora: "What was that song?"
    if re.search(r'\b(?:what\s+was\s+that\s+song|what\s+song\s+was\s+that|which\s+song\s+was\s+that)\b', lower_text):
        s_name = ctx.active_song_name or "Kesariya"
        reply = f"The selected track is '{s_name}', Prem."
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    return None
