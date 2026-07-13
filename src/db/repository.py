"""
Database Service — read/write functions used by every other service.
Keeps raw SQL/ORM calls out of the service layer.
"""

import uuid
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from src.core.errors import DatabaseSaveError
from src.db.database import SessionLocal
from src.db.models import Batch, Company, EnrichmentResult, ErrorLog, Source


def _normalize_domain(value: str | None) -> str | None:
    """Return a lowercase domain without scheme, path, port, or www."""
    if not value or not value.strip():
        return None

    candidate = value.strip().lower()
    parsed = urlparse(candidate if "://" in candidate else f"//{candidate}")
    domain = parsed.hostname or parsed.path.split("/")[0]

    if not domain:
        return None

    return domain.removeprefix("www.")


def _input_value(company, field_name: str, default=None):
    if isinstance(company, dict):
        return company.get(field_name, default)
    return getattr(company, field_name, default)


def create_batch(batch_id: str, status: str, validation) -> None:
    """Persist a new enrichment batch and its validation counters."""
    batch = Batch(
        id=batch_id,
        status=status,
        total_received=validation.total_received,
        valid_companies=len(validation.valid_companies),
        invalid_companies=len(validation.invalid_companies),
        duplicates=len(validation.duplicates),
    )

    try:
        with SessionLocal() as session:
            session.add(batch)
            session.commit()
    except IntegrityError as exc:
        raise DatabaseSaveError(f"batch already exists: {batch_id}") from exc


def finalize_batch(batch_id: str) -> None:
    """Mark a batch completed, preserving whether company errors occurred."""
    with SessionLocal() as session:
        batch = session.get(Batch, batch_id)
        if batch is None:
            return

        error_count = session.scalar(
            select(func.count(ErrorLog.id)).where(ErrorLog.batch_id == batch_id)
        ) or 0

        failed_count = session.scalar(
            select(func.count(Company.id)).where(
                Company.batch_id == batch_id,
                Company.status.in_(["Failed", "Partially Completed"]),
            )
        ) or 0

        batch.status = (
            "Completed with Errors"
            if error_count > 0 or failed_count > 0
            else "Completed"
        )
        session.commit()


def get_batch(batch_id: str) -> dict | None:
    """Return a batch summary and the companies linked to it."""
    with SessionLocal() as session:
        batch = session.get(Batch, batch_id)
        if batch is None:
            return None

        companies = session.scalars(
            select(Company)
            .where(Company.batch_id == batch_id)
            .order_by(Company.created_at, Company.id)
        ).all()

        return {
            "batchId": batch.id,
            "status": batch.status,
            "totalReceived": batch.total_received,
            "validCompanies": batch.valid_companies,
            "invalidCompanies": batch.invalid_companies,
            "duplicates": batch.duplicates,
            "companies": [
                {
                    "companyId": company.id,
                    "companyName": company.company_name,
                    "domain": company.domain,
                    "status": company.status,
                }
                for company in companies
            ],
        }


def save_company(batch_id: str, profile: dict) -> None:
    """
    Save the structured company profile, raw enrichment result, and sources.

    A domain may appear only once within the same batch. Database constraints
    provide a final safeguard in addition to validation-service checks.
    """
    company_id = profile.get("companyId") or f"company_{uuid.uuid4().hex[:8]}"
    website_url = (
        profile.get("websiteUrl")
        or profile.get("normalizedWebsite")
        or "unknown"
    )
    domain = _normalize_domain(profile.get("domain") or website_url)

    try:
        with SessionLocal() as session:
            if session.get(Batch, batch_id) is None:
                raise DatabaseSaveError(f"batch not found: {batch_id}")

            if domain is not None:
                duplicate = session.scalar(
                    select(Company.id).where(
                        Company.batch_id == batch_id,
                        Company.domain == domain,
                    )
                )
                if duplicate is not None:
                    raise DatabaseSaveError(
                        f"duplicate domain in batch {batch_id}: {domain}"
                    )

            company = Company(
                id=company_id,
                batch_id=batch_id,
                company_name=profile.get("companyName") or "Unknown",
                website_url=website_url,
                domain=domain,
                linkedin_url=profile.get("linkedinUrl"),
                description=profile.get("description"),
                industry=profile.get("industry"),
                products_services=profile.get("productsServices") or [],
                target_audience=profile.get("targetAudience") or [],
                business_model=profile.get("businessModel"),
                location=profile.get("location"),
                company_size=profile.get("companySize"),
                confidence=profile.get("confidence"),
                status=profile.get("status") or "Completed",
            )
            session.add(company)
            session.flush()

            session.add(
                EnrichmentResult(
                    id=f"result_{uuid.uuid4().hex[:8]}",
                    company_id=company_id,
                    raw_ai_output=dict(profile),
                )
            )

            seen_sources: set[str] = set()
            for source_value in profile.get("sourcesUsed") or []:
                source_text = str(source_value).strip()
                if not source_text or source_text in seen_sources:
                    continue
                seen_sources.add(source_text)
                session.add(
                    Source(
                        id=f"source_{uuid.uuid4().hex[:8]}",
                        company_id=company_id,
                        field_name="profile",
                        source_url=source_text,
                    )
                )

            session.commit()
    except DatabaseSaveError:
        raise
    except IntegrityError as exc:
        raise DatabaseSaveError(
            f"could not save company {company_id}"
        ) from exc


def get_company(company_id: str) -> dict | None:
    """Return one company in the API response format."""
    with SessionLocal() as session:
        company = session.get(Company, company_id)
        if company is None:
            return None

        result = session.scalar(
            select(EnrichmentResult).where(
                EnrichmentResult.company_id == company_id
            )
        )
        sources = session.scalars(
            select(Source)
            .where(Source.company_id == company_id)
            .order_by(Source.extracted_at, Source.id)
        ).all()

        raw_profile = dict(result.raw_ai_output) if result else {}

        return {
            "companyId": company.id,
            "batchId": company.batch_id,
            "companyName": company.company_name,
            "description": company.description or "unknown",
            "industry": company.industry or "unknown",
            "productsServices": company.products_services or [],
            "targetAudience": company.target_audience or [],
            "businessModel": company.business_model or "unknown",
            "confidence": company.confidence or "unknown",
            "missingFields": raw_profile.get("missingFields") or [],
            "sourcesUsed": [source.source_url for source in sources],
            "status": company.status,
        }


def mark_company_failed(batch_id: str, company, error_message: str) -> None:
    """Persist a failed company and a linked error record."""
    company_name = _input_value(company, "companyName", "Unknown") or "Unknown"
    website_url = _input_value(company, "websiteUrl", "unknown") or "unknown"
    linkedin_url = _input_value(company, "linkedinUrl")
    domain = _normalize_domain(website_url)

    try:
        with SessionLocal() as session:
            if session.get(Batch, batch_id) is None:
                raise DatabaseSaveError(f"batch not found: {batch_id}")

            existing_company_id = None
            if domain is not None:
                existing_company_id = session.scalar(
                    select(Company.id).where(
                        Company.batch_id == batch_id,
                        Company.domain == domain,
                    )
                )

            if existing_company_id is None:
                company_id = f"company_{uuid.uuid4().hex[:8]}"
                session.add(
                    Company(
                        id=company_id,
                        batch_id=batch_id,
                        company_name=company_name,
                        website_url=website_url,
                        domain=domain,
                        linkedin_url=linkedin_url,
                        products_services=[],
                        target_audience=[],
                        confidence="unknown",
                        status="Failed",
                    )
                )
                session.flush()
            else:
                company_id = existing_company_id

            session.add(
                ErrorLog(
                    id=f"error_{uuid.uuid4().hex[:8]}",
                    batch_id=batch_id,
                    company_id=company_id,
                    error_type="company_processing_failed",
                    message=error_message,
                    retry_count=0,
                )
            )
            session.commit()
    except DatabaseSaveError:
        raise
    except IntegrityError as exc:
        raise DatabaseSaveError(
            f"could not store company failure for batch {batch_id}"
        ) from exc
