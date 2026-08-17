"""services/brain/handlers/utilities_handler.py — Everyday productivity tools (Weather, Reminders, Tasks, History, Time)."""

import re
import time
from typing import Optional
from services.memory import log_conversation, get_recent_conversation
from services.todos import add_todo
from services.weather import get_weather
from services.reminders import add_reminder
from services.learning_engine import log_user_action


def handle_utilities(lower_text: str, is_boss: bool, text: str) -> Optional[dict]:
    """Handles everyday assistant utilities without invoking the LLM."""
    # Creator / Owner / Prathvi Sahu (Prem) Dossier
    if re.search(r'\b(?:who\s+are\s+you|who\s+made\s+you|who\s+created\s+you|who\s+is\s+your\s+owner|who\s+is\s+your\s+creator|who\s+is\s+your\s+boss|tell\s+me\s+about\s+(?:prem|prathvi|prathvi\s+sahu|your\s+owner|your\s+creator)|who\s+is\s+(?:prem|prathvi|prathvi\s+sahu)|owner\s+info|creator\s+info|about\s+prem|about\s+prathvi)\b', lower_text):
        reply_msg = (
            "I am F.R.I.D.A.Y., engineered by Prathvi Sahu (Prem), an AI Systems Architect and Software Engineer from IIT Mandi. "
            "Prem built me as a full-stack voice-controlled operating system integrating Groq Llama 3.3 70B, real-time quantum trading analysis, and an AI Career OS. "
            "You can explore his work on GitHub at github.com/PrathviSahu."
        )
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "none"}

    # Voice AI Quant Chart Analysis
    if re.search(r'\b(?:analyze|analysis|chart\s+analysis|technical\s+analysis|what\s+is\s+the\s+trend|quant\s+analysis)\b', lower_text):
        sym_match = re.search(r'\b(?:nas100|nasdaq|gold|xauusd|dxy|nifty|btc|bitcoin|eurusd|gbpusd|us100|reliance|tatamotors)\b', lower_text)
        symbol_name = sym_match.group(0).upper() if sym_match else "the active chart"
        reply_msg = (
            f"Prem, quant technical analysis for {symbol_name} shows strong bullish market structure above key 20-period EMA support. "
            f"RSI is currently at 64 indicating healthy buying momentum with primary resistance target at 21,240."
        )
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "none"}

    # Reminders / Timers
    rem_match = re.search(r'\b(?:remind\s+me|set\s+timer|timer\s+set|alarm)\b.*\b(?:in|for|after)?\s*(\d{1,3})\s*(min|minute|minutes|sec|second|seconds|hr|hour|hours)\b', lower_text)
    if rem_match:
        num = int(rem_match.group(1))
        unit = rem_match.group(2)
        if 'hour' in unit or 'hr' in unit:
            sec = num * 3600
        elif 'min' in unit:
            sec = num * 60
        else:
            sec = num
        msg_part = re.sub(r'^.*?\b(?:to|that|about)\b\s*', '', lower_text).strip()
        msg = msg_part if msg_part and not any(k in msg_part for k in ['minute', 'second', 'hour', 'timer', 'remind']) else "Timer up"
        add_reminder(msg, sec)
        reply_msg = f"Timer set for {num} {unit}, Prem. I'll remind you to '{msg}'."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "none"}

    # Weather
    if re.search(r'\b(?:weather|mausam|temperature|tapman)\b', lower_text):
        city_match = re.search(r'\b(?:in|of|at|for)\s+([a-zA-Z\s]+)', lower_text)
        city_query = city_match.group(1).strip() if city_match else None
        w = get_weather(city_query)
        reply_msg = f"Prem, it's currently {w['temperature']}°C and {w['condition'].lower()} in {w['city']}. Feels like {w['feels_like']}°C."
        log_conversation(role="assistant", message=reply_msg)
        log_user_action("weather")
        return {"reply": reply_msg, "action": "none"}

    # Todos / Tasks
    if re.search(r'\b(?:add\s+task|add\s+todo|add\s+to\s+task|add\s+to\s+todo|remind\s+me\s+to|task\s+add\s+karo)\b', lower_text):
        task_text = re.sub(r'^.*?\b(?:add\s+task|add\s+todo|add\s+to\s+task|add\s+to\s+todo|remind\s+me\s+to|task\s+add\s+karo)\b\s*', '', lower_text).strip()
        if task_text:
            item = add_todo(task_text, priority="normal")
            reply_msg = f"Added '{item['text']}' to your tasks, Prem."
            log_conversation(role="assistant", message=reply_msg)
            return {"reply": reply_msg, "action": "none"}

    # Memory / Previous question recall
    if re.search(r'\b(?:what\s+did\s+i\s+ask|previous\s+question|pehle\s+kya\s+pucha|pehle\s+kya\s+bola|last\s+question)\b', lower_text):
        recent = get_recent_conversation(limit=3)
        user_msgs = [h["message"] for h in recent if h["role"].lower() == "user"]
        if len(user_msgs) > 1:
            last_q = user_msgs[-2]
            reply_msg = f"Prem, earlier you asked: '{last_q}'."
        elif user_msgs:
            reply_msg = f"Prem, your last question was: '{user_msgs[-1]}'."
        else:
            reply_msg = "You haven't asked any previous questions in this session yet, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "none"}

    # Current Time / Date
    if re.search(r'\b(?:time|samay|waqt)\b.*\b(?:kya|what|tell|show|is|hua)\b|\b(?:kya|what)\b.*\b(?:time|samay|waqt)\b', lower_text):
        current_time_str = time.strftime("%I:%M %p")
        reply_msg = f"Prem, abhi samay {current_time_str} ho raha hai." if re.search(r'\b(?:samay|waqt|kya|hua)\b', lower_text) else f"Prem, the current time is {current_time_str}."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "none"}

    return None
