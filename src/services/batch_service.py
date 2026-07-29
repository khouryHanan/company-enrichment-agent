"""
Batch Processing Service — Mission 7 / SCRUM-7.

Orchestrates the full pipeline for a bulk request: assigns a batch ID,
tracks batch and per-company status, and ensures one failed company
does not stop the rest of the batch.

Downstream services (normalization, enrichment, Agent 3, merge) are
called here but any failure in any of them is caught and isolated to
that one company — this orchestration layer's correctness does not
depend on those services being fully implemented yet.
"""

from src.services import validation_service, normalization_service, enrichment_service, agent3_integration, merge_service
from src.db import repository
from src.core import logging as log


def start_batch(companies: list) -> dict:
    """
    Entry point called by the API layer (SCRUM-4/12). Validates the
    incoming companies, creates the batch record, processes each valid
    company independently, finalizes the batch, and returns a summary.
    """
    validation_result = validation_service.validate_companies(companies)

    batch_id = repository.create_batch(status="Running", validation=validation_result)
    log.info("batch_started", batch_id=batch_id, total=validation_result.total_received)

    for company in validation_result.valid_companies:
        _process_company(batch_id, company)

    repository.finalize_batch(batch_id)
    log.info("batch_completed", batch_id=batch_id)

    final_batch = repository.get_batch(batch_id)
    return final_batch


def _process_company(batch_id: str, company) -> None:
    """
    Per-company pipeline: normalize -> enrich -> trigger Agent 3 -> merge
    -> persist. Any exception at any stage is caught here so it cannot
    propagate up and abort the rest of the batch — this is the core
    guarantee SCRUM-7 is responsible for.
    """
    log.info("company_processing_started", batch_id=batch_id, company_name=getattr(company, "companyName", "unknown"))

    try:
        normalized = normalization_service.normalize_website_url(company.websiteUrl)
    except Exception as exc:
        log.error("normalization_failed", batch_id=batch_id, error=str(exc))
        repository.mark_company_failed(batch_id, company, f"normalization failed: {exc}")
        return

    try:
        enrichment = enrichment_service.enrich_company(company, normalized)
    except Exception as exc:
        log.error("enrichment_failed", batch_id=batch_id, error=str(exc))
        repository.mark_company_failed(batch_id, company, f"enrichment failed: {exc}")
        return

    # Agent 3 is allowed to fail without failing the whole company —
    # per Mission 10, a scan failure should still let the company be
    # saved with whatever the AI enrichment already produced.
    scan_result = None
    try:
        scan_result = agent3_integration.trigger_scan(
            company_id=enrichment["companyId"],
            website_url=normalized.get("normalizedWebsite", company.websiteUrl),
        )
    except Exception as exc:
        log.error("agent3_scan_failed", batch_id=batch_id, company_id=enrichment.get("companyId"), error=str(exc))

    try:
        if scan_result and scan_result.get("scanStatus") == "Completed":
            final_profile = merge_service.merge_results(enrichment, scan_result)
        else:
            # No successful scan — save the AI enrichment as-is, marked
            # Partially Completed rather than fully Completed, since
            # website evidence never confirmed/extended it.
            final_profile = dict(enrichment, status="Partially Completed")
    except Exception as exc:
        log.error("merge_failed", batch_id=batch_id, error=str(exc))
        final_profile = dict(enrichment, status="Partially Completed")

    try:
        repository.save_company(batch_id, final_profile)
        log.info("company_processing_completed", batch_id=batch_id, company_id=final_profile.get("companyId"))
    except Exception as exc:
        log.error("database_save_failed", batch_id=batch_id, error=str(exc))
        repository.mark_company_failed(batch_id, company, f"database save failed: {exc}")
