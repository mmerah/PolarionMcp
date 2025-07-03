"""Tests for the main FastAPI application."""

from unittest.mock import patch

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


@patch("mcp_server.config.settings")
def test_health_endpoint_without_env(mock_settings, client: TestClient) -> None:
    """Test health endpoint when environment variables are missing."""
    # Mock missing environment variables
    mock_settings.POLARION_URL = ""
    mock_settings.POLARION_USER = ""
    mock_settings.POLARION_TOKEN = ""
    
    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert "Service unavailable" in data["detail"]
