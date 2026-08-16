"""services/brain/handlers/hardware_handler.py — macOS hardware & display control (Brightness, Dark mode, Lock screen, Screenshots)."""

import re
from typing import Optional
from services.memory import log_conversation
from services.system_control import take_screenshot
from services.mac_controls import (
    get_brightness,
    set_brightness,
    set_dark_mode,
    lock_display,
)


def handle_hardware(lower_text: str, is_boss: bool) -> Optional[dict]:
    """Handles OS-level hardware toggles and macOS system integrations."""
    # Screenshot
    if re.search(r'\b(?:screenshot|screen\s+shot|capture\s+screen)\b', lower_text):
        path = take_screenshot()
        reply_msg = "Screenshot saved, Prem." if path else "Screenshot failed."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "none"}

    # Display Brightness
    if re.search(r'\b(?:brightness|dim\s+screen|brighten\s+screen|screen\s+brightness)\b', lower_text):
        b_match = re.search(r'(\d{1,3})\s*(?:%|percent)?', lower_text)
        if b_match:
            lvl = int(b_match.group(1))
        elif any(w in lower_text for w in ["max", "full", "100"]):
            lvl = 100
        elif any(w in lower_text for w in ["dim", "lower", "reduce", "down"]):
            lvl = max(10, int(get_brightness() * 100) - 25)
        elif any(w in lower_text for w in ["up", "increase", "higher", "bright"]):
            lvl = min(100, int(get_brightness() * 100) + 25)
        else:
            lvl = 80
        
        set_brightness(lvl)
        reply_msg = f"Brightness set to {lvl}%, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "brightness"}

    # Dark / Light Mode
    if re.search(r'\b(?:dark\s+mode|light\s+mode|appearance|theme)\b', lower_text):
        enable_dark = not ("light mode" in lower_text or "turn off dark" in lower_text or "disable dark" in lower_text)
        set_dark_mode(enable_dark)
        mode_name = "Dark mode" if enable_dark else "Light mode"
        reply_msg = f"{mode_name} enabled, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "dark_mode"}

    # Lock Display
    if re.search(r'\b(?:lock\s+screen|lock\s+display|lock\s+mac|lock\0)\b|\b(?:lock\s+the\s+screen|sleep\s+display)\b', lower_text):
        lock_display()
        reply_msg = "Locking display, Prem."
        log_conversation(role="assistant", message=reply_msg)
        return {"reply": reply_msg, "action": "lock_screen"}

    return None
