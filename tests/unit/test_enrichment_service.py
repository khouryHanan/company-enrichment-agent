"""
Unit tests for the AI enrichment service — Mission 9 / SCRUM-9.
Mocks the LangChain model call so tests don't hit a real provider.
"""

import pytest
from unittest.mock import patch

from src.services import enrichment_service
from src.services.enrichment_service import CompanyProfile
from src.core.errors import AIResponseError


VALID_PROFILE = CompanyProfile(
    companyName="Example Company",
    description="A short factual company summary based on available information.",
    industry="SaaS",
    productsServices=["CRM", "Workflow automation"],
    targetAudience=["Sales teams", "Small businesses"],
    businessModel="Subscription",
    location="Tel Aviv, Israel",
    companySize="51-200",
    foundedYear="2015",
    headquarters="Tel Aviv, Israel",
    keyCompetitors=["Rival Co"],
    techStack=["Python", "PostgreSQL"],
    keyContacts=["Jane Doe — CEO"],
    confidence="medium",
    missingFields=[],
    sourcesUsed=["company_name", "website_url"],
)


def test_company_profile_rejects_invalid_confidence_value():
    # Pydantic's Literal type enforces this at construction time —
    # this locks in that the schema itself catches bad values, not just
    # our own hand-written validation.
    with pytest.raises(Exception):
        CompanyProfile(
            companyName="Example",
            description="desc",
            industry="unknown",
            productsServices=[],
            targetAudience=[],
            businessModel="unknown",
            confidence="very sure",  # invalid — not low/medium/high
            missingFields=[],
            sourcesUsed=[],
        )


def test_company_profile_rejects_missing_required_field():
    with pytest.raises(Exception):
        CompanyProfile(
            companyName="Example",
            description="desc",
            industry="unknown",
            productsServices=[],
            targetAudience=[],
            businessModel="unknown",
            # confidence intentionally omitted
            missingFields=[],
            sourcesUsed=[],
        )


def test_missing_data_marked_unknown_not_invented():
    # The prompt instructs the model to use "unknown"/"not_available"
    # rather than inventing values. This is a contract enforced by the
    # prompt, not the schema — this test just documents/locks that a
    # sparse-but-valid profile is accepted as-is, nothing auto-fills it.
    sparse = CompanyProfile(
        companyName="Example Company",
        description="unknown",
        industry="unknown",
        productsServices=[],
        targetAudience=[],
        businessModel="not_available",
        location="unknown",
        companySize="unknown",
        foundedYear="unknown",
        headquarters="unknown",
        keyCompetitors=[],
        techStack=[],
        keyContacts=[],
        confidence="low",
        missingFields=["industry", "businessModel", "productsServices", "targetAudience"],
        sourcesUsed=["company_name"],
    )
    assert sparse.industry == "unknown"
    assert sparse.businessModel == "not_available"
    assert sparse.keyContacts == []


class FakeCompany:
    companyName = "Example Company"
    websiteUrl = "https://www.example.com"
    linkedinUrl = "https://www.linkedin.com/company/example"


@patch("src.services.enrichment_service._call_model")
def test_enrich_company_returns_completed_status_on_success(mock_call):
    mock_call.return_value = VALID_PROFILE

    result = enrichment_service.enrich_company(
        FakeCompany(), {"normalizedWebsite": "https://www.example.com", "domain": "example.com"}
    )

    assert result["status"] == "Completed"
    assert result["confidence"] == "medium"
    assert result["companyId"].startswith("company_")
    assert result["companyName"] == "Example Company"


@patch("src.services.enrichment_service._call_model")
def test_enrich_company_retries_once_then_raises(mock_call):
    mock_call.side_effect = AIResponseError("simulated malformed output")

    with pytest.raises(AIResponseError):
        enrichment_service.enrich_company(
            FakeCompany(), {"normalizedWebsite": "https://www.example.com", "domain": "example.com"}
        )

    # initial attempt + 1 retry per Mission 13's retry policy
    assert mock_call.call_count == 2


@patch("src.services.enrichment_service._structured_llm")
def test_call_model_wraps_provider_errors_as_ai_response_error(mock_structured_llm):
    # Simulates the underlying provider/LangChain raising anything (bad
    # JSON, a validation error, a network hiccup mid-parse) — our own
    # code should normalize all of that to AIResponseError so callers
    # only ever need to catch one exception type.
    mock_structured_llm.invoke.side_effect = ValueError("simulated provider failure")

    with pytest.raises(AIResponseError):
        enrichment_service._call_model("some prompt")