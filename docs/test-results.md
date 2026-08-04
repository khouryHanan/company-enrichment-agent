# Test Results — Agent 1 (SCRUM-15)

Latest full run: **2026-08-04** on `main` — **102 passed, 0 failed** (1 deprecation
warning from Starlette's test client, unrelated to our code).

```bash
pytest          # full suite
pytest -v       # per-test detail
```

## Suite layout

| Location | Tests | Covers |
|---|---|---|
| `tests/unit/test_validation_service.py` | 15 | Field/URL validation, duplicates |
| `tests/unit/test_repository.py` | 13 | Database persistence + retry |
| `tests/unit/test_agent3_integration.py` | 9 | Agent 3 calls, retries, bad responses |
| `tests/unit/test_merge_service.py` | 11 | AI + website-evidence merging |
| `tests/unit/test_logging.py` | 8 | Log format, secret redaction |
| `tests/unit/test_normalization_service.py` | 8 | Website/LinkedIn URL cleanup (SCRUM-6) |
| `tests/unit/test_retry.py` | 6 | Shared retry helper |
| `tests/unit/test_enrichment_service.py` | 6 | AI output parsing/schema enforcement |
| `tests/unit/test_batch_service.py` | 5 | Batch orchestration, failure isolation |
| `tests/integration/test_batch_flow.py` | 2 | Full pipeline, batch summary counts |
| `tests/api/test_bulk_input.py` | 9 | POST input validation |
| `tests/api/test_get_endpoints.py` | 7 | GET status/result endpoints |
| `tests/api/test_routes.py` | 3 | Health check, error responses |
| **Total** | **102** | |

## Required scenarios (SCRUM-15) → tests

| Scenario | Where tested |
|---|---|
| Valid company list | `test_valid_company_passes_through`, `test_accepts_valid_request_and_calls_batch_service` |
| Empty company list | `test_rejects_empty_company_list` (unit), `test_rejects_empty_companies_list` (API) |
| Missing company name | `test_detects_missing_company_name` (unit), `test_rejects_missing_company_name` (API) |
| Invalid website URL | `test_rejects_invalid_website_url`, `test_is_valid_website_url_rejects_missing_scheme` |
| Invalid LinkedIn URL | `test_rejects_invalid_linkedin_url`, `test_is_valid_linkedin_url_rejects_non_linkedin_domain` / `_non_company_path` |
| Duplicate company records | `test_detects_duplicate_by_domain_and_name`, `test_detects_duplicate_by_domain_only_different_name` |
| AI output parsing | `test_company_profile_rejects_invalid_confidence_value` / `_missing_required_field`, `test_enrich_company_retries_once_then_raises`, `test_call_model_wraps_provider_errors_as_ai_response_error` |
| Database save | `test_save_company_and_retrieve`, `test_save_company_persists_source_references`, `test_save_company_retries_then_raises_on_persistent_operational_error` |
| Agent 3 integration | all 9 tests in `test_agent3_integration.py` (success, payload, timeout/connection/5xx retries, 4xx no-retry, malformed body) |
| Batch summary | `test_batch_summary_matches_counts` (integration), `test_batch_summary_can_be_retrieved` (unit) |

## Acceptance criteria status

- **Core validation functions are tested** — 15 validation tests, including the
  Mission 4 example input.
- **Batch processing is tested** — orchestration unit tests plus a full-pipeline
  integration test.
- **API endpoints are tested** — 17 tests across POST input handling, GET
  endpoints, and health check.
- **Failed records do not break the full batch** —
  `test_one_failed_company_does_not_stop_the_batch` (unit) and
  `test_batch_continues_after_one_company_fails` (integration).
- **Test results are documented** — this file. Update the run date and counts
  when the suite changes.

## Notes

- No test calls a live AI provider, Agent 3, or external network — those
  boundaries are mocked, so the suite runs offline and deterministically.
- Repository tests run against a real SQLAlchemy engine on an in-memory
  SQLite database — persistence is exercised for real, but the on-disk
  `agent1.db` is never touched.
