"""
Database Service (Repository) — Mission 8 / SCRUM-8, extended for
Mission 11 / SCRUM-11's source-reference persistence.

All read/write functions used by the rest of the app live here, so no
other service touches SQLAlchemy directly.

Note on schema: Company does not have missing_fields/sources_used
columns — those live inside EnrichmentResult.raw_ai_output (the full
profile dict is kept there for auditability), and get_company
reconstructs them from there rather than from separate Company columns.
"""

import uuid

from sqlalchemy.exc import IntegrityError, OperationalError

from src.db.database import SessionLocal
from src.db.models import Batch, Company, EnrichmentResult, ErrorLog, Source
from src.core.errors import DatabaseSaveError, NotFoundError
from src.core import logging as log
from src.core.retry import retry


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def create_batch(status: str, validation) -> str:
    """
    Creates the batch record with the counts from validation_service's
    ValidationResult. The batch ID is generated here (models.py doesn't
    auto-generate IDs) and returned so the caller can use it for
    subsequent per-company processing. Duplicate/invalid companies are
    also recorded as error entries, so they're visible in the errors
    table too, not just the count.
    """
    session = SessionLocal()
    try:
        batch_id = _new_id("batch")
        batch = Batch(
            id=batch_id,
            status=status,
            total_received=validation.total_received,
            valid_companies=len(validation.valid_companies),
            invalid_companies=len(validation.invalid_companies),
            duplicates=len(validation.duplicates),
        )
        session.add(batch)

        for invalid in validation.invalid_companies:
            session.add(ErrorLog(
                id=_new_id("error"),
                batch_id=batch_id,
                error_type="InvalidInputError",
                message="; ".join(invalid["errors"]),
            ))
        for dup in validation.duplicates:
            session.add(ErrorLog(
                id=_new_id("error"),
                batch_id=batch_id,
                error_type="DuplicateCompanyError",
                message=dup["reason"],
            ))

        retry(session.commit, retryable_exceptions=(OperationalError,), event_name="create_batch_commit")
        log.info("batch_created", batch_id=batch_id, total=validation.total_received)
        return batch_id
    except IntegrityError as exc:
        session.rollback()
        log.error("database_save_failed", error=str(exc))
        raise DatabaseSaveError(f"failed to create batch: {exc}") from exc
    except OperationalError as exc:
        session.rollback()
        log.error("database_save_failed", error=str(exc))
        raise DatabaseSaveError(f"failed to create batch after retries: {exc}") from exc
    finally:
        session.close()


def finalize_batch(batch_id: str) -> None:
    """
    Sets the batch's final status based on its companies' outcomes:
    Completed if all succeeded, Completed with Errors if some failed,
    Failed if none succeeded.
    """
    session = SessionLocal()
    try:
        batch = session.get(Batch, batch_id)
        if not batch:
            raise NotFoundError(f"batch {batch_id} not found")

        companies = session.query(Company).filter(Company.batch_id == batch_id).all()
        statuses = {c.status for c in companies}

        if not companies:
            batch.status = "Completed"
        elif statuses <= {"Completed"}:
            batch.status = "Completed"
        elif "Completed" in statuses or "Partially Completed" in statuses:
            batch.status = "Completed with Errors"
        else:
            batch.status = "Failed"

        session.commit()
        log.info("batch_completed", batch_id=batch_id, status=batch.status)
    finally:
        session.close()


def get_batch(batch_id: str) -> dict | None:
    session = SessionLocal()
    try:
        batch = session.get(Batch, batch_id)
        if not batch:
            return None
        return {
            "batchId": batch.id,
            "status": batch.status,
            "totalReceived": batch.total_received,
            "validCompanies": batch.valid_companies,
            "invalidCompanies": batch.invalid_companies,
            "duplicates": batch.duplicates,
        }
    finally:
        session.close()


def save_company(batch_id: str, profile: dict) -> None:
    """
    Persists a company's final merged profile (post-enrichment, post-merge
    with Agent 3's scan). The full profile dict — including missingFields
    and sourcesUsed, which aren't their own Company columns — is kept in
    EnrichmentResult.raw_ai_output for auditability and later retrieval.
    Mission 11's source references (field -> URL) are persisted as
    individual Source rows.
    """
    session = SessionLocal()
    try:
        company_id = profile.get("companyId") or _new_id("company")
        company = Company(
            id=company_id,
            batch_id=batch_id,
            company_name=profile["companyName"],
            website_url=profile.get("websiteUrl", profile.get("normalizedWebsite", "")),
            domain=profile.get("domain"),
            linkedin_url=profile.get("linkedinUrl"),
            description=profile.get("description"),
            industry=profile.get("industry"),
            products_services=profile.get("productsServices", []),
            target_audience=profile.get("targetAudience", []),
            business_model=profile.get("businessModel"),
            location=profile.get("location"),
            company_size=profile.get("companySize"),
            founded_year=profile.get("foundedYear"),
            headquarters=profile.get("headquarters"),
            key_competitors=profile.get("keyCompetitors", []),
            tech_stack=profile.get("techStack", []),
            key_contacts=profile.get("keyContacts", []),
            confidence=profile.get("confidence"),
            status=profile.get("status", "Completed"),
        )
        session.add(company)
        session.add(EnrichmentResult(
            id=_new_id("result"),
            company_id=company.id,
            raw_ai_output=profile,
        ))

        # Mission 11: persist which URL backs which piece of confirmed
        # website evidence, kept separate from the AI-generated fields.
        for ref in profile.get("sourceReferences", []):
            session.add(Source(
                id=_new_id("source"),
                company_id=company.id,
                field_name=ref.get("field"),
                source_url=ref.get("url"),
            ))

        retry(session.commit, retryable_exceptions=(OperationalError,), event_name="save_company_commit")
        log.info("company_saved", batch_id=batch_id, company_id=company.id, status=company.status)
    except IntegrityError as exc:
        session.rollback()
        # Most likely the unique (batch_id, domain) constraint — a
        # duplicate that slipped past validation. Permanent — not
        # retried, since retrying an identical insert fails identically.
        log.error("database_save_failed", batch_id=batch_id, error=str(exc))
        raise DatabaseSaveError(f"failed to save company in batch {batch_id}: {exc}") from exc
    except OperationalError as exc:
        session.rollback()
        # Transient (e.g. SQLite "database is locked") — already retried
        # by retry() above; this is the final failure after all attempts.
        log.error("database_save_failed", batch_id=batch_id, error=str(exc))
        raise DatabaseSaveError(f"failed to save company in batch {batch_id} after retries: {exc}") from exc
    finally:
        session.close()


def _company_to_dict(company: Company) -> dict:
    # missingFields/sourcesUsed aren't their own Company columns —
    # pull them back out of the saved raw AI output if present.
    missing_fields = []
    sources_used = []
    if company.enrichment_result and company.enrichment_result.raw_ai_output:
        raw = company.enrichment_result.raw_ai_output
        missing_fields = raw.get("missingFields", [])
        sources_used = raw.get("sourcesUsed", [])

    return {
        "companyId": company.id,
        "batchId": company.batch_id,
        "companyName": company.company_name,
        "description": company.description,
        "industry": company.industry,
        "productsServices": company.products_services,
        "targetAudience": company.target_audience,
        "businessModel": company.business_model,
        "location": company.location,
        "companySize": company.company_size,
        "foundedYear": company.founded_year,
        "headquarters": company.headquarters,
        "keyCompetitors": company.key_competitors or [],
        "techStack": company.tech_stack or [],
        "keyContacts": company.key_contacts or [],
        "confidence": company.confidence,
        "missingFields": missing_fields,
        "sourcesUsed": sources_used,
        "status": company.status,
    }


def get_company(company_id: str) -> dict | None:
    session = SessionLocal()
    try:
        company = session.get(Company, company_id)
        if not company:
            return None
        return _company_to_dict(company)
    finally:
        session.close()


def get_companies_for_batch(batch_id: str) -> list[dict]:
    """All companies recorded for a batch — enriched and failed alike —
    in insertion order. Used by the demo UI's batch results view."""
    session = SessionLocal()
    try:
        companies = (
            session.query(Company)
            .filter(Company.batch_id == batch_id)
            .order_by(Company.created_at)
            .all()
        )
        return [_company_to_dict(company) for company in companies]
    finally:
        session.close()


def mark_company_failed(batch_id: str, company, error_message: str) -> None:
    """
    Records a failed company without crashing the batch. `company` here is
    the original validated input object (companyName, websiteUrl, ...),
    since enrichment/merge never completed for it.
    """
    session = SessionLocal()
    try:
        company_id = _new_id("company")
        failed = Company(
            id=company_id,
            batch_id=batch_id,
            company_name=getattr(company, "companyName", "unknown"),
            website_url=getattr(company, "websiteUrl", "unknown"),
            linkedin_url=getattr(company, "linkedinUrl", None),
            status="Failed",
        )
        session.add(failed)
        session.add(ErrorLog(
            id=_new_id("error"),
            batch_id=batch_id,
            company_id=company_id,
            error_type="ProcessingError",
            message=error_message,
        ))
        session.commit()
        log.error("company_marked_failed", batch_id=batch_id, error=error_message)
    finally:
        session.close()