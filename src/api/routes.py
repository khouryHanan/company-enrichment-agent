"""
API Controller — Mission 12.

Endpoints:
  POST /api/agents/agent1/bulk-enrichment
  GET  /api/agents/agent1/bulk-enrichment/{batchId}
  GET  /api/companies/{companyId}
"""

from fastapi import APIRouter, HTTPException

from src.api.schemas import BulkEnrichmentRequest, BulkEnrichmentResponse, CompanyEnrichmentResult
from src.services import batch_service
from src.db import repository

router = APIRouter()


@router.post("/api/agents/agent1/bulk-enrichment", response_model=BulkEnrichmentResponse)
def start_bulk_enrichment(payload: BulkEnrichmentRequest):
    if not payload.companies:
        raise HTTPException(status_code=400, detail="companies list cannot be empty")

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
