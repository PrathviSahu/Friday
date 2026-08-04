"""routes/company.py — Company Intelligence endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import require_boss
from services import company_intelligence
from services.permissions import require_permission

router = APIRouter(prefix="/api/company", tags=["company"])


@router.get("/intel", dependencies=[Depends(require_boss), Depends(require_permission("web.search"))])
def company_intel_endpoint(name: str = Query(..., min_length=1)):
    """Company brief: overview, hiring signals, your applications, prep checklist."""
    try:
        intel = company_intelligence.get_company_intel(name)
    except company_intelligence.CompanyIntelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return intel
