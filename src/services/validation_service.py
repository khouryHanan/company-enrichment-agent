"""
Input Validation Service — Missions 4 and 5.

Validates company name, website URL, and LinkedIn URL formats.
Detects missing fields, invalid records, and duplicates.
Invalid companies must not stop the batch.
"""

from dataclasses import dataclass


@dataclass
class ValidationResult:
    valid_companies: list
    invalid_companies: list
    duplicates: list
    total_received: int


def validate_companies(companies: list) -> ValidationResult:
    """
    Splits incoming companies into valid / invalid / duplicate groups.

    TODO:
      - reject empty company name
      - validate websiteUrl format
      - validate linkedinUrl format if present
      - detect duplicates by domain + company name
    """
    raise NotImplementedError


def is_valid_website_url(url: str) -> bool:
    raise NotImplementedError


def is_valid_linkedin_url(url: str) -> bool:
    raise NotImplementedError
