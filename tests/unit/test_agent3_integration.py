"""
Tests for the Agent 3 integration service — Mission 10 / SCRUM-10.
Mocks httpx so no real network call is made.
"""

import pytest
import httpx
from unittest.mock import patch, MagicMock

from src.services import agent3_integration
from src.core.errors import Agent3IntegrationError


def _mock_response(json_data, status_code=200):
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=response
        )
    return response


@patch("src.services.agent3_integration.httpx.post")
def test_trigger_scan_returns_data_on_success(mock_post):
    mock_post.return_value = _mock_response({
        "companyId": "company_123",
        "scanStatus": "Completed",
        "extractedData": {"productsServices": ["CRM"]},
    })

    result = agent3_integration.trigger_scan("company_123", "https://example.com")

    assert result["scanStatus"] == "Completed"
    assert result["companyId"] == "company_123"


@patch("src.services.agent3_integration.httpx.post")
def test_trigger_scan_sends_correct_payload(mock_post):
    mock_post.return_value = _mock_response({"companyId": "company_123", "scanStatus": "Completed"})

    agent3_integration.trigger_scan("company_123", "https://example.com")

    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["json"] == {"companyId": "company_123", "websiteUrl": "https://example.com"}


@patch("src.services.agent3_integration.httpx.post")
def test_trigger_scan_raises_on_timeout(mock_post):
    mock_post.side_effect = httpx.TimeoutException("simulated timeout")

    with pytest.raises(Agent3IntegrationError):
        agent3_integration.trigger_scan("company_123", "https://example.com")


@patch("src.services.agent3_integration.httpx.post")
def test_trigger_scan_raises_on_connection_error(mock_post):
    mock_post.side_effect = httpx.ConnectError("simulated connection failure")

    with pytest.raises(Agent3IntegrationError):
        agent3_integration.trigger_scan("company_123", "https://example.com")


@patch("src.services.agent3_integration.httpx.post")
def test_trigger_scan_raises_on_bad_status_code(mock_post):
    mock_post.return_value = _mock_response({"error": "internal error"}, status_code=500)

    with pytest.raises(Agent3IntegrationError):
        agent3_integration.trigger_scan("company_123", "https://example.com")


@patch("src.services.agent3_integration.httpx.post")
def test_trigger_scan_raises_on_non_json_response(mock_post):
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.raise_for_status.return_value = None
    response.json.side_effect = ValueError("not json")
    mock_post.return_value = response

    with pytest.raises(Agent3IntegrationError):
        agent3_integration.trigger_scan("company_123", "https://example.com")


@patch("src.services.agent3_integration.httpx.post")
def test_trigger_scan_raises_on_missing_scan_status_field(mock_post):
    mock_post.return_value = _mock_response({"companyId": "company_123"})  # scanStatus missing

    with pytest.raises(Agent3IntegrationError):
        agent3_integration.trigger_scan("company_123", "https://example.com")