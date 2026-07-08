"""
Database Service — read/write functions used by every other service.
Keeps raw SQL/ORM calls out of the service layer.
"""
from sqlalchemy import select

from src.db.database import SessionLocal
from src.db.models import Batch, ErrorLog

def create_batch(batch_id: str, status: str, validation) -> None:
    with SessionLocal() as session:
        batch = Batch(
            id=batch_id,
            status=status,
            total_received=validation.total_received,
            valid_companies=len(validation.valid_companies),
            invalid_companies=len(validation.invalid_companies),
            duplicates=len(validation.duplicates),
        )

        session.add(batch)
        session.commit()


def finalize_batch(batch_id: str) -> None:
    with SessionLocal() as session:
        batch = session.get(Batch, batch_id)

        if batch is None:
            return

        error_id = session.scalar(
            select(ErrorLog.id)
            .where(ErrorLog.batch_id == batch_id)
            .limit(1)
        )

        if error_id is not None:
            batch.status = "Completed with Errors"
        else:
            batch.status = "Completed"

        session.commit()


def get_batch(batch_id: str) -> dict | None:
    with SessionLocal() as session:
        batch = session.get(Batch, batch_id)

        if batch is None:
            return None

        return {
            "batchId": batch.id,
            "status": batch.status,
            "totalReceived": batch.total_received,
            "validCompanies": batch.valid_companies,
            "invalidCompanies": batch.invalid_companies,
            "duplicates": batch.duplicates,
        }

def save_company(batch_id: str, profile: dict) -> None:
    raise NotImplementedError


def get_company(company_id: str) -> dict | None:
    raise NotImplementedError


def mark_company_failed(batch_id: str, company, error_message: str) -> None:
    raise NotImplementedError
