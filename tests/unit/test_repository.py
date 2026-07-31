"""
Unit tests for the database service — Mission 8 / SCRUM-8, extended for
Mission 11 / SCRUM-11's source-reference persistence.
Uses an in-memory SQLite database so tests don't touch the real DB file.
"""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from src.db.models import Base
from src.db import repository as repo


class FakeValidationResult:
    def __init__(self, valid=0, invalid=None, duplicates=None, total=0):
        self.valid_companies = [object()] * valid
        self.invalid_companies = invalid or []
        self.duplicates = duplicates or []
        self.total_received = total


class FakeCompany:
    def __init__(self, companyName="Example", websiteUrl="https://example.com", linkedinUrl=None):
        self.companyName = companyName
        self.websiteUrl = websiteUrl
        self.linkedinUrl = linkedinUrl


@pytest.fixture(autouse=True)
def use_in_memory_db(monkeypatch):
    """Points repository.py's SessionLocal at an isolated in-memory DB for
    every test, so tests never touch the real sqlite file on disk."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(bind=engine)
    monkeypatch.setattr(repo, "SessionLocal", TestSessionLocal)
    yield


def test_create_batch_stores_counts_and_returns_generated_id():
    validation = FakeValidationResult(valid=2, invalid=[{"company": FakeCompany(), "errors": ["bad"]}], total=3)
    batch_id = repo.create_batch(status="Running", validation=validation)

    assert batch_id  # a real ID was generated
    batch = repo.get_batch(batch_id)
    assert batch["totalReceived"] == 3
    assert batch["validCompanies"] == 2
    assert batch["invalidCompanies"] == 1


def test_get_batch_returns_none_when_missing():
    assert repo.get_batch("does-not-exist") is None


def test_save_company_and_retrieve():
    validation = FakeValidationResult(valid=1, total=1)
    batch_id = repo.create_batch(status="Running", validation=validation)

    profile = {
        "companyId": "company_abc",
        "companyName": "Example Company",
        "domain": "example.com",
        "description": "A test company.",
        "industry": "SaaS",
        "productsServices": ["CRM"],
        "targetAudience": ["Sales teams"],
        "businessModel": "Subscription",
        "confidence": "medium",
        "missingFields": ["location"],
        "sourcesUsed": ["company_name"],
        "status": "Completed",
    }
    repo.save_company(batch_id, profile)

    company = repo.get_company("company_abc")
    assert company["companyName"] == "Example Company"
    assert company["status"] == "Completed"
    assert company["confidence"] == "medium"


def test_get_company_returns_none_when_missing():
    assert repo.get_company("does-not-exist") is None


def test_mark_company_failed_does_not_raise():
    validation = FakeValidationResult(valid=1, total=1)
    batch_id = repo.create_batch(status="Running", validation=validation)

    # Should not raise even though this company never finished processing
    repo.mark_company_failed(batch_id, FakeCompany(companyName="Broken Co"), "AI response error")


def test_finalize_batch_marks_completed_when_all_companies_completed():
    validation = FakeValidationResult(valid=1, total=1)
    batch_id = repo.create_batch(status="Running", validation=validation)
    repo.save_company(batch_id, {
        "companyId": "company_x",
        "companyName": "Co X",
        "domain": "cox.com",
        "status": "Completed",
    })

    repo.finalize_batch(batch_id)

    batch = repo.get_batch(batch_id)
    assert batch["status"] == "Completed"


def test_finalize_batch_marks_completed_with_errors_when_mixed():
    validation = FakeValidationResult(valid=2, total=2)
    batch_id = repo.create_batch(status="Running", validation=validation)
    repo.save_company(batch_id, {"companyId": "c1", "companyName": "Co 1", "domain": "co1.com", "status": "Completed"})
    repo.mark_company_failed(batch_id, FakeCompany(companyName="Co 2"), "some error")

    repo.finalize_batch(batch_id)

    batch = repo.get_batch(batch_id)
    assert batch["status"] == "Completed with Errors"


def test_save_company_persists_source_references():
    # Mission 11 / SCRUM-11: confirmed website evidence must be saved
    # with its source URL, traceable per-field.
    validation = FakeValidationResult(valid=1, total=1)
    batch_id = repo.create_batch(status="Running", validation=validation)

    profile = {
        "companyId": "company_with_sources",
        "companyName": "Example Company",
        "domain": "example.com",
        "status": "Completed",
        "sourceReferences": [
            {"field": "productsServices", "url": "https://example.com/products"},
            {"field": "pricingAvailable", "url": "https://example.com/pricing"},
        ],
    }
    repo.save_company(batch_id, profile)

    session = repo.SessionLocal()
    try:
        from src.db.models import Source
        sources = session.query(Source).filter(Source.company_id == "company_with_sources").all()
        assert len(sources) == 2
        fields = {s.field_name for s in sources}
        assert fields == {"productsServices", "pricingAvailable"}
    finally:
        session.close()


def test_save_company_with_no_source_references_saves_none():
    validation = FakeValidationResult(valid=1, total=1)
    batch_id = repo.create_batch(status="Running", validation=validation)

    repo.save_company(batch_id, {
        "companyId": "company_no_sources",
        "companyName": "Example Company",
        "domain": "example2.com",
        "status": "Completed",
    })

    from src.db.models import Source
    session = repo.SessionLocal()
    try:
        sources = session.query(Source).filter(Source.company_id == "company_no_sources").all()
        assert sources == []
    finally:
        session.close()


@patch("src.core.retry.time.sleep")  # skip real backoff delay in tests
def test_save_company_retries_then_raises_on_persistent_operational_error(mock_sleep, monkeypatch):
    # Mission 13: a transient DB failure (e.g. SQLite "database is locked")
    # should be retried, not fail on the first attempt. If it never
    # recovers, it should surface as a clean DatabaseSaveError, not a
    # raw SQLAlchemy exception leaking out of the repository layer.
    validation = FakeValidationResult(valid=1, total=1)
    batch_id = repo.create_batch(status="Running", validation=validation)

    real_session = repo.SessionLocal()
    always_fails_commit = MagicMock(side_effect=OperationalError("stmt", {}, Exception("db is locked")))
    monkeypatch.setattr(real_session, "commit", always_fails_commit)
    monkeypatch.setattr(repo, "SessionLocal", lambda: real_session)

    from src.core.errors import DatabaseSaveError
    with pytest.raises(DatabaseSaveError):
        repo.save_company(batch_id, {
            "companyId": "company_retry_test",
            "companyName": "Example Company",
            "domain": "retrytest.com",
            "status": "Completed",
        })

    # Confirms it actually retried (didn't give up after one attempt).
    assert always_fails_commit.call_count > 1