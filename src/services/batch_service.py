"""
Batch Processing Service — Mission 7.

Orchestrates the full pipeline for a bulk request: assigns a batch ID,
tracks batch and per-company status, and ensures one failed company
does not stop the rest of the batch.
"""

import uuid

from src.services import validation_service, normalization_service, enrichment_service, agent3_integration, merge_service
from src.db import repository
from src.core import logging as log


def start_batch(companies: list) -> dict:
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    log.info("batch_started", batch_id=batch_id, total=len(companies))

    validation_result = validation_service.validate_companies(companies)

    repository.create_batch(batch_id, status="Running", validation=validation_result)

    for company in validation_result.valid_companies:
        _process_company(batch_id, company)

    repository.finalize_batch(batch_id)
    log.info("batch_completed", batch_id=batch_id)

    return {
        "batchId": batch_id,
        "status": "Running",
        "totalReceived": validation_result.total_received,
        "validCompanies": len(validation_result.valid_companies),
        "invalidCompanies": len(validation_result.invalid_companies),
        "duplicates": len(validation_result.duplicates),
    }


def _process_company(batch_id: str, company) -> None:
    """
    Per-company pipeline: normalize -> enrich -> trigger Agent 3 -> merge -> persist.
    Any failure here should be caught and logged, not raised, so the batch continues.
    """
    try:
        normalized = normalization_service.normalize_website_url(company.websiteUrl)
        enrichment = enrichment_service.enrich_company(company, normalized)
        scan_result = agent3_integration.trigger_scan(company_id=enrichment["companyId"], website_url=normalized["normalizedWebsite"])
        final_profile = merge_service.merge_results(enrichment, scan_result)
        repository.save_company(batch_id, final_profile)
    except Exception as exc:  # noqa: BLE001 — intentionally broad, isolates per-company failures
        log.error("company_processing_failed", batch_id=batch_id, error=str(exc))
        repository.mark_company_failed(batch_id, company, str(exc))
