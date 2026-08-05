"""
API tests — Mission 4 / SCRUM-4.
Covers structural validation of the bulk enrichment input.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app
from tests.sample_data import (
    EMPTY_LIST_REQUEST,
    MISSING_COMPANY_NAME_REQUEST,
    MISSING_WEBSITE_URL_REQUEST,
    BLANK_COMPANY_NAME_REQUEST,
    NOT_A_LIST_REQUEST,
    MISSING_COMPANIES_KEY_REQUEST,
)

client = TestClient(app)

ENDPOINT = "/api/agents/agent1/bulk-enrichment"


def test_rejects_empty_companies_list():
    response = client.post(ENDPOINT, json=EMPTY_LIST_REQUEST)
    assert response.status_code == 400
    assert "companies list cannot be empty" in str(response.json())


def test_rejects_missing_company_name():
    response = client.post(ENDPOINT, json=MISSING_COMPANY_NAME_REQUEST)
    assert response.status_code == 400


def test_rejects_missing_website_url():
    response = client.post(ENDPOINT, json=MISSING_WEBSITE_URL_REQUEST)
    assert response.status_code == 400


def test_rejects_blank_company_name():
    response = client.post(ENDPOINT, json=BLANK_COMPANY_NAME_REQUEST)
    assert response.status_code == 400


def test_rejects_companies_not_a_list():
    response = client.post(ENDPOINT, json=NOT_A_LIST_REQUEST)
    assert response.status_code == 400


def test_rejects_missing_companies_key():
    response = client.post(ENDPOINT, json=MISSING_COMPANIES_KEY_REQUEST)
    assert response.status_code == 400


def test_error_response_is_readable_not_a_raw_traceback():
    response = client.post(ENDPOINT, json=EMPTY_LIST_REQUEST)
    body = response.json()
    assert "detail" in body
    assert "errors" in body
    assert isinstance(body["errors"], list)


@patch("src.services.batch_service.start_batch")
def test_accepts_valid_request_and_calls_batch_service(mock_start_batch):
    mock_start_batch.return_value = {
        "batchId": "batch_test123",
        "status": "Running",
        "totalReceived": 2,
        "validCompanies": 2,
        "invalidCompanies": 0,
        "duplicates": 0,
    }

    valid_request = {
        "companies": [
            {"companyName": "Example Company", "websiteUrl": "https://www.example.com"},
            {"companyName": "Another Company", "websiteUrl": "https://www.another.com"},
        ]
    }
    response = client.post(ENDPOINT, json=valid_request)

    assert response.status_code == 200
    assert response.json()["batchId"] == "batch_test123"
    mock_start_batch.assert_called_once()


def test_linkedin_url_is_optional():
    with patch("src.services.batch_service.start_batch") as mock_start_batch:
        mock_start_batch.return_value = {
            "batchId": "batch_test456",
            "status": "Running",
            "totalReceived": 1,
            "validCompanies": 1,
            "invalidCompanies": 0,
            "duplicates": 0,
        }
        request_without_linkedin = {
            "companies": [{"companyName": "Example Company", "websiteUrl": "https://www.example.com"}]
        }
        response = client.post(ENDPOINT, json=request_without_linkedin)
        assert response.status_code == 200


@patch("src.api.routes.batch_service.start_batch")
def test_import_endpoint_accepts_eyejee_export(mock_start_batch):
    mock_start_batch.return_value = {
        "batchId": "batch_1", "status": "Completed", "totalReceived": 1,
        "validCompanies": 1, "invalidCompanies": 0, "duplicates": 0,
    }

    response = client.post(
        "/api/agents/agent1/bulk-enrichment/import",
        json=[{
            "data_companies": "LinkTrust",
            "website": "https://linktrust.com",
            "Linkedin_url": "linkedin.com/company/linktrust-systems-inc-",
        }],
    )

    assert response.status_code == 200
    submitted = mock_start_batch.call_args[0][0]
    assert submitted[0].companyName == "LinkTrust"
    # The bare LinkedIn URL must reach the batch already schemed, or
    # validation would reject the company.
    assert submitted[0].linkedinUrl == "https://linkedin.com/company/linktrust-systems-inc-"


def test_import_endpoint_rejects_export_with_no_usable_rows():
    response = client.post(
        "/api/agents/agent1/bulk-enrichment/import",
        json=[{"Keyword": "Marketing", "Loc": "united states"}],
    )

    assert response.status_code == 400
    assert "no usable companies" in response.json()["detail"]
