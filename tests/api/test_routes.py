"""
API tests — Mission 15. Uses FastAPI's TestClient.
"""

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


def test_get_batch_status_not_found():
    response = client.get("/api/agents/agent1/bulk-enrichment/does-not-exist")
    assert response.status_code == 404
