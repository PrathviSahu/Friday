"""routes/documents.py — Document Agent endpoints.

Upload (PDF/DOCX/PPTX/XLSX/TXT) → extract → SQLite → ask / summarize /
compare via Groq. Original files are not stored — only the text.
"""

import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from auth import require_boss
from services import document_agent
from services.permissions import require_permission

router = APIRouter(prefix="/api/documents", tags=["documents"])


class AskRequest(BaseModel):
    question: str


class CompareRequest(BaseModel):
    ids: list[str]


def _unavailable(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


@router.post("/upload", dependencies=[Depends(require_boss), Depends(require_permission("documents.upload"))])
async def documents_upload_endpoint(request: Request, file: UploadFile = File(...)):
    """Upload a document and extract its text."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(data) > document_agent.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {document_agent.MAX_UPLOAD_BYTES // (1024 * 1024)} MB).",
        )
    try:
        doc = await asyncio.to_thread(document_agent.add_document, file.filename or "upload", data)
    except document_agent.DocumentUnavailableError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok", "document": doc}


@router.get("", dependencies=[Depends(require_boss), Depends(require_permission("documents.read"))])
def documents_list_endpoint(limit: int = 50):
    return {"documents": document_agent.list_documents(limit=limit)}


@router.get("/search", dependencies=[Depends(require_boss), Depends(require_permission("documents.read"))])
def documents_search_endpoint(q: str):
    return {"documents": document_agent.search_documents(q)}


@router.get("/{doc_id}", dependencies=[Depends(require_boss), Depends(require_permission("documents.read"))])
def documents_get_endpoint(doc_id: str):
    doc = document_agent.get_document(doc_id, include_text=True)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"document": doc}


@router.post("/{doc_id}/ask", dependencies=[Depends(require_boss), Depends(require_permission("documents.read"))])
def documents_ask_endpoint(doc_id: str, req: AskRequest):
    try:
        answer = document_agent.ask_document(doc_id, req.question)
    except document_agent.DocumentUnavailableError as exc:
        raise _unavailable(exc) from exc
    return {"answer": answer}


@router.post("/{doc_id}/summarize", dependencies=[Depends(require_boss), Depends(require_permission("documents.read"))])
def documents_summarize_endpoint(doc_id: str):
    try:
        summary = document_agent.summarize_document(doc_id)
    except document_agent.DocumentUnavailableError as exc:
        raise _unavailable(exc) from exc
    return {"summary": summary}


@router.post("/compare", dependencies=[Depends(require_boss), Depends(require_permission("documents.read"))])
def documents_compare_endpoint(req: CompareRequest):
    try:
        comparison = document_agent.compare_documents(req.ids)
    except document_agent.DocumentUnavailableError as exc:
        raise _unavailable(exc) from exc
    return {"comparison": comparison}


@router.delete("/{doc_id}", dependencies=[Depends(require_boss), Depends(require_permission("documents.upload"))])
def documents_delete_endpoint(doc_id: str):
    ok = document_agent.delete_document(doc_id)
    return {"status": "ok" if ok else "not_found"}
