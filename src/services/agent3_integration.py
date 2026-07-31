"""
Agent 3 Integration Service — Mission 10 / SCRUM-10, retry logic added
for Mission 13 / SCRUM-13.

Triggers Agent 3 to scan a company's website and receives the scan
result. Timeouts, connection errors, and 5xx responses are treated as
temporary and retried (per Mission 13's retry rules); 4xx responses and
malformed response bodies are treated as permanent and raised
immediately — retrying an identical bad request won't produce a
different result. Any failure that survives retries is raised as a
single Agent3IntegrationError — batch_service.py already treats this as
"safe to fail": the company still gets saved with whatever the AI
enrichment produced, just marked Partially Completed instead of
Completed.

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
from src.core.retry import retry

SCAN_ENDPOINT = "/api/agents/agent3/scan"
TIMEOUT_SECONDS = 10.0

# Temporary — worth retrying: network hiccups and server-side errors.
_RETRYABLE_EXCEPTIONS = (httpx.TimeoutException, httpx.ConnectError)


def _do_request(url: str, payload: dict) -> httpx.Response:
    response = httpx.post(url, json=payload, timeout=TIMEOUT_SECONDS)
    if response.status_code >= 500:
        # Server-side error — temporary, worth retrying. Raised as a
        # TimeoutException-compatible retryable type by reusing the
        # same retry() call below via a dedicated wrapper exception.
        raise _RetryableServerError(f"Agent 3 returned {response.status_code}")
    response.raise_for_status()  # 4xx here — permanent, not retried
    return response


class _RetryableServerError(Exception):
    """Internal-only: signals a 5xx response is worth retrying."""


def trigger_scan(company_id: str, website_url: str) -> dict:
    """
    Sends {"companyId": ..., "websiteUrl": ...} to Agent 3 and returns its
    response. Raises Agent3IntegrationError if every retry attempt fails,
    or immediately for permanent failures (4xx, malformed body) — so the
    caller can decide how to degrade gracefully rather than crashing the
    batch.
    """
    url = f"{settings.AGENT3_BASE_URL}{SCAN_ENDPOINT}"
    payload = {"companyId": company_id, "websiteUrl": website_url}

    log.info("agent3_scan_triggered", company_id=company_id, url=url)

    try:
        response = retry(
            _do_request,
            url,
            payload,
            retryable_exceptions=_RETRYABLE_EXCEPTIONS + (_RetryableServerError,),
            event_name="agent3_scan",
        )
    except _RetryableServerError as exc:
        log.error("agent3_scan_server_error", company_id=company_id, url=url)
        raise Agent3IntegrationError(f"Agent 3 server error for company {company_id}: {exc}") from exc
    except httpx.TimeoutException as exc:
        log.error("agent3_scan_timeout", company_id=company_id, url=url)
        raise Agent3IntegrationError(f"Agent 3 timed out for company {company_id}") from exc
    except httpx.ConnectError as exc:
        log.error("agent3_scan_connection_error", company_id=company_id, url=url)
        raise Agent3IntegrationError(f"Could not connect to Agent 3 at {url}") from exc
    except httpx.HTTPStatusError as exc:
        # 4xx — permanent, was never retried.
        log.error(
            "agent3_scan_bad_response",
            company_id=company_id,
            status_code=exc.response.status_code,
        )
        raise Agent3IntegrationError(
            f"Agent 3 returned {exc.response.status_code} for company {company_id}"
        ) from exc
    except httpx.HTTPError as exc:
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