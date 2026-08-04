"""
Tests for batch processing orchestration — Mission 7 / SCRUM-7.

All downstream services (normalization, enrichment, Agent 3, merge,
repository) are mocked here so these tests verify orchestration behavior
in isolation — they don't depend on those services being fully built yet.
"""

from unittest.mock import patch, MagicMock

from src.services import batch_service


class FakeCompany:
    def __init__(self, companyName="Example Company", websiteUrl="https://example.com"):
        self.companyName = companyName
        self.websiteUrl = websiteUrl
        self.linkedinUrl = None


class FakeValidationResult:
    def __init__(self, valid_companies=None, invalid_companies=None, duplicates=None, total=0):
        self.valid_companies = valid_companies or []
        self.invalid_companies = invalid_companies or []
        self.duplicates = duplicates or []
        self.total_received = total


@patch("src.services.batch_service.repository")
@patch("src.services.batch_service.validation_service")
def test_batch_gets_an_id(mock_validation, mock_repo):
    mock_validation.validate_companies.return_value = FakeValidationResult(total=0)
    mock_repo.create_batch.return_value = "batch_abc123"
    mock_repo.get_batch.return_value = {"batchId": "batch_abc123", "status": "Completed"}

    result = batch_service.start_batch([])

    mock_repo.create_batch.assert_called_once()
    assert result["batchId"] == "batch_abc123"


@patch("src.services.batch_service.merge_service")
@patch("src.services.batch_service.agent3_integration")
@patch("src.services.batch_service.enrichment_service")
@patch("src.services.batch_service.normalization_service")
@patch("src.services.batch_service.repository")
@patch("src.services.batch_service.validation_service")
def test_one_failed_company_does_not_stop_the_batch(
    mock_validation, mock_repo, mock_norm, mock_enrich, mock_agent3, mock_merge
):
    good_company = FakeCompany(companyName="Good Co", websiteUrl="https://good.com")
    bad_company = FakeCompany(companyName="Bad Co", websiteUrl="https://bad.com")
    mock_validation.validate_companies.return_value = FakeValidationResult(
        valid_companies=[good_company, bad_company], total=2
    )
    mock_repo.create_batch.return_value = "batch_xyz"
    mock_repo.get_batch.return_value = {"batchId": "batch_xyz", "status": "Completed with Errors"}

    # First company normalizes fine, second raises.
    def normalize_side_effect(url):
        if url == bad_company.websiteUrl:
            raise ValueError("simulated normalization failure")
        return {"normalizedWebsite": url, "domain": "example.com"}

    mock_norm.normalize_website_url.side_effect = normalize_side_effect
    mock_enrich.enrich_company.return_value = {"companyId": "company_1", "companyName": "Good Co", "status": "Completed"}
    mock_agent3.trigger_scan.return_value = {"scanStatus": "Failed"}
    mock_merge.merge_results.return_value = {"companyId": "company_1", "status": "Completed"}

    result = batch_service.start_batch([good_company, bad_company])

    # The batch itself must complete despite one company failing.
    mock_repo.finalize_batch.assert_called_once_with("batch_xyz")
    assert result["batchId"] == "batch_xyz"

    # The bad company should be marked failed, not raise out of start_batch.
    mock_repo.mark_company_failed.assert_called_once()
    call_args = mock_repo.mark_company_failed.call_args
    assert call_args[0][1] is bad_company


@patch("src.services.batch_service.merge_service")
@patch("src.services.batch_service.agent3_integration")
@patch("src.services.batch_service.enrichment_service")
@patch("src.services.batch_service.normalization_service")
@patch("src.services.batch_service.repository")
@patch("src.services.batch_service.validation_service")
def test_agent3_failure_does_not_fail_the_company(
    mock_validation, mock_repo, mock_norm, mock_enrich, mock_agent3, mock_merge
):
    company = FakeCompany()
    mock_validation.validate_companies.return_value = FakeValidationResult(valid_companies=[company], total=1)
    mock_repo.create_batch.return_value = "batch_1"
    mock_repo.get_batch.return_value = {"batchId": "batch_1", "status": "Completed"}
    mock_norm.normalize_website_url.return_value = {"normalizedWebsite": company.websiteUrl, "domain": "example.com"}
    mock_enrich.enrich_company.return_value = {"companyId": "company_1", "companyName": "Example Company", "status": "Completed"}

    # Agent 3 raises entirely (e.g. network timeout).
    mock_agent3.trigger_scan.side_effect = TimeoutError("simulated timeout")

    batch_service.start_batch([company])

    # Company should still be saved (with AI enrichment only), not marked failed.
    mock_repo.save_company.assert_called_once()
    mock_repo.mark_company_failed.assert_not_called()
    saved_profile = mock_repo.save_company.call_args[0][1]
    assert saved_profile["status"] == "Partially Completed"


@patch("src.services.batch_service.merge_service")
@patch("src.services.batch_service.agent3_integration")
@patch("src.services.batch_service.enrichment_service")
@patch("src.services.batch_service.normalization_service")
@patch("src.services.batch_service.repository")
@patch("src.services.batch_service.validation_service")
def test_successful_company_gets_merged_and_saved(
    mock_validation, mock_repo, mock_norm, mock_enrich, mock_agent3, mock_merge
):
    company = FakeCompany()
    mock_validation.validate_companies.return_value = FakeValidationResult(valid_companies=[company], total=1)
    mock_repo.create_batch.return_value = "batch_1"
    mock_repo.get_batch.return_value = {"batchId": "batch_1", "status": "Completed"}
    mock_norm.normalize_website_url.return_value = {"normalizedWebsite": company.websiteUrl, "domain": "example.com"}
    mock_enrich.enrich_company.return_value = {"companyId": "company_1", "companyName": "Example Company", "status": "Completed"}
    mock_agent3.trigger_scan.return_value = {"scanStatus": "Completed", "extractedData": {}}
    mock_merge.merge_results.return_value = {"companyId": "company_1", "status": "Completed", "sourcesUsed": ["website_scan"]}

    batch_service.start_batch([company])

    mock_merge.merge_results.assert_called_once()
    mock_repo.save_company.assert_called_once()
    mock_repo.mark_company_failed.assert_not_called()


@patch("src.services.batch_service.repository")
@patch("src.services.batch_service.validation_service")
def test_batch_summary_can_be_retrieved(mock_validation, mock_repo):
    mock_validation.validate_companies.return_value = FakeValidationResult(total=0)
    mock_repo.create_batch.return_value = "batch_retrieve_me"
    mock_repo.get_batch.return_value = {
        "batchId": "batch_retrieve_me",
        "status": "Completed",
        "totalReceived": 0,
        "validCompanies": 0,
        "invalidCompanies": 0,
        "duplicates": 0,
    }

    result = batch_service.start_batch([])

    mock_repo.get_batch.assert_called_with("batch_retrieve_me")
    assert result["status"] == "Completed"


# --- Read side (query paths behind the GET endpoints) ---------------


@patch("src.services.batch_service.repository")
def test_get_batch_summary_returns_repository_result(mock_repo):
    mock_repo.get_batch.return_value = {"batchId": "batch_1", "status": "Completed"}

    assert batch_service.get_batch_summary("batch_1")["status"] == "Completed"


@patch("src.services.batch_service.repository")
def test_get_batch_companies_returns_none_for_unknown_batch(mock_repo):
    # None (not []) so callers can tell "no such batch" from "a batch
    # that recorded no companies" — the API turns None into a 404.
    mock_repo.get_batch.return_value = None

    assert batch_service.get_batch_companies("nope") is None
    mock_repo.get_companies_for_batch.assert_not_called()


@patch("src.services.batch_service.repository")
def test_get_batch_companies_returns_empty_list_for_batch_with_no_companies(mock_repo):
    mock_repo.get_batch.return_value = {"batchId": "batch_1"}
    mock_repo.get_companies_for_batch.return_value = []

    assert batch_service.get_batch_companies("batch_1") == []


@patch("src.services.batch_service.repository")
def test_get_batch_companies_returns_all_recorded_companies(mock_repo):
    mock_repo.get_batch.return_value = {"batchId": "batch_1"}
    mock_repo.get_companies_for_batch.return_value = [{"companyId": "c1"}, {"companyId": "c2"}]

    assert len(batch_service.get_batch_companies("batch_1")) == 2


@patch("src.services.batch_service.repository")
def test_get_company_profile_returns_none_when_missing(mock_repo):
    mock_repo.get_company.return_value = None

    assert batch_service.get_company_profile("nope") is None
