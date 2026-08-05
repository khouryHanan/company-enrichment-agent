"""
Import Service — adapts an EYEjee platform export into Agent 1's input
contract.

The platform exports company lists with its own field names, and its
URLs are not always canonical: LinkedIn URLs in particular arrive
without a scheme ("linkedin.com/company/acme"), which our validation
correctly rejects as a malformed URL. Absorbing those quirks here — at
the boundary — keeps validation_service strict for everyone else
instead of loosening a shared contract for one producer's formatting.

Export row (only the fields we consume):
    {"data_companies": "LinkTrust",
     "website": "https://linktrust.com",
     "Linkedin_url": "linkedin.com/company/linktrust-systems-inc-",
     "Loc": "united states", "Size": "11-50", "Keyword": "Marketing", ...}
"""

# Export field -> our field. Kept as a table so a producer-side rename is
# a one-line change here rather than a hunt through the mapping code.
NAME_FIELD = "data_companies"
WEBSITE_FIELD = "website"
LINKEDIN_FIELD = "Linkedin_url"
# Facts the export already establishes. Carried through as ground truth
# rather than left for the model to re-derive — it returned "unknown"
# for sizes this file states outright.
LOCATION_FIELD = "Loc"
SIZE_FIELD = "Size"


def _with_scheme(url: str | None) -> str | None:
    """Prefix https:// when a URL arrives bare. Returns None for empty
    input so an absent LinkedIn URL stays absent rather than becoming
    the string "https://"."""
    if url is None:
        return None

    cleaned = url.strip()
    if not cleaned:
        return None
    if "://" in cleaned:
        return cleaned
    return f"https://{cleaned}"


def from_eyejee_export(rows: list[dict]) -> list[dict]:
    """
    Maps export rows to Agent 1 company inputs (companyName, websiteUrl,
    linkedinUrl). Rows missing a name or website are skipped rather than
    passed on as blanks: the batch's invalid/duplicate counts should
    describe companies that were really submitted, not artifacts of a
    malformed export. Structural validation of what survives is still
    the API layer's job.
    """
    companies = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        name = (row.get(NAME_FIELD) or "").strip()
        website = _with_scheme(row.get(WEBSITE_FIELD))
        if not name or not website:
            continue

        company = {"companyName": name, "websiteUrl": website}

        linkedin = _with_scheme(row.get(LINKEDIN_FIELD))
        if linkedin:
            company["linkedinUrl"] = linkedin

        for export_field, our_field in ((LOCATION_FIELD, "location"), (SIZE_FIELD, "companySize")):
            value = (row.get(export_field) or "").strip()
            if value:
                company[our_field] = value

        companies.append(company)

    return companies
