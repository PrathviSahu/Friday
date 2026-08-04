"""routes/todos.py — task management CRUD."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_boss
from services.todos import (
    get_todos,
    add_todo,
    toggle_todo,
    delete_todo,
    clear_done,
    update_todo_text,
)

router = APIRouter(prefix="/api", tags=["todos"])


class TodoCreateRequest(BaseModel):
    text: str
    priority: str = "normal"  # "high" | "normal" | "low"


class TodoTextRequest(BaseModel):
    text: str


@router.get("/todos")
def get_todos_endpoint():
    """Get all todos"""
    return {"todos": get_todos()}


@router.post("/todos", dependencies=[Depends(require_boss)])
def create_todo_endpoint(req: TodoCreateRequest):
    """Add a new todo"""
    item = add_todo(req.text, req.priority)
    return {"status": "ok", "todo": item}


@router.patch("/todos/{todo_id}/toggle", dependencies=[Depends(require_boss)])
def toggle_todo_endpoint(todo_id: str):
    """Toggle a todo's done state"""
    item = toggle_todo(todo_id)
    if not item:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"status": "ok", "todo": item}


@router.patch("/todos/{todo_id}/text", dependencies=[Depends(require_boss)])
def update_todo_endpoint(todo_id: str, req: TodoTextRequest):
    """Edit todo text"""
    item = update_todo_text(todo_id, req.text)
    if not item:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"status": "ok", "todo": item}


@router.delete("/todos/done", dependencies=[Depends(require_boss)])
def clear_done_endpoint():
    """Remove all completed todos"""
    count = clear_done()
    return {"status": "ok", "removed": count}


@router.delete("/todos/{todo_id}", dependencies=[Depends(require_boss)])
def delete_todo_endpoint(todo_id: str):
    """Delete a todo by id"""
    ok = delete_todo(todo_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"status": "ok"}
