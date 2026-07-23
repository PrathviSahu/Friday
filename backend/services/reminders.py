"""
FRIDAY Reminders Service
Manages one-time timers and scheduled reminders with persistent storage.
"""
import json
import uuid
import time
from pathlib import Path
from datetime import datetime

DATA_FILE = Path(__file__).parent.parent / "data" / "reminders.json"
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load() -> list:
    if not DATA_FILE.exists():
        return []
    try:
        return json.loads(DATA_FILE.read_text())
    except Exception:
        return []


def _save(items: list):
    DATA_FILE.write_text(json.dumps(items, indent=2))


def get_active_reminders() -> list:
    """Return all non-triggered reminders."""
    now = time.time()
    items = _load()
    active = [i for i in items if not i.get("triggered") and i.get("trigger_at", 0) > now]
    return sorted(active, key=lambda x: x.get("trigger_at", 0))


def add_reminder(message: str, delay_seconds: int) -> dict:
    """Add a timer/reminder to trigger after delay_seconds."""
    now = time.time()
    trigger_at = now + delay_seconds
    item = {
        "id": str(uuid.uuid4()),
        "message": message.strip(),
        "delay_seconds": delay_seconds,
        "created_at": datetime.now().isoformat(),
        "trigger_at": trigger_at,
        "triggered": False,
    }
    items = _load()
    items.append(item)
    _save(items)
    return item


def check_due_reminders() -> list:
    """Check and mark any due reminders as triggered. Returns due items."""
    now = time.time()
    items = _load()
    due = []
    updated = False
    for i in items:
        if not i.get("triggered") and i.get("trigger_at", 0) <= now:
            i["triggered"] = True
            due.append(i)
            updated = True
    if updated:
        _save(items)
    return due
