"""Tests for the Polarion MCP stdio server."""

import os
from unittest.mock import Mock, patch

import pytest

from mcp_server.server import PolarionSettings


class TestPolarionSettings:
    """Test the PolarionSettings class."""

    def test_missing_polarion_url(self):
        """Test that PolarionSettings raises error when POLARION_URL is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ValueError, match="POLARION_URL environment variable is required"
            ):
                PolarionSettings(load_dotenv_file=False)

    def test_missing_polarion_user(self):
        """Test that PolarionSettings raises error when POLARION_USER is missing."""
        with patch.dict(os.environ, {"POLARION_URL": "https://test.com"}, clear=True):
            with pytest.raises(
                ValueError, match="POLARION_USER environment variable is required"
            ):
                PolarionSettings(load_dotenv_file=False)

    def test_missing_polarion_token(self):
        """Test that PolarionSettings raises error when POLARION_TOKEN is missing."""
        with patch.dict(
            os.environ,
            {"POLARION_URL": "https://test.com", "POLARION_USER": "test@example.com"},
            clear=True,
        ):
            with pytest.raises(
                ValueError, match="POLARION_TOKEN environment variable is required"
            ):
                PolarionSettings(load_dotenv_file=False)

    def test_valid_settings(self):
        """Test that PolarionSettings initializes correctly with all required env vars."""
        with patch.dict(
            os.environ,
            {
                "POLARION_URL": "https://test.com",
                "POLARION_USER": "test@example.com",
                "POLARION_TOKEN": "test-token",
            },
        ):
            settings = PolarionSettings(load_dotenv_file=False)
            assert settings.polarion_url == "https://test.com"
            assert settings.polarion_user == "test@example.com"
            assert settings.polarion_token == "test-token"


class TestToolHandlers:
    """Test the individual tool handlers."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=PolarionSettings)
        settings.polarion_url = "https://test.com"
        settings.polarion_user = "test@example.com"
        settings.polarion_token = "test-token"
        return settings

    @pytest.fixture
    def mock_driver(self):
        """Create a mock PolarionDriver."""
        with patch("mcp_server.server.PolarionDriver") as mock_driver_class:
            mock_driver_instance = Mock()
            mock_driver_class.return_value.__enter__.return_value = mock_driver_instance
            mock_driver_class.return_value.__exit__.return_value = None
            yield mock_driver_instance

    async def test_health_check_tool(self, mock_settings):
        """Test that health_check tool calls the correct handler."""
        from mcp_server.server import _handle_health_check

        # Test the handler directly - this is more meaningful than testing the call_tool function
        with patch("mcp_server.server.PolarionDriver") as mock_driver_class:
            mock_driver_class.return_value.__enter__.return_value = Mock()
            mock_driver_class.return_value.__exit__.return_value = None
            result = await _handle_health_check({}, mock_settings)
            assert len(result) == 1
            assert result[0].type == "text"
            assert "healthy" in result[0].text

    async def test_health_check_handler_success(self, mock_settings, mock_driver):
        """Test health check handler with successful connection."""
        from mcp_server.server import _handle_health_check

        result = await _handle_health_check({}, mock_settings)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "healthy" in result[0].text
        assert "Successfully connected to Polarion server" in result[0].text

    async def test_health_check_handler_failure(self, mock_settings):
        """Test health check handler with connection failure."""
        from mcp_server.server import _handle_health_check

        with patch("mcp_server.server.PolarionDriver") as mock_driver_class:
            # Make the driver raise an exception
            mock_driver_class.return_value.__enter__.side_effect = Exception(
                "Connection failed"
            )

            result = await _handle_health_check({}, mock_settings)

            assert len(result) == 1
            assert result[0].type == "text"
            assert "unhealthy" in result[0].text
            assert "Failed to connect to Polarion server" in result[0].text

    async def test_get_project_info_handler(self, mock_settings, mock_driver):
        """Test get_project_info handler."""
        from mcp_server.server import _handle_get_project_info

        # Mock the driver methods
        mock_driver.select_project = Mock()
        mock_driver.get_project_info = Mock(
            return_value={
                "id": "TEST_PROJECT",
                "name": "Test Project",
                "description": "A test project",
            }
        )

        arguments = {"project_id": "TEST_PROJECT"}
        result = await _handle_get_project_info(arguments, mock_settings)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "TEST_PROJECT" in result[0].text
        mock_driver.select_project.assert_called_once_with("TEST_PROJECT")
        mock_driver.get_project_info.assert_called_once()

    async def test_get_workitem_handler(self, mock_settings, mock_driver):
        """Test get_workitem handler."""
        from mcp_server.server import _handle_get_workitem

        # Mock workitem object
        mock_workitem = Mock()
        mock_workitem.id = "TEST-123"
        mock_workitem.title = "Test Work Item"
        mock_workitem.description = "A test work item"
        mock_workitem.type = "requirement"
        mock_workitem.status = "open"
        mock_workitem.author = "test@example.com"
        mock_workitem.created = "2024-01-01"
        mock_workitem.updated = "2024-01-02"

        mock_driver.select_project = Mock()
        mock_driver.get_workitem = Mock(return_value=mock_workitem)

        arguments = {"project_id": "TEST_PROJECT", "workitem_id": "TEST-123"}
        result = await _handle_get_workitem(arguments, mock_settings)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "TEST-123" in result[0].text
        mock_driver.select_project.assert_called_once_with("TEST_PROJECT")
        mock_driver.get_workitem.assert_called_once_with("TEST-123")

    async def test_search_workitems_handler(self, mock_settings, mock_driver):
        """Test search_workitems handler."""
        from mcp_server.server import _handle_search_workitems

        mock_driver.select_project = Mock()
        mock_driver.search_workitems = Mock(
            return_value=[
                {"id": "TEST-123", "title": "Test Item 1"},
                {"id": "TEST-124", "title": "Test Item 2"},
            ]
        )

        arguments = {
            "project_id": "TEST_PROJECT",
            "query": "type:requirement",
            "field_list": ["id", "title"],
        }
        result = await _handle_search_workitems(arguments, mock_settings)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "TEST-123" in result[0].text
        assert "TEST-124" in result[0].text
        mock_driver.select_project.assert_called_once_with("TEST_PROJECT")
        mock_driver.search_workitems.assert_called_once_with(
            "type:requirement", ["id", "title"]
        )

    async def test_get_test_runs_handler(self, mock_settings, mock_driver):
        """Test get_test_runs handler."""
        from mcp_server.server import _handle_get_test_runs

        mock_driver.select_project = Mock()
        mock_driver.get_test_runs = Mock(
            return_value=[
                {"id": "TR-1", "title": "Test Run 1", "status": "passed"},
                {"id": "TR-2", "title": "Test Run 2", "status": "failed"},
            ]
        )

        arguments = {"project_id": "TEST_PROJECT"}
        result = await _handle_get_test_runs(arguments, mock_settings)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "TR-1" in result[0].text
        assert "TR-2" in result[0].text
        mock_driver.select_project.assert_called_once_with("TEST_PROJECT")
        mock_driver.get_test_runs.assert_called_once()

    async def test_get_test_run_handler(self, mock_settings, mock_driver):
        """Test get_test_run handler."""
        from mcp_server.server import _handle_get_test_run

        # Mock test run object
        mock_test_run = Mock()
        mock_test_run.id = "TR-123"
        mock_test_run.title = "Test Run 123"
        mock_test_run.status = "passed"
        mock_test_run.created = "2024-01-01"
        mock_test_run.updated = "2024-01-02"
        mock_test_run.description = "A test run"

        mock_driver.select_project = Mock()
        mock_driver.get_test_run = Mock(return_value=mock_test_run)

        arguments = {"project_id": "TEST_PROJECT", "test_run_id": "TR-123"}
        result = await _handle_get_test_run(arguments, mock_settings)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "TR-123" in result[0].text
        mock_driver.select_project.assert_called_once_with("TEST_PROJECT")
        mock_driver.get_test_run.assert_called_once_with("TR-123")

    async def test_get_test_run_handler_not_found(self, mock_settings, mock_driver):
        """Test get_test_run handler when test run is not found."""
        from mcp_server.server import _handle_get_test_run

        mock_driver.select_project = Mock()
        mock_driver.get_test_run = Mock(return_value=None)

        arguments = {"project_id": "TEST_PROJECT", "test_run_id": "TR-999"}
        result = await _handle_get_test_run(arguments, mock_settings)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "TR-999 not found" in result[0].text

    async def test_get_documents_handler(self, mock_settings, mock_driver):
        """Test get_documents handler."""
        from mcp_server.server import _handle_get_documents

        # Mock document objects
        mock_doc1 = Mock()
        mock_doc1.id = "DOC-1"
        mock_doc1.title = "Document 1"
        mock_doc1.type = "testSpecification"
        mock_doc1.created = "2024-01-01"
        mock_doc1.updated = "2024-01-02"

        mock_doc2 = Mock()
        mock_doc2.id = "DOC-2"
        mock_doc2.title = "Document 2"
        mock_doc2.type = "requirement"
        mock_doc2.created = "2024-01-01"
        mock_doc2.updated = "2024-01-02"

        mock_driver.select_project = Mock()
        mock_driver.get_documents = Mock(return_value=[mock_doc1, mock_doc2])

        arguments = {"project_id": "TEST_PROJECT"}
        result = await _handle_get_documents(arguments, mock_settings)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "DOC-1" in result[0].text
        assert "DOC-2" in result[0].text
        mock_driver.select_project.assert_called_once_with("TEST_PROJECT")
        mock_driver.get_documents.assert_called_once()

    async def test_get_test_specs_from_document_handler(
        self, mock_settings, mock_driver
    ):
        """Test get_test_specs_from_document handler."""
        from mcp_server.server import _handle_get_test_specs_from_document

        mock_doc = Mock()
        mock_driver.select_project = Mock()
        mock_driver.get_test_specs_doc = Mock(return_value=mock_doc)
        mock_driver.test_spec_ids_in_doc = Mock(
            return_value={"TEST-1", "TEST-2", "TEST-3"}
        )

        arguments = {"project_id": "TEST_PROJECT", "document_id": "DOC-1"}
        result = await _handle_get_test_specs_from_document(arguments, mock_settings)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "TEST-1" in result[0].text
        assert "TEST-2" in result[0].text
        assert "TEST-3" in result[0].text
        mock_driver.select_project.assert_called_once_with("TEST_PROJECT")
        mock_driver.get_test_specs_doc.assert_called_once_with("DOC-1")
        mock_driver.test_spec_ids_in_doc.assert_called_once_with(mock_doc)

    async def test_get_test_specs_from_document_handler_not_found(
        self, mock_settings, mock_driver
    ):
        """Test get_test_specs_from_document handler when document is not found."""
        from mcp_server.server import _handle_get_test_specs_from_document

        mock_driver.select_project = Mock()
        mock_driver.get_test_specs_doc = Mock(return_value=None)

        arguments = {"project_id": "TEST_PROJECT", "document_id": "DOC-999"}
        result = await _handle_get_test_specs_from_document(arguments, mock_settings)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "DOC-999 not found" in result[0].text
