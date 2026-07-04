"""
URL Normalization Service — Mission 6.

Cleans and standardizes website and LinkedIn URLs into a consistent format.
"""


def normalize_website_url(raw_url: str) -> dict:
    """
    Returns: {"normalizedWebsite": str, "domain": str}

    TODO:
      - strip whitespace
      - remove trailing slashes
      - extract domain
    """
    raise NotImplementedError


def normalize_linkedin_url(raw_url: str | None) -> str | None:
    """
    Returns a cleaned LinkedIn company URL, or None if input was empty.
    """
    raise NotImplementedError
