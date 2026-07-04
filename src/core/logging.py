"""
Logging Service — Mission 14.

Structured logging used by every other service. Always include batch_id
and company_id (when relevant). Never log secrets or API keys.
"""

import logging as _logging
import sys

_logger = _logging.getLogger("agent1")
_logger.setLevel(_logging.INFO)
_handler = _logging.StreamHandler(sys.stdout)
_handler.setFormatter(_logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
_logger.addHandler(_handler)


def _format(event: str, **fields) -> str:
    extras = " ".join(f"{k}={v}" for k, v in fields.items())
    return f"{event} {extras}".strip()


def info(event: str, **fields) -> None:
    _logger.info(_format(event, **fields))


def error(event: str, **fields) -> None:
    _logger.error(_format(event, **fields))
