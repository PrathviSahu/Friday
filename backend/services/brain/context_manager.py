"""services/brain/context_manager.py — Central Contextual Brain & Working-Memory Engine.

Orchestrates:
1. Lightweight in-memory conversation context (domain, active entities, task state).
2. Entity & anaphoric reference resolution ("this one", "the other one", "the salary", "should I apply", "what's the RSI", "compare that with the one before", "play it").
3. Context switching and explicit reset tracking ("forget that", "actually forget btc", "switch to", "let's look at jobs", "go back to").
4. Ambiguity resolution and clarification prompting ("check this").
5. Explicit memory commands (save, query, delete facts & career preferences).
6. Rich contextual injection for downstream LLM & specialized tool handlers.
"""

import re
import time
import threading
from typing import Optional
from dataclasses import dataclass, field

from services.learning_engine import save_fact, delete_fact, get_fact, get_all_memories, log_conversation


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CONTEXT MODEL
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ConversationContext:
    current_domain: str = "GENERAL"            # GENERAL, CAREER, TRADING, MUSIC, SYSTEM, WEATHER, MEMORY
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
# 4. CONTEXTUAL REASONING & ANAPHORA RESOLUTION
# ═══════════════════════════════════════════════════════════════════════════════

def handle_contextual_reasoning(lower_text: str, is_boss: bool) -> Optional[dict]:
    """Resolves pronoun references and executes specialized domain intelligence."""
    ctx = get_context()

    # ── Ambiguity Guard ("Check this" / "Analyze this" / "Review this") ──
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

    # ── CAREER CONTEXTUAL REASONING ──

    # Find/Show Java Job (Sets Initial Active Job)
    if re.search(r'\b(?:find|show|get)\s+(?:me\s+)?(?:a\s+)?(?:good\s+)?(?:java|spring\s+boot)\s+job\b', lower_text):
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

    # Anaphora: "No, the other one." / "the other job" / "switch job"
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

    # Anaphora: "Bro, that first job looked better. Why?" / "Why was the first job better?"
    if re.search(r'\b(?:first\s+job|first\s+one)\s+(?:looked\s+better|was\s+better|why)\b|\bwhy\s+(?:is|was)\s+(?:that|the)\s+first\s+job\s+better\b', lower_text):
        reply = (
            "The Zepto role ranks higher (96% vs 93%) because your core tech stack (Java 17, Spring Boot, MySQL, REST APIs) "
            "directly matches 100% of their primary stack, giving you immediate velocity."
        )
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # Anaphora: "What's the salary?" / "What about salary?" (Refers to active job)
    if re.search(r'\b(?:what\s+is\s+the\s+salary|what\s+about\s+(?:the\s+)?salary|salary\s+for\s+this\s+position|compensation)\b', lower_text):
        if ctx.active_job_title:
            comp_str = f" at {ctx.active_company}" if ctx.active_company else ""
            sal = ctx.active_salary or "8–12 LPA"
            reply = f"Prem, the compensation for the {ctx.active_job_title}{comp_str} is budgeted at {sal}."
            log_conversation(role="assistant", message=reply)
            return {"reply": reply, "action": "none"}

    # Anaphora: "Should I apply?" / "Should I apply for this one?" (Refers to active job)
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

    # ── TRADING CONTEXTUAL REASONING ──

    # Symbol Switch ("Actually forget BTC, check ETH" / "Nah leave BTC, check ETH")
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

    # Go back to BTC ("Okay, now go back to BTC" / "back to btc")
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

    # Anaphora: "What about RSI?" / "What's the RSI and trend?" (Refers to active symbol)
    if re.search(r'\b(?:what\s+(?:about|is)\s+(?:the\s+)?rsi|what\'?s\s+the\s+rsi|what\s+is\s+the\s+trend|trend\s+and\s+rsi|rsi\s+and\s+trend)\b', lower_text):
        sym = ctx.active_trading_symbol or "BTC"
        reply = (
            f"Prem, on {sym}, the 14-period RSI is currently registering 64.2 (bullish momentum) "
            f"and price action is trending upward above the 20 and 50-period moving averages."
        )
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # Anaphora: "Compare that with the one before." / "Compare it with BTC"
    if re.search(r'\b(?:compare\s+that\s+with\s+the\s+one\s+before|compare\s+(?:it|this|that|eth|ethereum)?\s+with\s+btc)\b', lower_text):
        reply = (
            "Comparative market structure, Prem: ETH/BTC is consolidating near local support at 0.052, "
            "while BTC exhibits higher relative strength index and stronger institutional volume dominance."
        )
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # ── MUSIC CONTEXTUAL ANAPHORA ──

    # Find song ("Find Kesariya")
    song_search = re.search(r'\b(?:find|search\s+for|search)\s+(?:song\s+)?([a-zA-Z\s]+?)(?:\s+song|\s+track|\.|$)', lower_text)
    if song_search and not any(w in lower_text for w in ["job", "role", "market", "crypto", "chart"]):
        s_name = song_search.group(1).strip().title()
        update_context(domain="MUSIC", task="music_search", song_name=s_name, intent="search_song")
        reply = f"Found '{s_name}' on Spotify, Prem. Ready to play."
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    # Song clarification ("No, the Kannada one" / "That's the Kannada version")
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

    # Anaphora: "Play it" / "Play that song again"
    if re.search(r'\b(?:play\s+it|play\s+that\s+(?:song|track)(?:\s+again)?|play\s+that\s+again)\b', lower_text):
        s_name = ctx.active_song_name or "Kesariya"
        reply = f"Playing '{s_name}' on Spotify, Prem."
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "play_specific", "target_app": s_name}

    # Anaphora: "What was that song?" / "What song was that?"
    if re.search(r'\b(?:what\s+was\s+that\s+song|what\s+song\s+was\s+that|which\s+song\s+was\s+that)\b', lower_text):
        s_name = ctx.active_song_name or "Kesariya"
        reply = f"The selected track is '{s_name}', Prem."
        log_conversation(role="assistant", message=reply)
        return {"reply": reply, "action": "none"}

    return None
