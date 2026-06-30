"""Tests for the health-check endpoint."""

from fastapi import status
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_check() -> None:
    """GET /api/v1/health returns 200 with status 'ok'."""
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data
    assert "version" in data
