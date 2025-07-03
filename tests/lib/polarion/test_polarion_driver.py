"""Tests for the Polarion driver core functionality."""

import os

import pytest

from lib.polarion.polarion_driver import PolarionDriver


def test_polarion_driver_missing_env_vars() -> None:
    """Test that PolarionDriver fails fast when required env vars are missing."""
    # Save original values
    orig_values = {}
    for var in ["POLARION_URL", "POLARION_USER", "POLARION_TOKEN"]:
        orig_values[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]

    try:
        with pytest.raises(ValueError, match="Polarion user name should not be None"):
            PolarionDriver("https://test.example.com")
    finally:
        # Restore original values
        for var, value in orig_values.items():
            if value is not None:
                os.environ[var] = value


def test_polarion_driver_with_valid_config() -> None:
    """Test that PolarionDriver initializes with valid configuration."""
    orig_values = {}
    for var in ["POLARION_URL", "POLARION_USER", "POLARION_TOKEN"]:
        orig_values[var] = os.environ.get(var)

    try:
        os.environ["POLARION_URL"] = "https://test.com/polarion"
        os.environ["POLARION_USER"] = "test@example.com"
        os.environ["POLARION_TOKEN"] = "test-token"

        driver = PolarionDriver("https://test.com/polarion")
        assert driver._url == "https://test.com/polarion"
        assert driver._user == "test@example.com"
        assert driver._token == "test-token"
    finally:
        # Restore original values
        for var, value in orig_values.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]
