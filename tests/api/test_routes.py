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
@patch("src.api.routes.repository.get_batch")
def test_get_batch_status_not_found(mock_get_batch):
    mock_get_batch.return_value = None
    response = client.get("/api/agents/agent1/bulk-enrichment/does-not-exist")
    assert response.status_code == 404
