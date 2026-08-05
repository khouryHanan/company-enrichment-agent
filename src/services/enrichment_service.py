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
from src.core.retry import retry

MAX_RETRIES = 1  # one retry on invalid/malformed output, then fail per Mission 13
# Intentionally lower than the general settings.MAX_RETRIES default (3):
# a model that returns malformed output once is quite likely to do so
# again, so we fail fast here rather than burning the full retry budget.


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
    location: str = Field(..., description='Country/city of primary operations. Use "unknown" if it cannot be determined.')
    companySize: str = Field(..., description='Approximate employee count or range, e.g. "51-200". Use "unknown" if it cannot be determined.')
    foundedYear: str = Field(..., description='Founding year, e.g. "2008". Use "unknown" if it cannot be determined.')
    headquarters: str = Field(..., description='Headquarters city and country. Use "unknown" if it cannot be determined.')
    keyCompetitors: list[str] = Field(..., description="Main competitors. Empty list if unknown.")
    techStack: list[str] = Field(..., description="Technologies the company is publicly known to build on or offer. Empty list if unknown.")
    keyContacts: list[str] = Field(..., description='Publicly known leadership only, formatted "Name — Role". Never include email addresses or phone numbers. Empty list if unknown.')
    confidence: Literal["low", "medium", "high"]
    missingFields: list[str] = Field(..., description="Names of fields that could not be determined.")
    sourcesUsed: list[str] = Field(..., description='e.g. "company_name", "website_url", "linkedin_url".')


ENRICHMENT_SYSTEM_PROMPT = """You are a company research assistant. Your job is to \
produce a factual, structured company profile using ONLY the company name, \
website, domain, and LinkedIn URL provided in the user message.

Rules you must follow:
- If the provided domain or LinkedIn URL clearly identifies a company you \
know (for example, github.com is GitHub), use your knowledge of that company \
to fill the profile as fully as you can.
- Never guess about a company you cannot confidently identify from the \
provided domain or LinkedIn URL — a similar name alone is not identification. \
For those, set fields you cannot support to "unknown" (for single strings) or \
"not_available" (where that reads more naturally, e.g. for a business model). \
An honest "unknown" is always better than an invented value.
- keyContacts may only contain leadership that is publicly and widely known \
(founders, CEO). Format each entry as "Name — Role". Never include email \
addresses, phone numbers, or any other contact details — return names and \
roles only.

Confidence guidance:
- "high": the domain identifies a company you know well and most fields are \
filled from solid knowledge of it.
- "medium": the company is identified, but several fields are inferred or \
incomplete.
- "low": you could not confidently identify the company; little more than \
the name and URLs were available.
"""

if not settings.AI_MODEL:
    raise ValueError(
        "AI_MODEL environment variable is not set. Add it to your .env, "
        "e.g. AI_MODEL=google_genai:gemini-2.0-flash"
    )

_llm = init_chat_model(settings.AI_MODEL, temperature=0.0)  # low-temperature, deterministic per Mission 9
_structured_llm = _llm.with_structured_output(CompanyProfile)


# Profile fields the caller may already know. Supplied values are
# authoritative: they overwrite the model's answer and clear the field
# from missingFields. Populated today by the EYEjee import adapter from
# the export's Loc/Size columns.
KNOWN_FACT_FIELDS = ("location", "companySize")


def known_facts(company) -> dict:
    """The caller-supplied facts present on this company input. Blank and
    placeholder values are ignored so an empty column never overwrites a
    real answer with nothing."""
    facts = {}

    for field in KNOWN_FACT_FIELDS:
        value = getattr(company, field, None)
        if value and str(value).strip() and str(value).strip().lower() not in ("unknown", "not_available"):
            facts[field] = str(value).strip()

    return facts


def build_prompt(company, normalized: dict) -> str:
    prompt = (
        f"Company name: {company.companyName}\n"
        f"Website URL: {normalized.get('normalizedWebsite', 'unknown')}\n"
        f"Domain: {normalized.get('domain', 'unknown')}\n"
        f"LinkedIn URL: {company.linkedinUrl or 'unknown'}\n"
    )

    # Stating known facts does not decide those fields — they are
    # overwritten after the call regardless — but it stops the model
    # reasoning about, say, a global enterprise when the caller already
    # knows this is an 11-50 person US company.
    facts = known_facts(company)
    if facts:
        stated = ", ".join(f"{field}: {value}" for field, value in facts.items())
        prompt += f"Known facts (established by the caller, treat as true): {stated}\n"

    return prompt + "\nProduce the structured company profile as specified."


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

    log.info("enrichment_started", company_id=company_id, company_name=company.companyName)

    profile: CompanyProfile = retry(
        _call_model,
        prompt,
        retryable_exceptions=(AIResponseError,),
        max_retries=MAX_RETRIES,
        event_name="ai_output_parsing",
    )

    log.info("enrichment_completed", company_id=company_id, confidence=profile.confidence)

    # Caller-supplied facts outrank inference, and a field the caller
    # established is not missing — however the model answered it.
    facts = known_facts(company)
    missing_fields = [field for field in profile.missingFields if field not in facts]
    if facts:
        log.info("known_facts_applied", company_id=company_id, fields=",".join(sorted(facts)))

    return {
        "companyId": company_id,
        "companyName": profile.companyName,
        "description": profile.description,
        "industry": profile.industry,
        "productsServices": profile.productsServices,
        "targetAudience": profile.targetAudience,
        "businessModel": profile.businessModel,
        "location": facts.get("location", profile.location),
        "companySize": facts.get("companySize", profile.companySize),
        "foundedYear": profile.foundedYear,
        "headquarters": profile.headquarters,
        "keyCompetitors": profile.keyCompetitors,
        "techStack": profile.techStack,
        "keyContacts": profile.keyContacts,
        "confidence": profile.confidence,
        "missingFields": missing_fields,
        "sourcesUsed": profile.sourcesUsed,
        "status": "Completed",
    }