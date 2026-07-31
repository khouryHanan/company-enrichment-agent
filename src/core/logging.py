"""
Logging Service — Mission 14.

Structured logging used by every other service. Always include batch_id
and company_id (when relevant). Never log secrets or API keys.
"""

import logging as _logging
import re
import sys

_logger = _logging.getLogger("agent1")
_logger.setLevel(_logging.INFO)
_handler = _logging.StreamHandler(sys.stdout)
_handler.setFormatter(_logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
_logger.addHandler(_handler)

# Error strings from AI providers and HTTP clients can embed credentials
# (e.g. a key in a query string or an Authorization header echoed back in
# an exception message). Every log line passes through these patterns so
# no caller has to remember to scrub.
# Authorization: Bearer <token> — must run before the key=value pattern,
# which would otherwise consume the word "Bearer" as the value and leave
# the token itself in the log line.
_BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
# Bare provider key shapes: OpenAI/Anthropic (sk-...), Google (AIza...), Groq (gsk_...)
_BARE_KEY_PATTERN = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{8,}|AIza[0-9A-Za-z_-]{20,}|gsk_[A-Za-z0-9]{8,})\b")
# key=value / key: value pairs for credential-looking names
_KEY_VALUE_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|apikey|access[_-]?token|auth[_-]?token|token|secret|password|authorization)\b(\s*[=:]\s*)\S+"
)


def _redact(message: str) -> str:
    message = _BEARER_PATTERN.sub("Bearer [REDACTED]", message)
    message = _BARE_KEY_PATTERN.sub("[REDACTED]", message)
    message = _KEY_VALUE_PATTERN.sub(r"\1\2[REDACTED]", message)
    return message


def _format(event: str, **fields) -> str:
    extras = " ".join(f"{k}={v}" for k, v in fields.items())
    return _redact(f"{event} {extras}".strip())


def info(event: str, **fields) -> None:
    _logger.info(_format(event, **fields))


def error(event: str, **fields) -> None:
    _logger.error(_format(event, **fields))
