"""
Company Enrichment Service — Mission 9.

Builds the AI prompt, calls the model, and validates/parses the structured
JSON response. The model must not invent information — missing data is
returned as "unknown" or "not_available".
"""

import json


ENRICHMENT_SYSTEM_PROMPT = """
You are a company research assistant. Given only the company name, website,
domain, and LinkedIn URL provided, produce a factual, structured company
profile. Do not invent information you cannot support from the given
context. Any field you cannot determine must be set to "unknown" or
"not_available". Respond with JSON only, no other text.
"""


def build_prompt(company, normalized: dict) -> str:
    raise NotImplementedError


def enrich_company(company, normalized: dict) -> dict:
    """
    Returns a structured enrichment dict matching CompanyEnrichmentResult
    (see src/api/schemas.py). Must validate the AI's JSON output before
    returning it — retry once on invalid JSON, then raise.
    """
    raise NotImplementedError


def parse_ai_response(raw_response: str) -> dict:
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid AI JSON output: {exc}") from exc
