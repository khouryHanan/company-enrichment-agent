"""Unit tests for the Agent 1 database repository."""

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.core.errors import DatabaseSaveError
from src.db import repository
from src.db.models import Base, Company, EnrichmentResult, ErrorLog, Source


@pytest.fixture()
def test_session_factory(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(repository, "SessionLocal", factory)

    yield factory

    Base.metadata.drop_all(engine)
    engine.dispose()


def _create_batch(batch_id: str = "batch_test") -> None:
    validation = SimpleNamespace(
        total_received=1,
        valid_companies=["valid"],
        invalid_companies=[],
        duplicates=[],
    )
    repository.create_batch(batch_id, "Running", validation)


def _profile(company_id: str = "company_1") -> dict:
    return {
        "companyId": company_id,
        "companyName": "Example Company",
        "websiteUrl": "https://www.example.com",
        "domain": "example.com",
        "linkedinUrl": "https://www.linkedin.com/company/example",
        "description": "Example description",
        "industry": "SaaS",
        "productsServices": ["CRM"],
        "targetAudience": ["Small businesses"],
        "businessModel": "Subscription",
        "location": "Haifa",
        "companySize": "11-50",
        "confidence": "high",
        "missingFields": [],
        "sourcesUsed": ["https://www.example.com/about"],
        "status": "Completed",
    }


def test_saves_company_with_batch_result_and_source(test_session_factory):
    _create_batch()
    repository.save_company("batch_test", _profile())

    batch = repository.get_batch("batch_test")
    company = repository.get_company("company_1")

    assert batch is not None
    assert batch["companies"][0]["companyId"] == "company_1"
    assert company is not None
    assert company["batchId"] == "batch_test"
    assert company["industry"] == "SaaS"
    assert company["productsServices"] == ["CRM"]
    assert company["sourcesUsed"] == ["https://www.example.com/about"]

    with test_session_factory() as session:
        assert session.scalar(select(func.count(Company.id))) == 1
        assert session.scalar(select(func.count(EnrichmentResult.id))) == 1
        assert session.scalar(select(func.count(Source.id))) == 1


def test_duplicate_domain_in_same_batch_is_rejected(test_session_factory):
    _create_batch()
    repository.save_company("batch_test", _profile("company_1"))

    duplicate = _profile("company_2")
    duplicate["domain"] = "www.example.com"

    with pytest.raises(DatabaseSaveError, match="duplicate domain"):
        repository.save_company("batch_test", duplicate)

    with test_session_factory() as session:
        assert session.scalar(select(func.count(Company.id))) == 1


def test_same_domain_is_allowed_in_different_batches(test_session_factory):
    _create_batch("batch_1")
    _create_batch("batch_2")

    repository.save_company("batch_1", _profile("company_1"))
    repository.save_company("batch_2", _profile("company_2"))

    with test_session_factory() as session:
        assert session.scalar(select(func.count(Company.id))) == 2


def test_failed_company_is_logged_and_batch_finishes_with_errors(
    test_session_factory,
):
    _create_batch()
    company_input = SimpleNamespace(
        companyName="Broken Company",
        websiteUrl="https://broken.example",
        linkedinUrl=None,
    )

    repository.mark_company_failed(
        "batch_test",
        company_input,
        "enrichment failed",
    )
    repository.finalize_batch("batch_test")

    batch = repository.get_batch("batch_test")
    assert batch is not None
    assert batch["status"] == "Completed with Errors"
    assert batch["companies"][0]["status"] == "Failed"

    with test_session_factory() as session:
        error = session.scalar(select(ErrorLog))
        assert error is not None
        assert error.batch_id == "batch_test"
        assert error.company_id is not None
        assert error.message == "enrichment failed"
