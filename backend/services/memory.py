"""memory.py — Backwards-compatibility shim.

All memory functions now delegate to learning_engine.py (friday_brain.db).
This file is kept so existing brain.py imports continue to work unchanged.
"""
from services.learning_engine import (
    save_fact,
    delete_fact,
    get_fact,
    get_all_memories,
    get_memory_context_string,
    log_conversation,
    get_recent_conversation,
)

__all__ = [
    "save_fact",
    "delete_fact",
    "get_fact",
    "get_all_memories",
    "get_memory_context_string",
    "log_conversation",
    "get_recent_conversation",
]
