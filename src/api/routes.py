"""
API Controller — Mission 4 / SCRUM-4 (receiving input) and Mission 12 /
SCRUM-12 (full endpoint set, added later on this same branch).
"""

import httpx
from fastapi import APIRouter, HTTPException

from src.api.schemas import BulkEnrichmentRequest, BulkEnrichmentResponse, CompanyEnrichmentResult
from src.core.config import settings
from src.services import batch_service
from src.db import repository

router = APIRouter()


@router.get("/api/agents/agent1/agent3-health")
def agent3_health():
    """Reachability probe for the demo UI's status indicator. Any HTTP
    response counts as reachable — only a connection failure means the
    scanner is down."""
    try:
        httpx.get(settings.AGENT3_BASE_URL, timeout=1.0)
        return {"reachable": True}
    except httpx.HTTPError:
        return {"reachable": False}


@router.post("/api/agents/agent1/bulk-enrichment", response_model=BulkEnrichmentResponse)
def start_bulk_enrichment(payload: BulkEnrichmentRequest):
    """
    Receives a bulk list of companies and kicks off batch processing.

    Structural validation (non-empty list, required fields present) is
    handled by BulkEnrichmentRequest/CompanyInput in schemas.py — Pydantic
    rejects malformed requests automatically with a 422 before this
    function body even runs. Business-rule validation (URL format,
    duplicates) happens downstream in validation_service.py (SCRUM-5).
    """
    result = batch_service.start_batch(payload.companies)
    return result


@router.get("/api/agents/agent1/bulk-enrichment/{batch_id}")
def get_batch_status(batch_id: str):
    batch = repository.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="batch not found")
    return batch


@router.get("/api/agents/agent1/bulk-enrichment/{batch_id}/companies")
def get_batch_companies(batch_id: str):
    """All company results for a batch (enriched and failed alike), so a
    client can render a batch's outcome without knowing company IDs
    up front. Added for the demo UI (SCRUM-18)."""
    batch = repository.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="batch not found")
    return {"batchId": batch_id, "companies": repository.get_companies_for_batch(batch_id)}


@router.get("/api/companies/{company_id}", response_model=CompanyEnrichmentResult)
def get_company_result(company_id: str):
    company = repository.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="company not found")
    return company
