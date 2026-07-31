"""
Input Validation Service — Missions 4 and 5.

Validates company name, website URL, and LinkedIn URL formats.
Detects missing fields, invalid records, and duplicates.
Invalid companies must not stop the batch.
"""

from dataclasses import dataclass
from urllib.parse import urlparse

from src.core import logging as log


@dataclass
class ValidationResult:
    valid_companies: list
    invalid_companies: list
    duplicates: list
    total_received: int


def validate_companies(companies: list) -> ValidationResult:
    # Validation runs before the batch record exists, so these logs carry
    # company names instead of a batch_id; batch_service logs the batch_id
    # against the same counts right after via batch_started.
    log.info("validation_started", total=len(companies))

    valid_companies = []
    invalid_companies = []
    duplicates = []

    seen_names = set()
    seen_domains = set()

    for company in companies:
        errors = []

        company_name = company.companyName
        website_url = company.websiteUrl
        linkedin_url = company.linkedinUrl

        log.info("company_validation_started", company_name=company_name or "unknown")

        if not company_name or not company_name.strip():
            errors.append("Company name is required")

        if not website_url or not is_valid_website_url(website_url):
            errors.append("Valid website URL is required")

        if linkedin_url and not is_valid_linkedin_url(linkedin_url):
            errors.append("Invalid LinkedIn URL")

        if errors:
            log.error("company_validation_failed", company_name=company_name or "unknown", errors="; ".join(errors))
            invalid_companies.append({
                "company": company,
                "errors": errors
            })
            continue

        normalized_name = company_name.strip().lower()
        domain = extract_domain(website_url)

        if normalized_name in seen_names or domain in seen_domains:
            log.info("company_duplicate_skipped", company_name=company_name, domain=domain)
            duplicates.append({
                "company": company,
                "reason": "Duplicate company name or domain"
            })
            continue

        seen_names.add(normalized_name)
        seen_domains.add(domain)
        valid_companies.append(company)

    log.info(
        "validation_completed",
        valid=len(valid_companies),
        invalid=len(invalid_companies),
        duplicates=len(duplicates),
    )

    return ValidationResult(
        valid_companies=valid_companies,
        invalid_companies=invalid_companies,
        duplicates=duplicates,
        total_received=len(companies)
    )


def is_valid_website_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def is_valid_linkedin_url(url: str) -> bool:
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return False

    domain = parsed.netloc.lower()
    return domain in ("linkedin.com", "www.linkedin.com") and "/company/" in parsed.path


def extract_domain(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain
