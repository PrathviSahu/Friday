"""
FRIDAY Todo Service
Persists tasks to backend/data/todos.json
"""
import json
import uuid
from pathlib import Path
from datetime import datetime

DATA_FILE = Path(__file__).parent.parent / "data" / "todos.json"
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load() -> list:
    if not DATA_FILE.exists():
        return []
    try:
        return json.loads(DATA_FILE.read_text())
    except Exception:
        return []


def _save(todos: list):
    DATA_FILE.write_text(json.dumps(todos, indent=2))


def get_todos() -> list:
    """Return all todos sorted by created_at descending."""
    return sorted(_load(), key=lambda t: t.get("created_at", ""), reverse=True)


def add_todo(text: str, priority: str = "normal") -> dict:
    """Add a new todo and return it."""
    todos = _load()
    item = {
        "id": str(uuid.uuid4()),
        "text": text.strip(),
        "done": False,
        "priority": priority,  # "high" | "normal" | "low"
        "created_at": datetime.now().isoformat(),
    }
    todos.append(item)
    _save(todos)
    return item


def toggle_todo(todo_id: str) -> dict | None:
    """Toggle done/undone state. Returns updated item or None if not found."""
    todos = _load()
    for t in todos:
        if t["id"] == todo_id:
            t["done"] = not t["done"]
            _save(todos)
            return t
    return None


def delete_todo(todo_id: str) -> bool:
    """Delete a todo by id. Returns True if deleted."""
    todos = _load()
    new = [t for t in todos if t["id"] != todo_id]
    if len(new) == len(todos):
        return False
    _save(new)
    return True


def clear_done() -> int:
    """Remove all completed todos. Returns count removed."""
    todos = _load()
    remaining = [t for t in todos if not t["done"]]
    removed = len(todos) - len(remaining)
    _save(remaining)
    return removed


def update_todo_text(todo_id: str, text: str) -> dict | None:
    """Edit a todo's text. Returns updated item or None."""
    todos = _load()
    for t in todos:
        if t["id"] == todo_id:
            t["text"] = text.strip()
            _save(todos)
            return t
    return None
