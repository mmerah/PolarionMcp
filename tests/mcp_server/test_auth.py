"""Tests for authentication functionality."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.security import APIKeyHeader

from mcp_server.auth import API_KEY_HEADER, get_api_key


def test_api_key_header_configuration() -> None:
    """Test that API key header is properly configured."""
    assert isinstance(API_KEY_HEADER, APIKeyHeader)
    # Test that the header configuration has the right name
    assert hasattr(API_KEY_HEADER, "model")
    assert API_KEY_HEADER.model.name == "X-API-Key"


@patch("mcp_server.auth.settings")
def test_get_api_key_valid(mock_settings) -> None:
    """Test that valid API key is accepted."""
    mock_settings.MCP_SERVER_API_KEY = "test-api-key"

    # Should return the API key when valid
    result = get_api_key("test-api-key")
    assert result == "test-api-key"


@patch("mcp_server.auth.settings")
def test_get_api_key_invalid(mock_settings) -> None:
    """Test that invalid API key raises HTTPException."""
    mock_settings.MCP_SERVER_API_KEY = "correct-api-key"

    with pytest.raises(HTTPException) as exc_info:
        get_api_key("wrong-api-key")

    assert exc_info.value.status_code == 401
    assert "Invalid API Key" in exc_info.value.detail


def test_get_api_key_missing() -> None:
    """Test that missing API key raises HTTPException."""
    with pytest.raises(HTTPException) as exc_info:
        get_api_key(None)

    assert exc_info.value.status_code == 401
    assert "API Key is missing" in exc_info.value.detail
