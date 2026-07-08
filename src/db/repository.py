"""
Database Service — read/write functions used by every other service.
Keeps raw SQL/ORM calls out of the service layer.
"""
from src.db.database import SessionLocal
from src.db.models import Batch

def create_batch(batch_id: str, status: str, validation) -> None:
    raise NotImplementedError


def finalize_batch(batch_id: str) -> None:
    raise NotImplementedError


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
