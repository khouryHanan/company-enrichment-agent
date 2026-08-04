"""
Merge Service — Mission 11 / SCRUM-11.

Combines the AI enrichment result (enrichment_service.py, SCRUM-9) with
Agent 3's website scan result (agent3_integration.py, SCRUM-10). Website
evidence is treated as more authoritative than the AI's inference — where
Agent 3 confirms something, it overwrites the AI's guess and the field
is removed from missingFields. Fields Agent 3 didn't find evidence for
are left exactly as the AI produced them, still marked missing if they
were missing before — nothing here invents data either.

Course connection (per Mission 11): this is the RAG-adjacent piece —
grounding the profile in retrieved evidence, keeping confirmed data
traceable to its source, and refusing to claim things aren't supported.
"""

# Fields Agent 3's extractedData may report; each maps to the profile
# field it updates and the missingFields entry it clears if present.
# Kept as a simple lookup — expand here if Agent 3's contract grows.
_BOOLEAN_EVIDENCE_FIELDS = {
    "pricingFound": "pricingAvailable",
    "blogFound": "blogPresent",
    "legalFound": "legalPagesPresent",
    "customerJourneyFound": "customerJourneyPresent",
}

# One-level confidence promotion applied when the website scan confirmed
# evidence: the AI rated itself before any evidence existed.
_CONFIDENCE_BUMP = {"low": "medium", "medium": "high", "high": "high"}


def merge_results(enrichment: dict, scan_result: dict) -> dict:
    """
    Returns a new profile dict — does not mutate the inputs. Adds a
    "sourceReferences" list of {"field", "url"} pairs so the database
    layer can persist which URL backs which piece of evidence
    (repository.save_company reads this to populate the Source table).
    """
    merged = dict(enrichment)
    extracted = scan_result.get("extractedData") or {}
    source_urls = extracted.get("sourceUrls", [])
    missing_fields = list(merged.get("missingFields", []))
    sources_used = set(merged.get("sourcesUsed", []))
    source_references = []

    # Products/services: website evidence overwrites the AI's guess.
    if extracted.get("productsServices"):
        merged["productsServices"] = extracted["productsServices"]
        if "productsServices" in missing_fields:
            missing_fields.remove("productsServices")
        sources_used.add("website_scan")
        for url in source_urls:
            source_references.append({"field": "productsServices", "url": url})

    # Boolean site-evidence indicators (pricing, blog, legal, customer
    # journey) — these aren't part of the AI schema, they're confirmed
    # facts about the site, kept clearly separate from AI-generated
    # analysis per Mission 11's requirement.
    for extracted_key, profile_key in _BOOLEAN_EVIDENCE_FIELDS.items():
        if extracted_key in extracted:
            merged[profile_key] = extracted[extracted_key]
            if extracted[extracted_key]:
                sources_used.add("website_scan")
                for url in source_urls:
                    source_references.append({"field": profile_key, "url": url})

    # Confirmed website evidence makes the profile more trustworthy than
    # the AI's pre-evidence self-assessment — raise confidence one level
    # when the scan actually backed something up. Evidence-based, so it
    # stays consistent with "explicit confidence on every claim": the
    # bump happens only when sourceReferences records what raised it.
    if source_references:
        merged["confidence"] = _CONFIDENCE_BUMP.get(merged.get("confidence"), merged.get("confidence"))

    merged["missingFields"] = missing_fields
    merged["sourcesUsed"] = sorted(sources_used)
    merged["sourceReferences"] = source_references
    merged["status"] = "Completed"
    return merged