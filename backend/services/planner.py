"""
planner.py — Multi-step autonomous planning engine for F.R.I.D.A.Y.
Decomposes complex user requests into structured, executable action plans.
"""

from typing import List, Dict, Any
import json
import logging

logger = logging.getLogger("friday_planner")

class PlanStep:
    def __init__(self, step_id: int, action: str, params: Dict[str, Any], description: str):
        self.step_id = step_id
        self.action = action
        self.params = params
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "action": self.action,
            "params": self.params,
            "description": self.description
        }

def generate_plan(prompt: str) -> List[Dict[str, Any]]:
    """
    Analyzes a multi-step user goal and returns a structured plan.
    Supported action types: 'career', 'trading', 'system', 'todo', 'weather', 'search', 'notify'.
    """
    lower = prompt.lower()
    plan = []

    # Complex Intent: Interview Prep
    if "interview" in lower and ("prep" in lower or "prepare" in lower):
        plan.append(PlanStep(1, "career", {"sub_action": "get_resume"}, "Retrieving active resume profile").to_dict())
        plan.append(PlanStep(2, "career", {"sub_action": "generate_questions"}, "Generating AI interview preparation questions").to_dict())
        plan.append(PlanStep(3, "todo", {"task": "Review interview questions", "priority": "high"}, "Adding interview review task to Todo list").to_dict())
        plan.append(PlanStep(4, "notify", {"message": "Interview prep session ready, Boss."}, "Summarizing readiness").to_dict())

    # Complex Intent: Morning Briefing
    elif "briefing" in lower or "morning" in lower:
        plan.append(PlanStep(1, "weather", {}, "Checking live local weather").to_dict())
        plan.append(PlanStep(2, "system", {}, "Auditing hardware telemetry").to_dict())
        plan.append(PlanStep(3, "career", {"sub_action": "briefing"}, "Generating daily Career OS opportunity briefing").to_dict())
        plan.append(PlanStep(4, "notify", {"message": "Morning briefing compiled, Boss."}, "Delivering morning summary").to_dict())

    # Single-Step Fallback
    else:
        plan.append(PlanStep(1, "chat", {"query": prompt}, "Direct AI response").to_dict())

    return plan
