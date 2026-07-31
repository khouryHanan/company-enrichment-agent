"""
Shared retry helper — Mission 13 / SCRUM-13.

Retries a callable a limited number of times when one of the given
"temporary" exception types is raised, with simple linear backoff.
Permanent errors should never be passed as retryable_exceptions here —
callers decide what's temporary vs. permanent for their own domain
(see docs/technical-design.md section 9 for the classification).
"""

import time

from src.core.config import settings
from src.core import logging as log


def retry(func, *args, retryable_exceptions, max_retries=None, backoff_seconds=0.5, event_name="operation", **kwargs):
    """
    Calls func(*args, **kwargs), retrying up to max_retries additional
    times if a retryable_exceptions exception is raised. Re-raises the
    last exception if every attempt fails. Logs each failed attempt.

    max_retries defaults to settings.MAX_RETRIES if not given explicitly,
    so the retry budget is centrally configurable via the MAX_RETRIES
    env var, but callers can override it for their own domain-specific
    policy (e.g. enrichment intentionally uses fewer retries).
    """
    attempts_allowed = (max_retries if max_retries is not None else settings.MAX_RETRIES) + 1
    last_exc = None

    for attempt in range(1, attempts_allowed + 1):
        try:
            return func(*args, **kwargs)
        except retryable_exceptions as exc:
            last_exc = exc
            log.error(
                f"{event_name}_retry_attempt_failed",
                attempt=attempt,
                max_attempts=attempts_allowed,
                error=str(exc),
            )
            if attempt < attempts_allowed:
                time.sleep(backoff_seconds * attempt)  # linear backoff: 0.5s, 1s, 1.5s, ...

    raise last_exc