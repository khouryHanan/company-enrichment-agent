"""
API tests — Mission 15. Uses FastAPI's TestClient.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_bulk_enrichment_rejects_empty_list():
    response = client.post("/api/agents/agent1/bulk-enrichment", json={"companies": []})
    assert response.status_code == 400


# Mocked like the rest of the API tests — this was the one test that hit
# the real database file, so it failed on any fresh checkout with no
# agent1.db (tables are created at app startup, which TestClient does
# not trigger without a `with` block).
@patch("src.api.routes.batch_service.get_batch_summary")
def test_get_batch_status_not_found(mock_get_batch):
    mock_get_batch.return_value = None
    response = client.get("/api/agents/agent1/bulk-enrichment/does-not-exist")
    assert response.status_code == 404


@patch("src.api.routes.batch_service.start_batch")
def test_unexpected_server_error_returns_json_not_plain_text(mock_start):
    # Starlette's default 500 body is plain text, which any JSON client
    # (including the demo UI) fails to parse — hiding the real reason.
    mock_start.side_effect = RuntimeError("boom")
    client_no_reraise = TestClient(app, raise_server_exceptions=False)

    response = client_no_reraise.post(
        "/api/agents/agent1/bulk-enrichment",
        json={"companies": [{"companyName": "X", "websiteUrl": "https://x.com"}]},
    )

    assert response.status_code == 500
    assert "boom" in response.json()["detail"]
