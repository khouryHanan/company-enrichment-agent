"""
Database Service (Repository) — Mission 8 / SCRUM-8.

All read/write functions used by the rest of the app live here, so no
other service touches SQLAlchemy directly.
"""

from sqlalchemy.exc import IntegrityError

from src.db.database import SessionLocal
from src.db.models import Batch, Company, EnrichmentResult, ErrorLog
from src.core.errors import DatabaseSaveError, NotFoundError
from src.core import logging as log


def create_batch(status: str, validation) -> str:
    """
    Creates the batch record with the counts from validation_service's
    ValidationResult. The batch ID is generated here (DB owns ID
    generation) and returned so the caller can use it for subsequent
    per-company processing. Duplicate companies are recorded as an
    error entry each, so they're visible in the errors table too, not
    just the count.
    """
    session = SessionLocal()
    try:
        batch = Batch(
            status=status,
            total_received=validation.total_received,
            valid_companies_count=len(validation.valid_companies),
            invalid_companies_count=len(validation.invalid_companies),
            duplicates_count=len(validation.duplicates),
        )
        session.add(batch)
        session.flush()  # populate batch.id from the default before using it below
        batch_id = batch.id

        for invalid in validation.invalid_companies:
            session.add(ErrorLog(
                batch_id=batch_id,
                error_type="InvalidInputError",
                message="; ".join(invalid["errors"]),
            ))
        for dup in validation.duplicates:
            session.add(ErrorLog(
                batch_id=batch_id,
                error_type="DuplicateCompanyError",
                message=dup["reason"],
            ))

        session.commit()
        log.info("batch_created", batch_id=batch_id, total=validation.total_received)
        return batch_id
    except IntegrityError as exc:
        session.rollback()
        log.error("database_save_failed", error=str(exc))
        raise DatabaseSaveError(f"failed to create batch: {exc}") from exc
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
            "validCompanies": batch.valid_companies_count,
            "invalidCompanies": batch.invalid_companies_count,
            "duplicates": batch.duplicates_count,
        }
    finally:
        session.close()


def save_company(batch_id: str, profile: dict) -> None:
    """
    Persists a company's final merged profile (post-enrichment, post-merge
    with Agent 3's scan). `profile` is expected to carry both the original
    input fields (companyName, websiteUrl, domain, linkedinUrl) and the
    enrichment output fields (description, industry, etc.) — batch_service
    is responsible for combining these before calling save_company.
    """
    session = SessionLocal()
    try:
        company = Company(
            id=profile.get("companyId"),
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
            confidence=profile.get("confidence"),
            missing_fields=profile.get("missingFields", []),
            sources_used=profile.get("sourcesUsed", []),
            status=profile.get("status", "Completed"),
        )
        session.add(company)
        session.add(EnrichmentResult(company_id=company.id, raw_ai_output=profile))
        session.commit()
        log.info("company_saved", batch_id=batch_id, company_id=company.id, status=company.status)
    except IntegrityError as exc:
        session.rollback()
        # Most likely the unique (batch_id, domain) constraint — a
        # duplicate that slipped past validation. Log and re-raise so the
        # caller can mark this one company failed without crashing the batch.
        log.error("database_save_failed", batch_id=batch_id, error=str(exc))
        raise DatabaseSaveError(f"failed to save company in batch {batch_id}: {exc}") from exc
    finally:
        session.close()


def get_company(company_id: str) -> dict | None:
    session = SessionLocal()
    try:
        company = session.get(Company, company_id)
        if not company:
            return None
        return {
            "companyId": company.id,
            "batchId": company.batch_id,
            "companyName": company.company_name,
            "description": company.description,
            "industry": company.industry,
            "productsServices": company.products_services,
            "targetAudience": company.target_audience,
            "businessModel": company.business_model,
            "confidence": company.confidence,
            "missingFields": company.missing_fields,
            "sourcesUsed": company.sources_used,
            "status": company.status,
        }
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
        failed = Company(
            batch_id=batch_id,
            company_name=getattr(company, "companyName", "unknown"),
            website_url=getattr(company, "websiteUrl", "unknown"),
            linkedin_url=getattr(company, "linkedinUrl", None),
            status="Failed",
        )
        session.add(failed)
        session.add(ErrorLog(
            batch_id=batch_id,
            company_id=failed.id,
            error_type="ProcessingError",
            message=error_message,
        ))
        session.commit()
        log.error("company_marked_failed", batch_id=batch_id, error=error_message)
    finally:
        session.close()
