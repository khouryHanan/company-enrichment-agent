"""
API Controller — Mission 4 / SCRUM-4 (receiving input) and Mission 12 /
SCRUM-12 (full endpoint set, added later on this same branch).
"""

from fastapi import APIRouter, HTTPException

from src.api.schemas import BulkEnrichmentRequest, BulkEnrichmentResponse, CompanyEnrichmentResult
from src.services import batch_service
from src.db import repository

router = APIRouter()


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


@router.get("/api/companies/{company_id}", response_model=CompanyEnrichmentResult)
def get_company_result(company_id: str):
    company = repository.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="company not found")
    return company
