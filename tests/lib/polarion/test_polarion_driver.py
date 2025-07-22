"""Tests for the Polarion driver core functionality."""

import pytest

from lib.polarion.polarion_driver import PolarionDriver


def test_polarion_driver_missing_user() -> None:
    """Test that PolarionDriver fails fast when user is missing."""
    with pytest.raises(ValueError, match="Polarion user name must be provided"):
        PolarionDriver("https://test.example.com", "", "test-token")


def test_polarion_driver_missing_token() -> None:
    """Test that PolarionDriver fails fast when token is missing."""
    with pytest.raises(ValueError, match="Polarion token must be provided"):
        PolarionDriver("https://test.example.com", "test@example.com", "")


def test_polarion_driver_with_valid_config() -> None:
    """Test that PolarionDriver initializes with valid configuration."""
    driver = PolarionDriver(
        "https://test.com/polarion", "test@example.com", "test-token"
    )
    assert driver._url == "https://test.com/polarion"
    assert driver._user == "test@example.com"
    assert driver._token == "test-token"
