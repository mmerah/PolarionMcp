"""Tests for the main FastAPI application."""

import pytest
from fastapi.testclient import TestClient

from mcp_server.main import app


@pytest.fixture  # type: ignore[misc]
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


def test_root_endpoint(client: TestClient) -> None:
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Welcome to the MCP Server for Polarion"
    assert data["version"] == "1.0.0"


def test_health_endpoint_without_env(client: TestClient) -> None:
    """Test health endpoint when environment variables are missing."""
    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert "Service unavailable" in data["detail"]
