"""agents.py — Multi-Agent framework (v3.1).

FRIDAY routes requests to specialised agents (career, coding, research,
finance, communication, automation) which run the same function-calling
brain but with a filtered tool set — each agent can only call the functions
in its capability list. Agent autonomy is gated by the `agent.autonomy`
permission (default: ask).

Routing today is keyword-based (deterministic, testable, zero-latency); the
LLM-tool path inside brain_v2 does the actual work once an agent is chosen.
"""

import logging

from services import function_engine

# agent_key -> {name, blurb, capabilities (function names), keywords}
AGENTS = {
    "career": {
        "name": "Career Agent",
        "blurb": "Resumes, jobs, interviews, applications, recruiters.",
        "capabilities": ["get_time", "get_todos", "add_todo", "set_reminder",
                         "search_web", "navigate_to", "technical_analysis"],
        "keywords": ["job", "resume", "interview", "salary", "career", "recruiter",
                     "application", "cover letter", "linkedin", "naukri",
                     "offer", "hir", "vacancy", "candidate", "role"],
    },
    "coding": {
        "name": "Coding Agent",
        "blurb": "Code, bugs, debugging, GitHub, VS Code, terminals.",
        "capabilities": ["open_app", "get_time", "search_web", "take_screenshot",
                         "add_todo", "set_reminder"],
        "keywords": ["code", "bug", "debug", "github", "vscode", "terminal",
                     "compile", "error", "function", "python", "java", "react",
                     "refactor", "test"],
    },
    "research": {
        "name": "Research Agent",
        "blurb": "Web research, explanations, comparisons, summaries.",
        "capabilities": ["search_web", "get_time", "get_weather", "add_todo",
                         "navigate_to"],
        "keywords": ["research", "explain", "compare", "summar", "what is",
                     "how does", "paper", "document", "learn", "tell me about"],
    },
    "finance": {
        "name": "Finance Agent",
        "blurb": "Markets, technical analysis, watchlists, crypto, trading.",
        "capabilities": ["technical_analysis", "get_time", "search_web",
                         "get_todos", "add_todo", "set_reminder", "navigate_to"],
        "keywords": ["market", "trade", "stock", "crypto", "gold", "forex",
                     "analysis", "trend", "chart", "invest", "price", "nifty",
                     "sensex", "bitcoin", "rsi", "support", "resistance"],
    },
    "communication": {
        "name": "Communication Agent",
        "blurb": "Email, messages, calendar, reminders, notifications.",
        "capabilities": ["get_time", "get_weather", "get_todos", "add_todo",
                         "set_reminder", "search_web", "check_email",
                         "search_email", "send_email"],
        "keywords": ["email", "message", "whatsapp", "call", "calendar",
                     "meeting", "remind", "notify", "send", "draft", "inbox",
                     "summar"],
    },
    "automation": {
        "name": "Automation Agent",
        "blurb": "Scheduled workflows, routines, daily briefing.",
        "capabilities": ["get_time", "get_todos", "add_todo", "set_reminder",
                         "search_web", "navigate_to"],
        "keywords": ["automate", "schedule", "routine", "every morning",
                     "every day", "daily", "workflow", "briefing", "hourly"],
    },
}


def list_agents() -> list:
    return [
        {"key": key, "name": a["name"], "blurb": a["blurb"],
         "tools": len(a["capabilities"])}
        for key, a in AGENTS.items()
    ]


def route_to_agent(text: str) -> str:
    """Deterministic keyword router. Returns the best agent key or 'career'
    as a sensible default for FRIDAY's job-hunting focus."""
    lowered = (text or "").lower()
    best_key, best_score = None, 0
    for key, agent in AGENTS.items():
        score = sum(1 for kw in agent["keywords"] if kw in lowered)
        if score > best_score:
            best_key, best_score = key, score
    if best_key is None:
        best_key = "career"  # default
    return best_key


def tools_for_agent(agent_key: str) -> list:
    """Return the LLM tool schemas filtered to one agent's capabilities."""
    caps = set(AGENTS.get(agent_key, {}).get("capabilities", []))
    return [
        t for t in function_engine.get_tools_schema()
        if t["function"]["name"] in caps
    ]


def handle_with_agent(text: str, is_boss: bool = True) -> dict:
    """Route to an agent and run brain_v2 with its filtered tool set.

    Agent autonomy is gated: if the `agent.autonomy` permission is not
    allowed, we still answer (via the agent's tools) but the reply notes that
    autonomous multi-step actions are approval-gated.
    """
    from services.brain_v2 import respond_v2
    from services.permissions import check_permission

    agent_key = route_to_agent(text)
    agent = AGENTS[agent_key]
    autonomy = check_permission("agent.autonomy")

    result = respond_v2(text, is_boss=is_boss, tools_filter=tools_for_agent(agent_key))
    result["agent"] = agent_key
    result["agent_name"] = agent["name"]
    if autonomy != "allowed":
        result["autonomy_gated"] = True
        result["reply"] = (
            f"[{agent['name']}] " + (result.get("reply") or "")
        )
    return result
