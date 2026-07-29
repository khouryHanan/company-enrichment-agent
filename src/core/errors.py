"""
Custom exception classes — Mission 13.

Distinguishing error types lets the batch service decide what's retryable
(temporary) versus permanent, per docs/technical-design.md section 9.
"""


class Agent1Error(Exception):
    """Base class for all Agent 1 errors."""


class InvalidInputError(Agent1Error):
    """Permanent — malformed or missing input. Not retryable."""


class WebsiteUnreachableError(Agent1Error):
    """Temporary — may be retried with backoff."""


class AIResponseError(Agent1Error):
    """Raised when the AI call fails or returns invalid JSON."""


class Agent3IntegrationError(Agent1Error):
    """Raised when Agent 3 fails or times out. Company should be marked
    Partially Completed rather than failing the whole batch."""


class DatabaseSaveError(Agent1Error):
    """Temporary — may be retried with backoff."""


class NotFoundError(Agent1Error):
    """Raised when a requested batch or company doesn't exist."""