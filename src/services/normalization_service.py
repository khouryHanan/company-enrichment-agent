"""
URL Normalization Service — Mission 6.

Cleans and standardizes website and LinkedIn URLs into a consistent format.
"""

from src.core.errors import InvalidInputError

from .validation_service import extract_domain


def normalize_website_url(raw_url: str | None) -> dict:
    """
    Normalize a website URL and extract its domain.

    Returns: {"normalizedWebsite": str, "domain": str}

    Raises InvalidInputError (permanent, not retryable) when the input
    is empty — batch_service catches it and logs the failure against
    the normalization stage, keeping the error traceable to the step
    that actually rejected the company.
    """
    if raw_url is None or not raw_url.strip():
        raise InvalidInputError("Empty website URL")

    normalized_url = raw_url.strip().rstrip("/")

    return {
        "normalizedWebsite": normalized_url,
        "domain": extract_domain(normalized_url),
    }


def normalize_linkedin_url(raw_url: str | None) -> str | None:
    """
    Return a cleaned LinkedIn company URL,
    or None when the input is empty.
    """
    if raw_url is None:
        return None

    normalized_url = raw_url.strip().rstrip("/")

    if not normalized_url:
        return None

    return normalized_url