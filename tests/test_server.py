"""Tests for the Polarion MCP server."""

import os
from unittest.mock import Mock, patch

import pytest

from mcp_server.settings import PolarionSettings


class TestTools:
    """Test the MCP tools."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        with patch.dict(
            os.environ,
            {
                "POLARION_URL": "https://test.com",
                "POLARION_USER": "test@example.com",
                "POLARION_TOKEN": "test-token",
            },
            clear=True,
        ):
            yield PolarionSettings()

    @pytest.fixture
    def mock_driver(self):
        """Create a mock PolarionDriver."""
        with patch("mcp_server.tools.PolarionDriver") as mock_driver_class:
            mock_driver_instance = Mock()
            mock_driver_class.return_value.__enter__.return_value = mock_driver_instance
            mock_driver_class.return_value.__exit__.return_value = None
            yield mock_driver_instance

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_settings, mock_driver):
        """Test health check with successful connection."""
        # Import the actual function, not the decorated tool
        import mcp_server.tools

        with patch("mcp_server.tools.settings", mock_settings):
            # Call the actual function directly
            result = await mcp_server.tools.health_check.fn()
            assert "✅ Polarion connection is healthy." in result

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_settings):
        """Test health check with connection failure."""
        import mcp_server.tools
        from lib.polarion.polarion_driver import PolarionConnectionException

        with patch("mcp_server.tools.settings", mock_settings):
            with patch("mcp_server.tools.PolarionDriver") as mock_driver_class:
                mock_driver_class.return_value.__enter__.side_effect = (
                    PolarionConnectionException("Connection failed")
                )

                result = await mcp_server.tools.health_check.fn()
                assert "❌ Polarion connection failed:" in result

    @pytest.mark.asyncio
    async def test_get_project_info(self, mock_settings, mock_driver):
        """Test get_project_info tool."""
        import mcp_server.tools

        mock_driver.get_project_info.return_value = {
            "name": "Test Project",
            "description": "A test project",
        }

        with patch("mcp_server.tools.settings", mock_settings):
            result = await mcp_server.tools.get_project_info.fn("TEST_PROJECT")

            assert "Project Information for 'TEST_PROJECT'" in result
            assert "Name: Test Project" in result
            assert "Description: A test project" in result
            mock_driver.select_project.assert_called_once_with("TEST_PROJECT")

    @pytest.mark.asyncio
    async def test_get_workitem(self, mock_settings, mock_driver):
        """Test get_workitem tool."""
        import mcp_server.tools

        mock_item = Mock()
        mock_item.id = "TEST-123"
        mock_item.title = "Test Work Item"
        mock_item.type = Mock(id="requirement")
        mock_item.status = Mock(id="open")
        mock_item.author = Mock(id="test@example.com")
        mock_item.created = "2024-01-01"
        mock_item.description = Mock(content="Test description")

        mock_driver.get_workitem.return_value = mock_item

        with patch("mcp_server.tools.settings", mock_settings):
            result = await mcp_server.tools.get_workitem.fn("TEST_PROJECT", "TEST-123")

            assert "Work Item Details for 'TEST-123'" in result
            assert "ID: TEST-123" in result
            assert "Title: Test Work Item" in result
            mock_driver.select_project.assert_called_once_with("TEST_PROJECT")
            mock_driver.get_workitem.assert_called_once_with("TEST-123")

    @pytest.mark.asyncio
    async def test_search_workitems(self, mock_settings, mock_driver):
        """Test search_workitems tool."""
        import mcp_server.tools

        # Mock driver now returns dictionaries with only requested fields
        mock_driver.search_workitems.return_value = [
            {"id": "TEST-123", "title": "Test Item 1"},
            {"id": "TEST-124", "title": "Test Item 2"}
        ]

        with patch("mcp_server.tools.settings", mock_settings):
            result = await mcp_server.tools.search_workitems.fn(
                "TEST_PROJECT", "type:requirement", "id,title"
            )

            assert "Found 2 work items" in result
            assert "TEST-123" in result
            assert "TEST-124" in result
            assert "Test Item 1" in result
            assert "Test Item 2" in result
            mock_driver.search_workitems.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_test_runs(self, mock_settings, mock_driver):
        """Test get_test_runs tool."""
        import mcp_server.tools

        mock_run1 = Mock(id="TR-1", title="Test Run 1", status="passed")
        mock_run2 = Mock(id="TR-2", title="Test Run 2", status="failed")
        mock_driver.get_test_runs.return_value = [mock_run1, mock_run2]

        with patch("mcp_server.tools.settings", mock_settings):
            result = await mcp_server.tools.get_test_runs.fn("TEST_PROJECT")

            assert "Found 2 test runs" in result
            assert "TR-1" in result
            assert "TR-2" in result

    @pytest.mark.asyncio
    async def test_get_documents(self, mock_settings, mock_driver):
        """Test get_documents tool."""
        import mcp_server.tools

        mock_doc1 = Mock(id="DOC-1", title="Document 1", moduleFolder="Specs")
        mock_doc2 = Mock(id="DOC-2", title="Document 2", moduleFolder="Tests")
        mock_driver.get_documents.return_value = [mock_doc1, mock_doc2]

        with patch("mcp_server.tools.settings", mock_settings):
            result = await mcp_server.tools.get_documents.fn("TEST_PROJECT")

            assert "Found 2 documents" in result
            assert "DOC-1" in result
            assert "DOC-2" in result

    @pytest.mark.asyncio
    async def test_search_workitems_with_named_query(self, mock_settings, mock_driver):
        """Test search_workitems with named query resolution."""
        import mcp_server.tools
        from mcp_server.config import ConfigManager

        # Mock config manager with named query
        mock_config = Mock(spec=ConfigManager)
        mock_config.resolve_project_id.return_value = "TEST_PROJECT"
        mock_config.resolve_query.return_value = "type:defect AND status:open"
        mock_config.get_display_fields.return_value = ["id", "title", "type", "status"]
        mock_config.is_plan_project.return_value = False  # Not a plan project

        # Return only the fields from get_display_fields
        mock_driver.search_workitems.return_value = [
            {"id": "TEST-123", "title": "Bug 1", "type": {"id": "defect"}, "status": {"id": "open"}}
        ]

        with patch("mcp_server.tools.settings", mock_settings):
            with patch("mcp_server.tools.config_manager", mock_config):
                result = await mcp_server.tools.search_workitems.fn(
                    "webstore", "query:open_bugs"
                )

                assert "Found 1 work items" in result
                assert "TEST-123" in result
                mock_config.resolve_query.assert_called_once_with(
                    "webstore", "query:open_bugs"
                )

    @pytest.mark.asyncio
    async def test_search_workitems_with_explicit_fields(
        self, mock_settings, mock_driver
    ):
        """Test search_workitems with explicitly provided field list."""
        import mcp_server.tools
        from mcp_server.config import ConfigManager

        # Mock config manager
        mock_config = Mock(spec=ConfigManager)
        mock_config.resolve_project_id.return_value = "TEST_PROJECT"
        mock_config.resolve_query.return_value = "type:defect AND status:open"
        mock_config.get_display_fields.return_value = [
            "id",
            "title",
            "status",
        ]  # Not used when field_list provided
        mock_config.is_plan_project.return_value = False  # Not a plan project

        # Mock returns only the explicitly requested fields
        mock_driver.search_workitems.return_value = [
            {
                "id": "TEST-123",
                "title": "Bug 1", 
                "status": {"id": "open"},
                "customFields.severity": "high",
                "customFields.foundIn": "v1.2"
            }
        ]

        with patch("mcp_server.tools.settings", mock_settings):
            with patch("mcp_server.tools.config_manager", mock_config):
                # Explicitly provide field list including custom fields
                result = await mcp_server.tools.search_workitems.fn(
                    "webstore",
                    "type:defect AND status:open",
                    "id,title,status,customFields.severity,customFields.foundIn",
                )

                assert "Found 1 work items" in result
                assert "TEST-123" in result
                # Now with individual custom fields as we requested them
                assert "customFields.severity: high" in result
                assert "customFields.foundIn: v1.2" in result
                # Verify get_display_fields was NOT called since field_list was provided
                mock_config.get_display_fields.assert_not_called()

    @pytest.mark.asyncio
    async def test_project_alias_resolution(self, mock_settings, mock_driver):
        """Test that project aliases are resolved to actual IDs."""
        import mcp_server.tools
        from mcp_server.config import ConfigManager

        # Mock config manager with alias resolution
        mock_config = Mock(spec=ConfigManager)
        mock_config.resolve_project_id.return_value = "WEBSTORE_V3"
        mock_config.get_project_config.return_value = Mock(
            name="Web Store", work_item_types=["defect", "requirement"]
        )

        mock_driver.get_project_info.return_value = {
            "name": "Web Store Project",
            "description": "E-commerce platform",
        }

        with patch("mcp_server.tools.settings", mock_settings):
            with patch("mcp_server.tools.config_manager", mock_config):
                result = await mcp_server.tools.get_project_info.fn("webstore")

                assert "WEBSTORE_V3" in result
                assert "alias: webstore" in result
                mock_config.resolve_project_id.assert_called_once_with("webstore")
                mock_driver.select_project.assert_called_once_with("WEBSTORE_V3")
