"""
Unit tests for the input validation service — Missions 4 and 5 / SCRUM-5.
"""

from src.services import validation_service


class FakeCompany:
    """Lightweight stand-in for the CompanyInput schema, so these tests
    don't depend on the API layer."""
    def __init__(self, companyName="", websiteUrl="", linkedinUrl=None):
        self.companyName = companyName
        self.websiteUrl = websiteUrl
        self.linkedinUrl = linkedinUrl


def test_rejects_empty_company_list():
    result = validation_service.validate_companies([])
    assert result.total_received == 0
    assert result.valid_companies == []
    assert result.invalid_companies == []
    assert result.duplicates == []


def test_detects_missing_company_name():
    companies = [
        FakeCompany(companyName="", websiteUrl="https://www.example.com"),
        FakeCompany(companyName="   ", websiteUrl="https://www.other.com"),
    ]

    result = validation_service.validate_companies(companies)

    assert len(result.invalid_companies) == 2
    assert result.valid_companies == []
    for invalid in result.invalid_companies:
        assert "Company name is required" in invalid["errors"]


def test_valid_company_passes_through():
    companies = [
        FakeCompany(
            companyName="Example Company",
            websiteUrl="https://www.example.com",
            linkedinUrl="https://www.linkedin.com/company/example",
        )
    ]

    result = validation_service.validate_companies(companies)

    assert len(result.valid_companies) == 1
    assert result.invalid_companies == []
    assert result.duplicates == []
    assert result.total_received == 1


def test_rejects_invalid_website_url():
    companies = [FakeCompany(companyName="Example Company", websiteUrl="not-a-url")]

    result = validation_service.validate_companies(companies)

    assert result.valid_companies == []
    assert len(result.invalid_companies) == 1
    assert "Valid website URL is required" in result.invalid_companies[0]["errors"]


def test_rejects_invalid_linkedin_url():
    companies = [
        FakeCompany(
            companyName="Example Company",
            websiteUrl="https://www.example.com",
            linkedinUrl="https://www.notlinkedin.com/company/example",
        )
    ]

    result = validation_service.validate_companies(companies)

    assert result.valid_companies == []
    assert len(result.invalid_companies) == 1
    assert "Invalid LinkedIn URL" in result.invalid_companies[0]["errors"]


def test_accepts_valid_linkedin_url_matching_mission_4_example():
    # Regression test: this exact URL from Mission 4's spec previously
    # failed validation due to a domain-matching bug. Locking it in here
    # so it can't silently regress.
    companies = [
        FakeCompany(
            companyName="Example Company",
            websiteUrl="https://www.example.com",
            linkedinUrl="https://www.linkedin.com/company/example",
        )
    ]

    result = validation_service.validate_companies(companies)

    assert len(result.valid_companies) == 1
    assert result.invalid_companies == []


def test_missing_linkedin_url_is_allowed():
    # linkedinUrl is optional per Mission 4 — its absence should not
    # invalidate an otherwise-valid company.
    companies = [
        FakeCompany(companyName="Example Company", websiteUrl="https://www.example.com", linkedinUrl=None)
    ]

    result = validation_service.validate_companies(companies)

    assert len(result.valid_companies) == 1
    assert result.invalid_companies == []


def test_detects_duplicate_by_domain_and_name():
    companies = [
        FakeCompany(companyName="Example Company", websiteUrl="https://www.example.com"),
        FakeCompany(companyName="Example Company", websiteUrl="https://www.example.com"),
    ]

    result = validation_service.validate_companies(companies)

    assert len(result.valid_companies) == 1
    assert len(result.duplicates) == 1
    assert result.duplicates[0]["reason"] == "Duplicate company name or domain"


def test_detects_duplicate_by_domain_only_different_name():
    # Current implementation flags a match on EITHER name OR domain as a
    # duplicate (not requiring both to match). This test locks in that
    # behavior — see team discussion on whether OR vs AND is intended.
    companies = [
        FakeCompany(companyName="Example Company", websiteUrl="https://www.example.com"),
        FakeCompany(companyName="Totally Different Name", websiteUrl="https://www.example.com/"),
    ]

    result = validation_service.validate_companies(companies)

    assert len(result.valid_companies) == 1
    assert len(result.duplicates) == 1


def test_invalid_companies_do_not_block_valid_ones_in_same_batch():
    companies = [
        FakeCompany(companyName="", websiteUrl="https://www.example.com"),  # invalid
        FakeCompany(companyName="Good Company", websiteUrl="https://www.good.com"),  # valid
    ]

    result = validation_service.validate_companies(companies)

    assert len(result.valid_companies) == 1
    assert result.valid_companies[0].companyName == "Good Company"
    assert len(result.invalid_companies) == 1
    assert result.total_received == 2


def test_is_valid_website_url_accepts_https():
    assert validation_service.is_valid_website_url("https://www.example.com") is True


def test_is_valid_website_url_rejects_missing_scheme():
    assert validation_service.is_valid_website_url("www.example.com") is False


def test_is_valid_linkedin_url_accepts_company_profile():
    assert validation_service.is_valid_linkedin_url("https://www.linkedin.com/company/example") is True


def test_is_valid_linkedin_url_rejects_non_linkedin_domain():
    assert validation_service.is_valid_linkedin_url("https://www.notlinkedin.com/company/example") is False


def test_is_valid_linkedin_url_rejects_non_company_path():
    # e.g. a personal profile URL rather than a company page
    assert validation_service.is_valid_linkedin_url("https://www.linkedin.com/in/someone") is False 