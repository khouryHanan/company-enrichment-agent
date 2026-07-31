"""
Tests for the logging service — Mission 14 / SCRUM-14.

The acceptance criteria that matter here: log lines are readable
(event name + key=value pairs), and no API keys or secrets ever reach
the output, even when a provider exception message embeds one.
"""

import pytest

from src.core import logging as log


@pytest.fixture
def captured(caplog):
    caplog.set_level("INFO", logger="agent1")
    return caplog


def last_message(caplog) -> str:
    return caplog.records[-1].getMessage()


def test_log_line_is_readable_event_plus_key_value_pairs(captured):
    log.info("batch_started", batch_id="batch_1", total=5)

    assert last_message(captured) == "batch_started batch_id=batch_1 total=5"


def test_event_without_fields_logs_just_the_event_name(captured):
    log.info("batch_completed")

    assert last_message(captured) == "batch_completed"


def test_error_level_is_used_for_error_logs(captured):
    log.error("database_save_failed", batch_id="batch_1")

    assert captured.records[-1].levelname == "ERROR"


class TestSecretRedaction:
    def test_api_key_value_in_error_string_is_redacted(self, captured):
        log.error("enrichment_failed", error="401 Unauthorized: api_key=abc123secret was rejected")

        message = last_message(captured)
        assert "abc123secret" not in message
        assert "api_key=[REDACTED]" in message

    def test_bearer_token_is_redacted(self, captured):
        log.error("agent3_scan_failed", error="header Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload")

        message = last_message(captured)
        assert "eyJhbGciOiJIUzI1NiJ9" not in message
        assert "[REDACTED]" in message

    def test_bare_provider_key_shapes_are_redacted(self, captured):
        log.error(
            "ai_call_failed",
            error="tried sk-proj-abc123def456ghi789 then AIzaSyD4W9v8xQ2p1LmNoPqRsTuV and gsk_a1b2c3d4e5f6g7h8",
        )

        message = last_message(captured)
        assert "sk-proj-abc123def456ghi789" not in message
        assert "AIzaSyD4W9v8xQ2p1LmNoPqRsTuV" not in message
        assert "gsk_a1b2c3d4e5f6g7h8" not in message

    def test_key_in_query_string_is_redacted(self, captured):
        log.error("ai_call_failed", error="POST https://api.example.com/v1?key=AIzaSyD4W9v8xQ2p1LmNoPqRsTuV failed")

        assert "AIzaSyD4W9v8xQ2p1LmNoPqRsTuV" not in last_message(captured)

    def test_normal_fields_are_not_redacted(self, captured):
        log.info(
            "company_processing_started",
            batch_id="batch_1",
            company_id="company_ab12cd34",
            company_name="Example Company",
        )

        assert (
            last_message(captured)
            == "company_processing_started batch_id=batch_1 company_id=company_ab12cd34 company_name=Example Company"
        )
