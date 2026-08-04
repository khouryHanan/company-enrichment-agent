import pytest

from src.core.errors import InvalidInputError
from src.services.normalization_service import (
    normalize_linkedin_url,
    normalize_website_url,
)


def test_normalize_website_url():
    result = normalize_website_url("  https://www.example.com/  ")

    assert result == {
        "normalizedWebsite": "https://www.example.com",
        "domain": "example.com",
    }


def test_normalize_website_url_empty_string():
    with pytest.raises(InvalidInputError):
        normalize_website_url("")


def test_normalize_website_url_whitespace():
    with pytest.raises(InvalidInputError):
        normalize_website_url("   ")


def test_normalize_website_url_none():
    with pytest.raises(InvalidInputError):
        normalize_website_url(None)


def test_normalize_linkedin_url():
    result = normalize_linkedin_url(
        "  https://www.linkedin.com/company/example/  "
    )

    assert result == "https://www.linkedin.com/company/example"


def test_normalize_linkedin_url_empty_string():
    assert normalize_linkedin_url("") is None


def test_normalize_linkedin_url_whitespace():
    assert normalize_linkedin_url("   ") is None


def test_normalize_linkedin_url_none():
    assert normalize_linkedin_url(None) is None