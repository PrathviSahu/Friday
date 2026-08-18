"""routes/life_memory.py — searchable life memory (knowledge-graph-lite)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_boss
from services.life_memory import (
    save_memory, list_memories, delete_memory, search_memories,
    answer_memory_query,
)

router = APIRouter(prefix="/api", tags=["life-memory"])


class MemoryCreate(BaseModel):
    subject: str = "Boss"
    relation: str = "remembers"
    target: str
    category: str = "personal"
    note: str = ""


@router.get("/life-memory", dependencies=[Depends(require_boss)])
def get_life_memories(category: str = None, limit: int = 100):
    """List stored memory triples (optionally filtered by category)."""
    return {"memories": list_memories(category=category, limit=limit)}


@router.post("/life-memory", dependencies=[Depends(require_boss)])
def add_life_memory(req: MemoryCreate):
    """Store a (subject → relation → target) memory (owner only)."""
    try:
        mid = save_memory(req.subject, req.relation, req.target,
                          category=req.category, note=req.note)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "ok", "memory_id": mid}


@router.get("/life-memory/search", dependencies=[Depends(require_boss)])
def search_life_memories(q: str = ""):
    """Search memories by query; returns matches + a natural-language answer."""
    matches = search_memories(q, limit=8)
    return {"query": q, "matches": matches,
            "answer": answer_memory_query(q)}


@router.delete("/life-memory/{memory_id}", dependencies=[Depends(require_boss)])
def remove_life_memory(memory_id: int):
    ok = delete_memory(memory_id)
    if not ok:
        raise HTTPException(404, "Memory not found")
    return {"status": "ok"}
