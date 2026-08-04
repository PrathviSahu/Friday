"""routes/coding.py — Coding Workspace AI endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_boss
from services import coding_agent
from services.permissions import require_permission

router = APIRouter(prefix="/api/coding", tags=["coding"])


class CodeRequest(BaseModel):
    code: str
    language: str = ""


def _unavailable(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


@router.post("/review", dependencies=[Depends(require_boss), Depends(require_permission("coding.analyze"))])
def coding_review_endpoint(req: CodeRequest):
    try:
        return {"result": coding_agent.review_code(req.code, req.language)}
    except coding_agent.CodingUnavailableError as exc:
        raise _unavailable(exc) from exc


@router.post("/explain", dependencies=[Depends(require_boss), Depends(require_permission("coding.analyze"))])
def coding_explain_endpoint(req: CodeRequest):
    try:
        return {"result": coding_agent.explain_code(req.code, req.language)}
    except coding_agent.CodingUnavailableError as exc:
        raise _unavailable(exc) from exc


@router.post("/bugs", dependencies=[Depends(require_boss), Depends(require_permission("coding.analyze"))])
def coding_bugs_endpoint(req: CodeRequest):
    try:
        return {"result": coding_agent.find_bugs(req.code, req.language)}
    except coding_agent.CodingUnavailableError as exc:
        raise _unavailable(exc) from exc


@router.post("/tests", dependencies=[Depends(require_boss), Depends(require_permission("coding.analyze"))])
def coding_tests_endpoint(req: CodeRequest):
    try:
        return {"result": coding_agent.generate_tests(req.code, req.language)}
    except coding_agent.CodingUnavailableError as exc:
        raise _unavailable(exc) from exc


@router.post("/docs", dependencies=[Depends(require_boss), Depends(require_permission("coding.analyze"))])
def coding_docs_endpoint(req: CodeRequest):
    try:
        return {"result": coding_agent.generate_docs(req.code, req.language)}
    except coding_agent.CodingUnavailableError as exc:
        raise _unavailable(exc) from exc


@router.post("/refactor", dependencies=[Depends(require_boss), Depends(require_permission("coding.analyze"))])
def coding_refactor_endpoint(req: CodeRequest):
    try:
        return {"result": coding_agent.suggest_refactor(req.code, req.language)}
    except coding_agent.CodingUnavailableError as exc:
        raise _unavailable(exc) from exc
