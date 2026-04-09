"""Tests for the Polarion MCP server."""

import os
from unittest.mock import Mock, patch

import pytest
from polarion_mcp.core.settings import PolarionSettings


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
        with patch("polarion_mcp.mcp.tools.PolarionDriver") as mock_driver_class:
            mock_driver_instance = Mock()
            mock_driver_class.return_value.__enter__.return_value = mock_driver_instance
            mock_driver_class.return_value.__exit__.return_value = None
            yield mock_driver_instance

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_settings, mock_driver):
        """Test health check with successful connection."""
        import polarion_mcp.mcp.tools

        with patch("polarion_mcp.mcp.tools.settings", mock_settings):
            result = await polarion_mcp.mcp.tools.health_check.fn()
            assert "✅ Polarion connection is healthy." in result

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_settings):
        """Test health check with connection failure."""
        import polarion_mcp.mcp.tools
        from polarion_mcp.core.client import PolarionConnectionException

        with patch("polarion_mcp.mcp.tools.settings", mock_settings):
            with patch("polarion_mcp.mcp.tools.PolarionDriver") as mock_driver_class:
                mock_driver_class.return_value.__enter__.side_effect = (
                    PolarionConnectionException("Connection failed")
                )

                result = await polarion_mcp.mcp.tools.health_check.fn()
                assert "❌ Polarion connection failed:" in result

    @pytest.mark.asyncio
    async def test_get_project_info(self, mock_settings, mock_driver):
        """Test get_project_info tool."""
        import polarion_mcp.mcp.tools

        mock_driver.get_project_info.return_value = {
            "name": "Test Project",
            "description": "A test project",
        }

        with patch("polarion_mcp.mcp.tools.settings", mock_settings):
            result = await polarion_mcp.mcp.tools.get_project_info.fn("TEST_PROJECT")

            assert "Project Information for 'TEST_PROJECT'" in result
            assert "Name: Test Project" in result
            assert "Description: A test project" in result
            mock_driver.select_project.assert_called_once_with("TEST_PROJECT")

    @pytest.mark.asyncio
    async def test_get_workitem(self, mock_settings, mock_driver):
        """Test get_workitem tool."""
        import polarion_mcp.mcp.tools

        mock_item = Mock()
        mock_item.id = "TEST-123"
        mock_item.title = "Test Work Item"
        mock_item.type = Mock(id="requirement")
        mock_item.status = Mock(id="open")
        mock_item.author = Mock(id="test@example.com")
        mock_item.created = "2024-01-01"
        mock_item.description = Mock(content="Test description")

        mock_driver.get_workitem.return_value = mock_item

        with patch("polarion_mcp.mcp.tools.settings", mock_settings):
            result = await polarion_mcp.mcp.tools.get_workitem.fn(
                "TEST_PROJECT", "TEST-123"
            )

            assert "Work Item Details for 'TEST-123'" in result
            assert "ID: TEST-123" in result
            assert "Title: Test Work Item" in result
            mock_driver.select_project.assert_called_once_with("TEST_PROJECT")
            mock_driver.get_workitem.assert_called_once_with("TEST-123")

    @pytest.mark.asyncio
    async def test_get_workitem_multiple_ids_partial_failure(
        self, mock_settings, mock_driver
    ):
        """Test get_workitem can fetch multiple IDs with per-item error handling."""
        import polarion_mcp.mcp.tools

        item1 = Mock()
        item1.id = "TEST-123"
        item1.title = "First Item"
        item1.type = Mock(id="requirement")
        item1.status = Mock(id="open")
        item1.author = Mock(id="test@example.com")
        item1.created = "2024-01-01"
        item1.description = Mock(content="First description")

        def get_workitem_side_effect(workitem_id):
            if workitem_id == "TEST-123":
                return item1
            raise Exception("Not found")

        mock_driver.get_workitem.side_effect = get_workitem_side_effect

        with patch("polarion_mcp.mcp.tools.settings", mock_settings):
            result = await polarion_mcp.mcp.tools.get_workitem.fn(
                "TEST_PROJECT", ["TEST-123", "TEST-404"]
            )

            assert "Work Item Results (2 requested):" in result
            assert "Work Item Details for 'TEST-123':" in result
            assert "Title: First Item" in result
            assert "Work Item Details for 'TEST-404':" in result
            assert "Error: ❌ Failed to get work item: Not found" in result

    @pytest.mark.asyncio
    async def test_get_workitem_rejects_plan_projects(self, mock_settings, mock_driver):
        """Test get_workitem is rejected for plan projects."""
        import polarion_mcp.mcp.tools
        from polarion_mcp.core.config import ConfigManager

        mock_item = Mock()
        mock_item.id = "PLAN-123"
        mock_item.title = "Planned Item"
        mock_item.type = Mock(id="task")
        mock_item.status = Mock(id="open")
        mock_item.author = Mock(id="planner")
        mock_item.created = "2024-01-01"
        mock_item.description = Mock(content="Plan work item")
        mock_driver.get_workitem.return_value = mock_item

        mock_config = Mock(spec=ConfigManager)
        mock_config.resolve_project_id.return_value = "PLAN_PROJECT"
        mock_config.is_plan_project.return_value = True
        mock_config.get_custom_fields.return_value = None

        with patch("polarion_mcp.mcp.tools.settings", mock_settings):
            with patch("polarion_mcp.mcp.tools.config_manager", mock_config):
                result = await polarion_mcp.mcp.tools.get_workitem.fn(
                    "planning", "PLAN-123"
                )

                assert "not currently supported for plan projects" in result
                mock_driver.get_workitem.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_workitems(self, mock_settings, mock_driver):
        """Test search_workitems tool."""
        import polarion_mcp.mcp.tools

        # Mock driver now returns dictionaries with only requested fields
        mock_driver.search_workitems.return_value = [
            {"id": "TEST-123", "title": "Test Item 1"},
            {"id": "TEST-124", "title": "Test Item 2"},
        ]

        with patch("polarion_mcp.mcp.tools.settings", mock_settings):
            result = await polarion_mcp.mcp.tools.search_workitems.fn(
                "TEST_PROJECT", "type:requirement", "id,title"
            )

            assert "Found 2 work items" in result
            assert "TEST-123" in result
            assert "TEST-124" in result
            assert "Test Item 1" in result
            assert "Test Item 2" in result
            mock_driver.search_workitems.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_workitems_with_limit(self, mock_settings, mock_driver):
        """Test search_workitems forwards an explicit limit."""
        import polarion_mcp.mcp.tools

        mock_driver.search_workitems.return_value = [
            {"id": "TEST-123", "title": "Test Item 1"},
            {"id": "TEST-124", "title": "Test Item 2"},
            {"id": "TEST-125", "title": "Test Item 3"},
        ]

        with patch("polarion_mcp.mcp.tools.settings", mock_settings):
            result = await polarion_mcp.mcp.tools.search_workitems.fn(
                "TEST_PROJECT", "type:requirement", "id,title", 2
            )

            assert "Found 2 work items" in result
            assert "more exist" in result
            assert "more beyond the configured limit" in result
            mock_driver.search_workitems.assert_called_once_with(
                "type:requirement", ["id", "title"], limit=3
            )

    @pytest.mark.asyncio
    async def test_get_test_runs(self, mock_settings, mock_driver):
        """Test get_test_runs tool."""
        import polarion_mcp.mcp.tools

        mock_run1 = Mock(id="TR-1", title="Test Run 1", status="passed")
        mock_run2 = Mock(id="TR-2", title="Test Run 2", status="failed")
        mock_driver.get_test_runs.return_value = [mock_run1, mock_run2]

        with patch("polarion_mcp.mcp.tools.settings", mock_settings):
            result = await polarion_mcp.mcp.tools.get_test_runs.fn("TEST_PROJECT")

            assert "Found 2 test runs" in result
            assert "TR-1" in result
            assert "TR-2" in result

    @pytest.mark.asyncio
    async def test_get_documents(self, mock_settings, mock_driver):
        """Test get_documents tool."""
        import polarion_mcp.mcp.tools

        mock_doc1 = Mock(id="DOC-1", title="Document 1", moduleFolder="Specs")
        mock_doc2 = Mock(id="DOC-2", title="Document 2", moduleFolder="Tests")
        mock_driver.get_documents.return_value = [mock_doc1, mock_doc2]

        with patch("polarion_mcp.mcp.tools.settings", mock_settings):
            result = await polarion_mcp.mcp.tools.get_documents.fn("TEST_PROJECT")

            assert "Found 2 documents" in result
            assert "DOC-1" in result
            assert "DOC-2" in result
            assert "Path: Specs/DOC-1" in result

    @pytest.mark.asyncio
    async def test_get_documents_with_limit(self, mock_settings, mock_driver):
        """Test get_documents applies display limit."""
        import polarion_mcp.mcp.tools

        mock_driver.get_documents.return_value = [
            Mock(id="DOC-1", title="Document 1", moduleFolder="Specs"),
            Mock(id="DOC-2", title="Document 2", moduleFolder="Specs"),
            Mock(id="DOC-3", title="Document 3", moduleFolder="Specs"),
        ]

        with patch("polarion_mcp.mcp.tools.settings", mock_settings):
            result = await polarion_mcp.mcp.tools.get_documents.fn("TEST_PROJECT", 2)

            assert "Found 3 documents" in result
            assert "DOC-1" in result
            assert "DOC-2" in result
            assert "DOC-3" not in result
            assert "...and 1 more." in result

    @pytest.mark.asyncio
    async def test_get_document(self, mock_settings, mock_driver):
        """Test get_document tool exports a PDF."""
        import polarion_mcp.mcp.tools

        mock_doc = Mock(id="DOC-1", title="Document 1", moduleFolder="Specs")
        mock_doc.moduleName = "Regression"
        mock_driver.resolve_document.return_value = mock_doc
        mock_driver.export_document_pdf.return_value = "/tmp/polarion_DOC-1_test.pdf"

        with patch("polarion_mcp.mcp.tools.settings", mock_settings):
            result = await polarion_mcp.mcp.tools.get_document.fn(
                "TEST_PROJECT", "Specs/Regression"
            )

            assert isinstance(result, str)
            assert "Document Details for 'Specs/Regression':" in result
            assert "ID: DOC-1" in result
            assert "PDF Path: /tmp/polarion_DOC-1_test.pdf" in result
            assert "Download Path: /artifacts/" in result

    @pytest.mark.asyncio
    async def test_get_document_without_body(self, mock_settings, mock_driver):
        """Test get_document reports PDF export failures clearly."""
        import polarion_mcp.mcp.tools

        mock_doc = Mock(id="DOC-2", title="Document 2", moduleFolder="Specs")
        mock_doc.moduleName = "NoBody"
        mock_driver.resolve_document.return_value = mock_doc
        mock_driver.export_document_pdf.side_effect = Exception("Export failed")

        with patch("polarion_mcp.mcp.tools.settings", mock_settings):
            result = await polarion_mcp.mcp.tools.get_document.fn(
                "TEST_PROJECT", "Specs/NoBody"
            )

            assert "❌ Failed to get document: Export failed" in result

    @pytest.mark.asyncio
    async def test_search_workitems_with_named_query(self, mock_settings, mock_driver):
        """Test search_workitems with named query resolution."""
        import polarion_mcp.mcp.tools
        from polarion_mcp.core.config import ConfigManager

        # Mock config manager with named query
        mock_config = Mock(spec=ConfigManager)
        mock_config.resolve_project_id.return_value = "TEST_PROJECT"
        mock_config.resolve_query.return_value = "type:defect AND status:open"
        mock_config.get_display_fields.return_value = ["id", "title", "type", "status"]
        mock_config.is_plan_project.return_value = False  # Not a plan project

        # Return only the fields from get_display_fields
        mock_driver.search_workitems.return_value = [
            {
                "id": "TEST-123",
                "title": "Bug 1",
                "type": {"id": "defect"},
                "status": {"id": "open"},
            }
        ]

        with patch("polarion_mcp.mcp.tools.settings", mock_settings):
            with patch("polarion_mcp.mcp.tools.config_manager", mock_config):
                result = await polarion_mcp.mcp.tools.search_workitems.fn(
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
        import polarion_mcp.mcp.tools
        from polarion_mcp.core.config import ConfigManager

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
                "customFields.foundIn": "v1.2",
            }
        ]

        with patch("polarion_mcp.mcp.tools.settings", mock_settings):
            with patch("polarion_mcp.mcp.tools.config_manager", mock_config):
                # Explicitly provide field list including custom fields
                result = await polarion_mcp.mcp.tools.search_workitems.fn(
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
        import polarion_mcp.mcp.tools
        from polarion_mcp.core.config import ConfigManager

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

        with patch("polarion_mcp.mcp.tools.settings", mock_settings):
            with patch("polarion_mcp.mcp.tools.config_manager", mock_config):
                result = await polarion_mcp.mcp.tools.get_project_info.fn("webstore")

                assert "WEBSTORE_V3" in result
                assert "alias: webstore" in result
                mock_config.resolve_project_id.assert_called_once_with("webstore")
                mock_driver.select_project.assert_called_once_with("WEBSTORE_V3")
