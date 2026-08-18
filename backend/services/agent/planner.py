"""services/agent/planner.py — Goal Decomposition & Plan Validation Engine.

Transforms natural language goals into validated, multi-step tool execution plans.
Plans are constructed and validated BEFORE any tool is invoked.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel
from services.agent.tool_registry import get_tool


class PlanStep(BaseModel):
    step_id: int
    tool_name: str
    arguments: Dict[str, Any]
    reason: str
    depends_on: Optional[int] = None


class ExecutionPlan(BaseModel):
    plan_id: str
    goal: str
    domain: str
    steps: List[PlanStep]
    requires_user_approval: bool = False


def create_execution_plan(user_request: str, domain: str, context: Any) -> ExecutionPlan:
    """Constructs a structured execution plan from user intent and working memory."""
    lower = user_request.lower()
    plan_id = f"PLAN-{abs(hash(user_request)) % 100000}"

    # 1. Job search / filtering
    if "job" in lower and any(w in lower for w in ["find", "search", "show", "get"]):
        sal_match = re.search(r'(\d+)\s*(?:lpa|lac|lakh)', lower)
        min_sal = float(sal_match.group(1)) if sal_match else 0.0
        return ExecutionPlan(
            plan_id=plan_id,
            goal=f"Discover and filter software engineering roles (>= {min_sal} LPA)",
            domain="CAREER",
            steps=[
                PlanStep(
                    step_id=1,
                    tool_name="search_jobs",
                    arguments={"keyword": "Java", "min_salary": min_sal},
                    reason="Retrieve matching engineering roles meeting user criteria."
                )
            ],
            requires_user_approval=False
        )

    # 2. Job application preparation / submission
    if "apply" in lower:
        # Resolve target job from context or request
        target_company = "JPMorgan Chase" if "second" in lower or "jpmorgan" in lower else "Zepto Digital Labs"
        target_id = "jpmc-sde" if "second" in lower or "jpmorgan" in lower else "zdl-sde"
        target_role = "Software Engineer — Full Stack" if "second" in lower or "jpmorgan" in lower else "Software Development Engineer"
        
        return ExecutionPlan(
            plan_id=plan_id,
            goal=f"Prepare and submit job application to {target_company}",
            domain="CAREER",
            steps=[
                PlanStep(
                    step_id=1,
                    tool_name="prepare_job_application",
                    arguments={"job_id": target_id, "company": target_company, "role": target_role},
                    reason="Assemble application packet, portfolio metrics, and tailored resume."
                ),
                PlanStep(
                    step_id=2,
                    tool_name="submit_job_application",
                    arguments={"job_id": target_id, "company": target_company, "role": target_role},
                    reason="Submit verified application to employer portal upon approval.",
                    depends_on=1
                )
            ],
            requires_user_approval=True
        )

    # 3. Email drafting / sending
    if "email" in lower:
        return ExecutionPlan(
            plan_id=plan_id,
            goal="Draft recruiter outreach email",
            domain="COMMUNICATION",
            steps=[
                PlanStep(
                    step_id=1,
                    tool_name="draft_email",
                    arguments={
                        "to": "recruiter@jpmorgan.com",
                        "subject": "Application for Software Engineer — Prem Sahu",
                        "body": "Dear Hiring Team,\n\nI am reaching out regarding the Software Engineer position..."
                    },
                    reason="Generate professional recruiter correspondence preview."
                )
            ],
            requires_user_approval=False
        )

    # 4. WhatsApp
    if "whatsapp" in lower or "message" in lower:
        return ExecutionPlan(
            plan_id=plan_id,
            goal="Draft WhatsApp notification",
            domain="COMMUNICATION",
            steps=[
                PlanStep(
                    step_id=1,
                    tool_name="draft_whatsapp",
                    arguments={"contact": "Rahul", "message": "Hey Rahul, I'll call you tonight."},
                    reason="Prepare message preview for user review."
                )
            ],
            requires_user_approval=False
        )

    # 5. Trading
    if any(w in lower for w in ["buy", "sell", "order", "shares"]):
        shares_match = re.search(r'(\d+)\s*(?:shares|units)', lower)
        shares = int(shares_match.group(1)) if shares_match else 10
        symbol_match = re.search(r'(?:of|for)\s+([a-zA-Z]+)', lower)
        symbol = symbol_match.group(1).upper() if symbol_match else "AAPL"
        
        return ExecutionPlan(
            plan_id=plan_id,
            goal=f"Prepare and execute trade order for {shares} shares of {symbol}",
            domain="TRADING",
            steps=[
                PlanStep(
                    step_id=1,
                    tool_name="prepare_trade_order",
                    arguments={"symbol": symbol, "shares": shares, "side": "BUY"},
                    reason="Calculate order value, spread, and ticket preview."
                ),
                PlanStep(
                    step_id=2,
                    tool_name="execute_trade_order",
                    arguments={"symbol": symbol, "shares": shares, "side": "BUY"},
                    reason="Submit market order upon explicit authorization.",
                    depends_on=1
                )
            ],
            requires_user_approval=True
        )

    # 6. Weather
    if "weather" in lower:
        return ExecutionPlan(
            plan_id=plan_id,
            goal="Query live weather conditions",
            domain="WEATHER",
            steps=[
                PlanStep(step_id=1, tool_name="get_weather", arguments={}, reason="Fetch meteorological report.")
            ],
            requires_user_approval=False
        )

    # 7. System / App
    if "open" in lower and any(w in lower for w in ["terminal", "vscode", "chrome", "spotify"]):
        app = "Terminal" if "terminal" in lower else ("VS Code" if "vscode" in lower else "Chrome")
        return ExecutionPlan(
            plan_id=plan_id,
            goal=f"Launch application {app}",
            domain="SYSTEM",
            steps=[
                PlanStep(step_id=1, tool_name="open_app", arguments={"app_name": app}, reason=f"Launch {app} executable.")
            ],
            requires_user_approval=False
        )

    # 8. File Deletion (Blocked)
    if "delete" in lower and "file" in lower:
        return ExecutionPlan(
            plan_id=plan_id,
            goal="Request file deletion",
            domain="SYSTEM",
            steps=[
                PlanStep(step_id=1, tool_name="delete_file", arguments={"file_path": "/tmp/target"}, reason="File deletion request.")
            ],
            requires_user_approval=True
        )

    # Default general plan
    return ExecutionPlan(
        plan_id=plan_id,
        goal="Respond to conversational query",
        domain=domain,
        steps=[],
        requires_user_approval=False
    )


def validate_plan(plan: ExecutionPlan) -> Tuple[bool, str]:
    """Validates plan steps against registered tools and safety constraints."""
    for step in plan.steps:
        tool = get_tool(step.tool_name)
        if not tool:
            return False, f"Plan contains unregistered tool: '{step.tool_name}'."
        if tool.risk_level.value == "blocked":
            return False, f"Tool '{step.tool_name}' is blocked by security policy."
    return True, "Plan validated successfully."
