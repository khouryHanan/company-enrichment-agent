"""
Tests for the merge service — Mission 11 / SCRUM-11.
"""

from src.services import merge_service


BASE_ENRICHMENT = {
    "companyId": "company_1",
    "companyName": "Example Company",
    "description": "A SaaS company.",
    "industry": "SaaS",
    "productsServices": ["unknown"],
    "targetAudience": ["Sales teams"],
    "businessModel": "Subscription",
    "confidence": "low",
    "missingFields": ["productsServices", "location"],
    "sourcesUsed": ["company_name", "website_url"],
    "status": "Completed",
}


def test_merge_does_not_mutate_the_original_enrichment_dict():
    scan_result = {"scanStatus": "Completed", "extractedData": {}}
    original = dict(BASE_ENRICHMENT)

    merge_service.merge_results(BASE_ENRICHMENT, scan_result)

    assert BASE_ENRICHMENT == original


def test_website_evidence_overwrites_products_services_and_clears_missing_field():
    scan_result = {
        "scanStatus": "Completed",
        "extractedData": {
            "productsServices": ["CRM", "Workflow automation"],
            "sourceUrls": ["https://example.com/products"],
        },
    }

    merged = merge_service.merge_results(BASE_ENRICHMENT, scan_result)

    assert merged["productsServices"] == ["CRM", "Workflow automation"]
    assert "productsServices" not in merged["missingFields"]
    # location was never addressed by the scan — stays marked missing.
    assert "location" in merged["missingFields"]


def test_no_website_evidence_leaves_ai_fields_untouched():
    scan_result = {"scanStatus": "Completed", "extractedData": {}}

    merged = merge_service.merge_results(BASE_ENRICHMENT, scan_result)

    assert merged["productsServices"] == ["unknown"]
    assert merged["missingFields"] == ["productsServices", "location"]


def test_boolean_evidence_fields_are_recorded_separately_from_ai_fields():
    scan_result = {
        "scanStatus": "Completed",
        "extractedData": {
            "pricingFound": True,
            "blogFound": False,
            "sourceUrls": ["https://example.com/pricing"],
        },
    }

    merged = merge_service.merge_results(BASE_ENRICHMENT, scan_result)

    assert merged["pricingAvailable"] is True
    assert merged["blogPresent"] is False
    # These are website-confirmed facts, not part of the AI's own fields.
    assert "pricingAvailable" not in BASE_ENRICHMENT


def test_source_references_recorded_for_confirmed_evidence_only():
    scan_result = {
        "scanStatus": "Completed",
        "extractedData": {
            "productsServices": ["CRM"],
            "pricingFound": True,
            "blogFound": False,  # confirmed absent — should NOT generate a source reference
            "sourceUrls": ["https://example.com/products", "https://example.com/pricing"],
        },
    }

    merged = merge_service.merge_results(BASE_ENRICHMENT, scan_result)

    fields_with_sources = {ref["field"] for ref in merged["sourceReferences"]}
    assert "productsServices" in fields_with_sources
    assert "pricingAvailable" in fields_with_sources
    assert "blogPresent" not in fields_with_sources


def test_sources_used_includes_website_scan_when_evidence_found():
    scan_result = {
        "scanStatus": "Completed",
        "extractedData": {"productsServices": ["CRM"], "sourceUrls": ["https://example.com"]},
    }

    merged = merge_service.merge_results(BASE_ENRICHMENT, scan_result)

    assert "website_scan" in merged["sourcesUsed"]


def test_sources_used_unchanged_when_no_evidence_found():
    scan_result = {"scanStatus": "Completed", "extractedData": {}}

    merged = merge_service.merge_results(BASE_ENRICHMENT, scan_result)

    assert "website_scan" not in merged["sourcesUsed"]


def test_merged_status_is_completed():
    scan_result = {"scanStatus": "Completed", "extractedData": {"productsServices": ["CRM"]}}

    merged = merge_service.merge_results(BASE_ENRICHMENT, scan_result)

    assert merged["status"] == "Completed"

def test_confirmed_evidence_bumps_confidence_one_level():
    # low -> medium; the AI rated itself before any evidence existed, so
    # confirmed website evidence promotes confidence exactly one level.
    scan_result = {
        "scanStatus": "Completed",
        "extractedData": {"pricingFound": True, "sourceUrls": ["https://example.com/pricing"]},
    }

    merged = merge_service.merge_results(BASE_ENRICHMENT, scan_result)

    assert merged["confidence"] == "medium"


def test_confirmed_evidence_does_not_raise_high_above_high():
    scan_result = {
        "scanStatus": "Completed",
        "extractedData": {"pricingFound": True, "sourceUrls": ["https://example.com/pricing"]},
    }

    merged = merge_service.merge_results(dict(BASE_ENRICHMENT, confidence="high"), scan_result)

    assert merged["confidence"] == "high"


def test_no_confirmed_evidence_leaves_confidence_unchanged():
    # A completed scan that found nothing is not evidence — no bump.
    scan_result = {"scanStatus": "Completed", "extractedData": {"pricingFound": False}}

    merged = merge_service.merge_results(BASE_ENRICHMENT, scan_result)

    assert merged["confidence"] == "low"
