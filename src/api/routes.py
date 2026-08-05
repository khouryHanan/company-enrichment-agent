"""
API Controller — Mission 4 / SCRUM-4 (receiving input) and Mission 12 /
SCRUM-12 (full endpoint set, added later on this same branch).

This layer only translates HTTP: it parses the request, calls a service,
and turns a missing result into a 404. It deliberately does not talk to
the database or to other agents directly — where the data lives and how
it is assembled belongs to the services.
"""

from fastapi import APIRouter, HTTPException

from src.api.schemas import BulkEnrichmentRequest, BulkEnrichmentResponse, CompanyEnrichmentResult
from src.services import agent3_integration, batch_service, import_service

router = APIRouter()


@router.get("/api/agents/agent1/agent3-health")
def agent3_health():
    """Whether the Agent 3 scanner is reachable — powers the demo UI's
    status indicator."""
    return {"reachable": agent3_integration.is_reachable()}


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
    return batch_service.start_batch(payload.companies)


@router.post("/api/agents/agent1/bulk-enrichment/import", response_model=BulkEnrichmentResponse)
def start_bulk_enrichment_from_export(rows: list[dict]):
    """
    Accepts an EYEjee platform export (its own field names and bare URLs)
    and runs it as a batch, so the platform can hand its company lists
    over without reshaping them first.

    The export is mapped to our input contract, then validated by the
    same Pydantic models as the regular POST — an export that maps to
    nothing usable is a 400, not an empty batch.
    """
    companies = import_service.from_eyejee_export(rows)
    if not companies:
        raise HTTPException(
            status_code=400,
            detail="no usable companies in export — each row needs a company name and website",
        )
    request = BulkEnrichmentRequest(companies=companies)
    return batch_service.start_batch(request.companies)


@router.get("/api/agents/agent1/bulk-enrichment/{batch_id}")
def get_batch_status(batch_id: str):
    batch = batch_service.get_batch_summary(batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")
    return batch


@router.get("/api/agents/agent1/bulk-enrichment/{batch_id}/companies")
def get_batch_companies(batch_id: str):
    """All company results for a batch (enriched and failed alike), so a
    client can render a batch's outcome without knowing company IDs
    up front. Added for the demo UI (SCRUM-18)."""
    companies = batch_service.get_batch_companies(batch_id)
    if companies is None:
        # None means no such batch; an empty list is a real batch that
        # recorded no companies, which is a 200 with nothing in it.
        raise HTTPException(status_code=404, detail="batch not found")
    return {"batchId": batch_id, "companies": companies}


@router.get("/api/companies/{company_id}", response_model=CompanyEnrichmentResult)
def get_company_result(company_id: str):
    company = batch_service.get_company_profile(company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")
    return company
