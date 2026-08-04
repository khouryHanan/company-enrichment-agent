"""
API tests — Mission 12 / SCRUM-12.
Covers the GET endpoints: batch status and company result retrieval.
(The POST endpoint's structural validation is covered separately in
tests/api/test_bulk_input.py, SCRUM-4.)
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


FAKE_BATCH = {
    "batchId": "batch_abc123",
    "status": "Completed",
    "totalReceived": 3,
    "validCompanies": 2,
    "invalidCompanies": 1,
    "duplicates": 0,
}

FAKE_COMPANY = {
    "companyId": "company_xyz789",
    "batchId": "batch_abc123",
    "companyName": "Example Company",
    "description": "A short factual company summary.",
    "industry": "SaaS",
    "productsServices": ["CRM", "Workflow automation"],
    "targetAudience": ["Sales teams", "Small businesses"],
    "businessModel": "Subscription",
    "confidence": "medium",
    "missingFields": ["location"],
    "sourcesUsed": ["company_name", "website_url"],
    "status": "Completed",
}


@patch("src.api.routes.repository.get_batch")
def test_get_batch_status_returns_batch_when_found(mock_get_batch):
    mock_get_batch.return_value = FAKE_BATCH

    response = client.get("/api/agents/agent1/bulk-enrichment/batch_abc123")

    assert response.status_code == 200
    assert response.json()["batchId"] == "batch_abc123"
    assert response.json()["status"] == "Completed"


@patch("src.api.routes.repository.get_batch")
def test_get_batch_status_returns_404_when_not_found(mock_get_batch):
    mock_get_batch.return_value = None

    response = client.get("/api/agents/agent1/bulk-enrichment/does-not-exist")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@patch("src.api.routes.repository.get_company")
def test_get_company_result_returns_company_when_found(mock_get_company):
    mock_get_company.return_value = FAKE_COMPANY

    response = client.get("/api/companies/company_xyz789")

    assert response.status_code == 200
    body = response.json()
    assert body["companyId"] == "company_xyz789"
    assert body["confidence"] == "medium"
    assert body["productsServices"] == ["CRM", "Workflow automation"]


@patch("src.api.routes.repository.get_company")
def test_get_company_result_returns_404_when_not_found(mock_get_company):
    mock_get_company.return_value = None

    response = client.get("/api/companies/does-not-exist")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@patch("src.api.routes.repository.get_company")
def test_get_company_result_matches_response_schema(mock_get_company):
    # Confirms every field CompanyEnrichmentResult requires is actually
    # present in what the endpoint returns — catches schema drift early.
    mock_get_company.return_value = FAKE_COMPANY

    response = client.get("/api/companies/company_xyz789")

    body = response.json()
    required_fields = {
        "companyId", "batchId", "companyName", "description", "industry",
        "productsServices", "targetAudience", "businessModel", "confidence",
        "missingFields", "sourcesUsed", "status",
    }
    assert required_fields.issubset(body.keys())

@patch("src.api.routes.repository.get_companies_for_batch")
@patch("src.api.routes.repository.get_batch")
def test_get_batch_companies_returns_all_companies(mock_get_batch, mock_get_companies):
    mock_get_batch.return_value = FAKE_BATCH
    mock_get_companies.return_value = [dict(FAKE_COMPANY), dict(FAKE_COMPANY, companyId="company_2", status="Failed")]

    response = client.get("/api/agents/agent1/bulk-enrichment/batch_abc123/companies")

    assert response.status_code == 200
    body = response.json()
    assert body["batchId"] == "batch_abc123"
    assert len(body["companies"]) == 2
    assert body["companies"][1]["status"] == "Failed"


@patch("src.api.routes.repository.get_batch")
def test_get_batch_companies_404_when_batch_missing(mock_get_batch):
    mock_get_batch.return_value = None

    response = client.get("/api/agents/agent1/bulk-enrichment/nope/companies")

    assert response.status_code == 404
