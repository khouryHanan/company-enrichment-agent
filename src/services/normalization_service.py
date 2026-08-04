"""
URL Normalization Service — Mission 6.

Cleans and standardizes website and LinkedIn URLs into a consistent format.
"""

from .validation_service import extract_domain


def normalize_website_url(raw_url: str | None) -> dict | None:
    """
    Normalize a website URL and extract its domain.

    Returns:
        {"normalizedWebsite": str, "domain": str}
        or None when the input is empty.
    """
    if raw_url is None:
        return None

    normalized_url = raw_url.strip().rstrip("/")

    if not normalized_url:
        return None

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