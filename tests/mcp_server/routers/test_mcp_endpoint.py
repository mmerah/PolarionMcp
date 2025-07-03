"""Tests for MCP endpoint functionality with mocked Polarion."""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from mcp_server.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


@patch("mcp_server.routers.mcp_endpoint.settings")
def test_mcp_initialize(mock_settings, client: TestClient) -> None:
    """Test MCP initialize request."""
    # Mock settings
    mock_settings.POLARION_URL = "https://test.polarion.com"
    mock_settings.POLARION_USER = "test@example.com"
    mock_settings.POLARION_TOKEN = "test-token"

    request_data = {
        "jsonrpc": "2.0",
        "id": "test-1",
        "method": "initialize",
        "params": {},
    }

    response = client.post("/mcp", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == "test-1"
    assert "result" in data
    assert data["result"]["protocolVersion"] == "2024-11-05"
    assert "capabilities" in data["result"]


@patch("mcp_server.routers.mcp_endpoint.settings")
def test_mcp_tools_list(mock_settings, client: TestClient) -> None:
    """Test MCP tools/list request."""
    # Mock settings
    mock_settings.POLARION_URL = "https://test.polarion.com"
    mock_settings.POLARION_USER = "test@example.com"
    mock_settings.POLARION_TOKEN = "test-token"

    request_data = {
        "jsonrpc": "2.0",
        "id": "test-2",
        "method": "tools/list",
        "params": {},
    }

    response = client.post("/mcp", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == "test-2"
    assert "result" in data
    assert "tools" in data["result"]

    # Check that our new tool is in the list
    tool_names = [tool["name"] for tool in data["result"]["tools"]]
    assert "get_test_specs_from_document" in tool_names
    assert "health_check" in tool_names
    assert "get_project_info" in tool_names


@patch("mcp_server.routers.mcp_endpoint.PolarionDriver")
@patch("mcp_server.routers.mcp_endpoint.settings")
def test_mcp_get_project_info_success(
    mock_settings, mock_driver_class, client: TestClient
) -> None:
    """Test MCP tools/call for get_project_info with successful response."""
    # Mock settings
    mock_settings.POLARION_URL = "https://test.polarion.com"
    mock_settings.POLARION_USER = "test@example.com"
    mock_settings.POLARION_TOKEN = "test-token"

    # Mock the driver and its methods
    mock_driver_instance = MagicMock()
    mock_driver_instance.__enter__ = MagicMock(return_value=mock_driver_instance)
    mock_driver_instance.__exit__ = MagicMock(return_value=None)
    mock_driver_instance.get_project_info.return_value = {
        "id": "TestProject",
        "name": "Test Project",
        "description": "A test project",
    }
    mock_driver_class.return_value = mock_driver_instance

    request_data = {
        "jsonrpc": "2.0",
        "id": "test-3",
        "method": "tools/call",
        "params": {
            "name": "get_project_info",
            "arguments": {"project_id": "TestProject"},
        },
    }

    response = client.post("/mcp", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == "test-3"
    assert "result" in data

    # Verify the driver was called correctly
    mock_driver_class.assert_called_once_with(
        "https://test.polarion.com", "test@example.com", "test-token"
    )
    mock_driver_instance.select_project.assert_called_once_with("TestProject")
    mock_driver_instance.get_project_info.assert_called_once()


@patch("mcp_server.routers.mcp_endpoint.PolarionDriver")
@patch("mcp_server.routers.mcp_endpoint.settings")
def test_mcp_get_test_specs_from_document_success(
    mock_settings, mock_driver_class, client: TestClient
) -> None:
    """Test MCP tools/call for get_test_specs_from_document with successful response."""
    # Mock settings
    mock_settings.POLARION_URL = "https://test.polarion.com"
    mock_settings.POLARION_USER = "test@example.com"
    mock_settings.POLARION_TOKEN = "test-token"

    # Mock the driver and its methods
    mock_driver_instance = MagicMock()
    mock_driver_instance.__enter__ = MagicMock(return_value=mock_driver_instance)
    mock_driver_instance.__exit__ = MagicMock(return_value=None)

    # Mock document and test spec IDs
    mock_document = MagicMock()
    mock_document.title = "Test Specifications Document"
    mock_driver_instance.get_test_specs_doc.return_value = mock_document
    mock_driver_instance.test_spec_ids_in_doc.return_value = {
        "TEST-001",
        "TEST-002",
        "TEST-003",
    }

    mock_driver_class.return_value = mock_driver_instance

    request_data = {
        "jsonrpc": "2.0",
        "id": "test-4",
        "method": "tools/call",
        "params": {
            "name": "get_test_specs_from_document",
            "arguments": {"project_id": "TestProject", "document_id": "TEST-DOC-001"},
        },
    }

    response = client.post("/mcp", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == "test-4"
    assert "result" in data

    # Parse the result content
    result_content = json.loads(data["result"]["content"][0]["text"])
    assert result_content["document_id"] == "TEST-DOC-001"
    assert result_content["document_title"] == "Test Specifications Document"
    assert result_content["total_test_specs"] == 3
    assert set(result_content["test_spec_ids"]) == {"TEST-001", "TEST-002", "TEST-003"}

    # Verify the driver was called correctly
    mock_driver_class.assert_called_once_with(
        "https://test.polarion.com", "test@example.com", "test-token"
    )
    mock_driver_instance.select_project.assert_called_once_with("TestProject")
    mock_driver_instance.get_test_specs_doc.assert_called_once_with("TEST-DOC-001")
    mock_driver_instance.test_spec_ids_in_doc.assert_called_once_with(mock_document)


def test_mcp_invalid_method(client: TestClient) -> None:
    """Test MCP request with invalid method."""
    request_data = {
        "jsonrpc": "2.0",
        "id": "test-5",
        "method": "invalid_method",
        "params": {},
    }

    response = client.post("/mcp", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == "test-5"
    assert "error" in data
    assert data["error"]["code"] == -32600
    assert "Invalid request" in data["error"]["message"]


def test_mcp_invalid_json(client: TestClient) -> None:
    """Test MCP request with invalid JSON."""
    response = client.post("/mcp", data="invalid json")
    assert response.status_code == 200

    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] is None
    assert "error" in data
    assert data["error"]["code"] == -32700
    assert "Parse error" in data["error"]["message"]
