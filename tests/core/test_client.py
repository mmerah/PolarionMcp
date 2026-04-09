"""Tests for the Polarion driver core functionality."""

from unittest.mock import Mock, patch

import pytest

from polarion_mcp.core.client import PolarionDriver


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


def test_resolve_document_falls_back_to_bare_id() -> None:
    """Test resolving a document by bare ID through the document list."""
    driver = PolarionDriver(
        "https://test.com/polarion", "test@example.com", "test-token"
    )
    driver._project = Mock()

    matching_doc = Mock()
    matching_doc.id = "DOC-1"

    with patch.object(driver, "get_document", return_value=None):
        with patch.object(driver, "get_documents", return_value=[matching_doc]):
            assert driver.resolve_document("DOC-1") is matching_doc


def test_search_workitems_forwards_limit() -> None:
    """Test search_workitems forwards the explicit limit to Polarion."""
    driver = PolarionDriver(
        "https://test.com/polarion", "test@example.com", "test-token"
    )
    driver._project = Mock()
    driver._project.searchWorkitem.return_value = [{"id": "TEST-1", "title": "Item 1"}]

    with patch("zeep.helpers.serialize_object", side_effect=lambda item: item):
        results = driver.search_workitems("type:defect", ["id", "title"], limit=5)

    assert results == [{"id": "TEST-1", "title": "Item 1"}]
    driver._project.searchWorkitem.assert_called_once_with(
        query="type:defect",
        field_list=["id", "title"],
        limit=5,
    )


def test_export_document_pdf_writes_temp_file(tmp_path) -> None:
    """Test exporting a document PDF to a temp file path."""
    driver = PolarionDriver(
        "https://test.com/polarion", "test@example.com", "test-token"
    )

    document = Mock()
    document.id = "DOC-1"
    document.exportDocumentToPDF.return_value = b"%PDF-1.4 mock"

    with patch("tempfile.gettempdir", return_value=str(tmp_path)):
        pdf_path = driver.export_document_pdf(document)

    assert pdf_path.parent == tmp_path
    assert pdf_path.suffix == ".pdf"
    assert pdf_path.read_bytes() == b"%PDF-1.4 mock"
