"""
Input Validation Service — Missions 4 and 5.

Validates company name, website URL, and LinkedIn URL formats.
Detects missing fields, invalid records, and duplicates.
Invalid companies must not stop the batch.
"""

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class ValidationResult:
    valid_companies: list
    invalid_companies: list
    duplicates: list
    total_received: int


def validate_companies(companies: list) -> ValidationResult:
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

        if not company_name or not company_name.strip():
            errors.append("Company name is required")

        if not website_url or not is_valid_website_url(website_url):
            errors.append("Valid website URL is required")

        if linkedin_url and not is_valid_linkedin_url(linkedin_url):
            errors.append("Invalid LinkedIn URL")

        if errors:
            invalid_companies.append({
                "company": company,
                "errors": errors
            })
            continue

        normalized_name = company_name.strip().lower()
        domain = extract_domain(website_url)

        if normalized_name in seen_names or domain in seen_domains:
            duplicates.append({
                "company": company,
                "reason": "Duplicate company name or domain"
            })
            continue

        seen_names.add(normalized_name)
        seen_domains.add(domain)
        valid_companies.append(company)

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