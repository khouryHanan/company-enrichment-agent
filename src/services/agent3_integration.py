"""
Agent 3 Integration Service — Mission 10 / SCRUM-10.

Triggers Agent 3 to scan a company's website and receives the scan
result. Any failure (timeout, connection error, bad response) is caught
here and raised as a single Agent3IntegrationError — batch_service.py
already treats this as "safe to fail": the company still gets saved
with whatever the AI enrichment produced, just marked Partially
Completed instead of Completed.

Endpoint contract (see docs/technical-design.md section 8):
  POST {AGENT3_BASE_URL}/api/agents/agent3/scan
  Request:  {"companyId": ..., "websiteUrl": ...}
  Response: {"companyId": ..., "scanStatus": "Completed" | "Failed",
             "extractedData": {...}}
"""

import httpx

from src.core.config import settings
from src.core import logging as log
from src.core.errors import Agent3IntegrationError

SCAN_ENDPOINT = "/api/agents/agent3/scan"
TIMEOUT_SECONDS = 10.0


def trigger_scan(company_id: str, website_url: str) -> dict:
    """
    Sends {"companyId": ..., "websiteUrl": ...} to Agent 3 and returns its
    response. Raises Agent3IntegrationError on any failure — timeout,
    connection error, non-2xx response, or a malformed response body —
    so the caller can decide how to degrade gracefully rather than
    crashing the batch.
    """
    url = f"{settings.AGENT3_BASE_URL}{SCAN_ENDPOINT}"
    payload = {"companyId": company_id, "websiteUrl": website_url}

    try:
        response = httpx.post(url, json=payload, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        log.error("agent3_scan_timeout", company_id=company_id, url=url)
        raise Agent3IntegrationError(f"Agent 3 timed out for company {company_id}") from exc
    except httpx.ConnectError as exc:
        log.error("agent3_scan_connection_error", company_id=company_id, url=url)
        raise Agent3IntegrationError(f"Could not connect to Agent 3 at {url}") from exc
    except httpx.HTTPStatusError as exc:
        log.error(
            "agent3_scan_bad_response",
            company_id=company_id,
            status_code=exc.response.status_code,
        )
        raise Agent3IntegrationError(
            f"Agent 3 returned {exc.response.status_code} for company {company_id}"
        ) from exc
    except httpx.HTTPError as exc:
        # Catch-all for any other httpx failure not covered above
        # (e.g. malformed URL, unexpected network condition).
        log.error("agent3_scan_failed", company_id=company_id, error=str(exc))
        raise Agent3IntegrationError(f"Agent 3 request failed for company {company_id}: {exc}") from exc

    try:
        data = response.json()
    except ValueError as exc:
        log.error("agent3_scan_invalid_response", company_id=company_id)
        raise Agent3IntegrationError(f"Agent 3 returned a non-JSON response for company {company_id}") from exc

    if "scanStatus" not in data:
        log.error("agent3_scan_malformed_response", company_id=company_id, response=data)
        raise Agent3IntegrationError(f"Agent 3 response missing scanStatus for company {company_id}")

    log.info("agent3_scan_completed", company_id=company_id, scan_status=data["scanStatus"])
    return data