"""Tests for Polarion REST API endpoints with mocked Polarion driver."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from mcp_server.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Provide authentication headers for testing."""
    return {"X-API-Key": "test-api-key"}


@patch("mcp_server.routers.polarion.settings")
@patch("mcp_server.auth.settings")
@patch("mcp_server.routers.polarion.PolarionDriver")
def test_get_workitem_success(
    mock_driver_class,
    mock_auth_settings,
    mock_settings,
    client: TestClient,
    auth_headers,
) -> None:
    """Test successful work item retrieval."""
    # Mock settings
    mock_settings.POLARION_URL = "https://test.polarion.com"
    mock_settings.POLARION_USER = "test@example.com"
    mock_settings.POLARION_TOKEN = "test-token"
    mock_auth_settings.MCP_SERVER_API_KEY = "test-api-key"

    # Mock the driver and work item
    mock_driver_instance = MagicMock()
    mock_driver_instance.__enter__ = MagicMock(return_value=mock_driver_instance)
    mock_driver_instance.__exit__ = MagicMock(return_value=None)

    mock_workitem = MagicMock()
    mock_workitem.id = "TEST-001"
    mock_workitem.title = "Test Work Item"
    mock_workitem.type.id = "requirement"
    mock_workitem.status.id = "open"
    mock_workitem.description.content = "Test description"
    mock_workitem.customFields = {"Custom": []}

    mock_driver_instance.get_workitem.return_value = mock_workitem
    mock_driver_class.return_value = mock_driver_instance

    response = client.get(
        "/polarion/projects/TestProject/workitems/TEST-001", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "TEST-001"
    assert data["title"] == "Test Work Item"
    assert data["type"] == "requirement"
    assert data["status"] == "open"
    assert data["description"] == "Test description"

    # Verify driver was called correctly
    mock_driver_class.assert_called_once_with(
        "https://test.polarion.com", "test@example.com", "test-token"
    )
    mock_driver_instance.select_project.assert_called_once_with("TestProject")
    mock_driver_instance.get_workitem.assert_called_once_with("TEST-001")


@patch("mcp_server.routers.polarion.settings")
@patch("mcp_server.auth.settings")
@patch("mcp_server.routers.polarion.PolarionDriver")
def test_get_workitem_not_found(
    mock_driver_class,
    mock_auth_settings,
    mock_settings,
    client: TestClient,
    auth_headers,
) -> None:
    """Test work item not found scenario."""
    # Mock settings
    mock_settings.POLARION_URL = "https://test.polarion.com"
    mock_settings.POLARION_USER = "test@example.com"
    mock_settings.POLARION_TOKEN = "test-token"
    mock_auth_settings.MCP_SERVER_API_KEY = "test-api-key"

    # Mock the driver to return None (not found)
    mock_driver_instance = MagicMock()
    mock_driver_instance.__enter__ = MagicMock(return_value=mock_driver_instance)
    mock_driver_instance.__exit__ = MagicMock(return_value=None)
    mock_driver_instance.select_project = MagicMock()
    mock_driver_instance.get_workitem.return_value = None
    mock_driver_class.return_value = mock_driver_instance

    response = client.get(
        "/polarion/projects/TestProject/workitems/NONEXISTENT", headers=auth_headers
    )

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@patch("mcp_server.auth.settings")
def test_get_workitem_unauthorized(mock_auth_settings, client: TestClient) -> None:
    """Test unauthorized access without API key."""
    mock_auth_settings.MCP_SERVER_API_KEY = "correct-api-key"

    # Request without API key
    response = client.get("/polarion/projects/TestProject/workitems/TEST-001")
    assert response.status_code == 401

    # Request with wrong API key
    response = client.get(
        "/polarion/projects/TestProject/workitems/TEST-001",
        headers={"X-API-Key": "wrong-api-key"},
    )
    assert response.status_code == 401


@patch("mcp_server.routers.polarion.settings")
@patch("mcp_server.auth.settings")
@patch("mcp_server.routers.polarion.PolarionDriver")
def test_get_project_info_success(
    mock_driver_class,
    mock_auth_settings,
    mock_settings,
    client: TestClient,
    auth_headers,
) -> None:
    """Test successful project info retrieval."""
    # Mock settings
    mock_settings.POLARION_URL = "https://test.polarion.com"
    mock_settings.POLARION_USER = "test@example.com"
    mock_settings.POLARION_TOKEN = "test-token"
    mock_auth_settings.MCP_SERVER_API_KEY = "test-api-key"

    # Mock the driver
    mock_driver_instance = MagicMock()
    mock_driver_instance.__enter__ = MagicMock(return_value=mock_driver_instance)
    mock_driver_instance.__exit__ = MagicMock(return_value=None)
    mock_driver_instance.get_project_info.return_value = {
        "id": "TestProject",
        "name": "Test Project",
        "description": "A test project",
    }
    mock_driver_class.return_value = mock_driver_instance

    response = client.get("/polarion/projects/TestProject/info", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "TestProject"
    assert data["name"] == "Test Project"
    assert data["description"] == "A test project"

    # Verify driver was called correctly
    mock_driver_class.assert_called_once_with(
        "https://test.polarion.com", "test@example.com", "test-token"
    )
    mock_driver_instance.select_project.assert_called_once_with("TestProject")
    mock_driver_instance.get_project_info.assert_called_once()


@patch("mcp_server.routers.polarion.settings")
@patch("mcp_server.auth.settings")
@patch("mcp_server.routers.polarion.PolarionDriver")
def test_search_workitems_success(
    mock_driver_class,
    mock_auth_settings,
    mock_settings,
    client: TestClient,
    auth_headers,
) -> None:
    """Test successful work item search."""
    # Mock settings
    mock_settings.POLARION_URL = "https://test.polarion.com"
    mock_settings.POLARION_USER = "test@example.com"
    mock_settings.POLARION_TOKEN = "test-token"
    mock_auth_settings.MCP_SERVER_API_KEY = "test-api-key"

    # Mock the driver
    mock_driver_instance = MagicMock()
    mock_driver_instance.__enter__ = MagicMock(return_value=mock_driver_instance)
    mock_driver_instance.__exit__ = MagicMock(return_value=None)
    mock_driver_instance.search_workitems.return_value = [
        {
            "id": "REQ-001",
            "title": "Test Requirement 1",
            "type": {"id": "requirement"},
            "status": {"id": "open"},
            "description": {"content": "First requirement"},
        },
        {
            "id": "REQ-002",
            "title": "Test Requirement 2",
            "type": {"id": "requirement"},
            "status": {"id": "approved"},
            "description": {"content": "Second requirement"},
        },
    ]
    mock_driver_class.return_value = mock_driver_instance

    response = client.get(
        "/polarion/projects/TestProject/workitems?query=type:requirement",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["id"] == "REQ-001"
    assert data["items"][1]["id"] == "REQ-002"

    # Verify driver was called correctly
    mock_driver_instance.search_workitems.assert_called_once_with(
        "type:requirement", field_list=None
    )
