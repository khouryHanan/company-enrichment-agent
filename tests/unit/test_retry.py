"""
Tests for the shared retry helper — Mission 13 / SCRUM-13.
"""

import pytest
from unittest.mock import MagicMock

from src.core.retry import retry


class _TemporaryError(Exception):
    pass


class _PermanentError(Exception):
    pass


def test_returns_result_on_first_success_no_retry_needed():
    func = MagicMock(return_value="ok")

    result = retry(func, retryable_exceptions=(_TemporaryError,), max_retries=3, backoff_seconds=0)

    assert result == "ok"
    assert func.call_count == 1


def test_retries_up_to_max_retries_then_succeeds():
    func = MagicMock(side_effect=[_TemporaryError("fail 1"), _TemporaryError("fail 2"), "ok"])

    result = retry(func, retryable_exceptions=(_TemporaryError,), max_retries=3, backoff_seconds=0)

    assert result == "ok"
    assert func.call_count == 3


def test_raises_last_exception_after_exhausting_retries():
    func = MagicMock(side_effect=_TemporaryError("always fails"))

    with pytest.raises(_TemporaryError):
        retry(func, retryable_exceptions=(_TemporaryError,), max_retries=2, backoff_seconds=0)

    # initial attempt + 2 retries = 3 total calls
    assert func.call_count == 3


def test_does_not_retry_non_retryable_exceptions():
    func = MagicMock(side_effect=_PermanentError("permanent failure"))

    with pytest.raises(_PermanentError):
        retry(func, retryable_exceptions=(_TemporaryError,), max_retries=3, backoff_seconds=0)

    # Not in retryable_exceptions — fails immediately, no retry attempted.
    assert func.call_count == 1


def test_passes_args_and_kwargs_through_to_func():
    func = MagicMock(return_value="ok")

    retry(func, "arg1", "arg2", key="value", retryable_exceptions=(_TemporaryError,), backoff_seconds=0)

    func.assert_called_once_with("arg1", "arg2", key="value")


def test_uses_settings_max_retries_when_not_specified(monkeypatch):
    from src.core import retry as retry_module
    monkeypatch.setattr(retry_module.settings, "MAX_RETRIES", 1)

    func = MagicMock(side_effect=_TemporaryError("fail"))

    with pytest.raises(_TemporaryError):
        retry(func, retryable_exceptions=(_TemporaryError,), backoff_seconds=0)

    # settings.MAX_RETRIES=1 -> initial attempt + 1 retry = 2 total calls
    assert func.call_count == 2