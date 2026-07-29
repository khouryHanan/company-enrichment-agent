"""
Company Enrichment Service — Mission 9 / SCRUM-9.

Uses LangChain's init_chat_model + with_structured_output so the
underlying AI provider can be swapped via a single config string
(AI_MODEL) — no code changes needed to move between Gemini, Anthropic,
OpenAI, Groq, etc. LangChain handles getting well-formed JSON out of the
model; a Pydantic schema defines and enforces the required shape.

Hallucination control: the model is instructed to never invent
information. Any field it cannot support from the given context must
come back as "unknown" or "not_available" rather than a guess.
"""

import uuid
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from src.core.config import settings
from src.core import logging as log
from src.core.errors import AIResponseError

MAX_RETRIES = 1  # one retry on invalid/malformed output, then fail per Mission 13


class CompanyProfile(BaseModel):
    """
    The required output shape for Mission 9. Using this as the schema for
    with_structured_output means LangChain (via the underlying provider's
    JSON mode or tool-calling) enforces these types and required fields
    directly — a model returning a missing field or a bad confidence
    value fails validation before it ever reaches our code.
    """
    companyName: str
    description: str = Field(..., description='Factual summary. Use "not_available" if unknown.')
    industry: str = Field(..., description='Use "unknown" if it cannot be determined.')
    productsServices: list[str]
    targetAudience: list[str]
    businessModel: str = Field(..., description='Use "not_available" if unknown.')
    confidence: Literal["low", "medium", "high"]
    missingFields: list[str] = Field(..., description="Names of fields that could not be determined.")
    sourcesUsed: list[str] = Field(..., description='e.g. "company_name", "website_url", "linkedin_url".')


ENRICHMENT_SYSTEM_PROMPT = """You are a company research assistant. Your job is to \
produce a factual, structured company profile using ONLY the company name, \
website, domain, and LinkedIn URL provided in the user message.

Rules you must follow:
- Do not invent, assume, or infer information you cannot support from the \
given context. If you do not have enough information for a field, set that \
field's value to "unknown" (for single strings) or "not_available" (where \
"not_available" reads more naturally, e.g. for a business model).
- Do not use outside knowledge about companies with similar names unless the \
provided domain or LinkedIn URL confirms it is the same company.

Confidence guidance:
- "high": website and/or LinkedIn content clearly supports most fields.
- "medium": some fields supported, others inferred from limited context.
- "low": little more than the company name and URLs were available.
"""

if not settings.AI_MODEL:
    raise ValueError(
        "AI_MODEL environment variable is not set. Add it to your .env, "
        "e.g. AI_MODEL=google_genai:gemini-2.0-flash"
    )

_llm = init_chat_model(settings.AI_MODEL, temperature=0.0)  # low-temperature, deterministic per Mission 9
_structured_llm = _llm.with_structured_output(CompanyProfile)


def build_prompt(company, normalized: dict) -> str:
    return (
        f"Company name: {company.companyName}\n"
        f"Website URL: {normalized.get('normalizedWebsite', 'unknown')}\n"
        f"Domain: {normalized.get('domain', 'unknown')}\n"
        f"LinkedIn URL: {company.linkedinUrl or 'unknown'}\n\n"
        "Produce the structured company profile as specified."
    )


def _call_model(prompt: str) -> CompanyProfile:
    """
    Single point of contact with the AI provider. Swapping providers is a
    config change (settings.AI_MODEL + the matching provider package and
    API key env var) — nothing here needs to change.

    Raises AIResponseError if the model's output doesn't conform to
    CompanyProfile — LangChain/Pydantic validation failures are caught
    and normalized to our own error type so callers don't need to know
    about LangChain's internal exception types.
    """
    try:
        return _structured_llm.invoke([
            SystemMessage(content=ENRICHMENT_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
    except Exception as exc:
        raise AIResponseError(f"AI did not return a valid structured output: {exc}") from exc


def enrich_company(company, normalized: dict) -> dict:
    """
    Returns a dict matching CompanyEnrichmentResult (src/api/schemas.py).
    Retries once on malformed/invalid output per Mission 13's retry
    policy, then raises AIResponseError so the caller (batch_service) can
    mark the company Failed without crashing the batch.
    """
    prompt = build_prompt(company, normalized)
    company_id = f"company_{uuid.uuid4().hex[:8]}"

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            profile: CompanyProfile = _call_model(prompt)
            return {
                "companyId": company_id,
                "companyName": profile.companyName,
                "description": profile.description,
                "industry": profile.industry,
                "productsServices": profile.productsServices,
                "targetAudience": profile.targetAudience,
                "businessModel": profile.businessModel,
                "confidence": profile.confidence,
                "missingFields": profile.missingFields,
                "sourcesUsed": profile.sourcesUsed,
                "status": "Completed",
            }
        except AIResponseError as exc:
            last_error = exc
            log.error(
                "ai_output_parsing_failed",
                company_id=company_id,
                attempt=attempt + 1,
                error=str(exc),
            )

    # All retries exhausted — raise so batch_service marks this company
    # Failed and moves on to the next one, per Mission 13.
    raise last_error