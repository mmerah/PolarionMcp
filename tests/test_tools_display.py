"""Test the field display functionality in tools.py"""

import pytest
from unittest.mock import Mock, patch
from mcp_server.config import ConfigManager


@pytest.mark.asyncio
async def test_get_project_types_field_display():
    """Test that get_project_types shows all fields correctly."""
    import mcp_server.tools

    # Mock config manager
    mock_config_manager = Mock(spec=ConfigManager)
    mock_project_config = Mock()
    mock_project_config.name = "Test Project"
    mock_project_config.work_item_types = ["defect", "requirement"]
    mock_config_manager.get_project_config.return_value = mock_project_config
    mock_config_manager.get_combined_fields.side_effect = [
        ["id", "title", "status", "customFields.severity", "customFields.priority"],
        ["id", "title", "status", "customFields.businessValue"],
    ]

    with patch("mcp_server.tools.config_manager", mock_config_manager):
        result = await mcp_server.tools.get_project_types.fn("testproj")

        # Verify output structure
        assert "Work Item Types for 'Test Project'" in result
        assert "- defect" in result
        assert "- requirement" in result

        # Verify standard fields are shown
        assert "Standard fields: id, title, status" in result

        # Verify custom fields are shown as "Additional"
        assert "Additional custom fields: severity, priority" in result
        assert "Additional custom fields: businessValue" in result

        # Verify get_combined_fields was called for each type
        assert mock_config_manager.get_combined_fields.call_count == 2
        mock_config_manager.get_combined_fields.assert_any_call("testproj", "defect")
        mock_config_manager.get_combined_fields.assert_any_call(
            "testproj", "requirement"
        )


@pytest.mark.asyncio
async def test_discover_work_item_types_configured_field_display():
    """Test that discover_work_item_types shows all fields when configured."""
    import mcp_server.tools

    # Mock config manager with configured types
    mock_config_manager = Mock(spec=ConfigManager)
    mock_config_manager.resolve_project_id.return_value = "TEST_PROJ"
    mock_config_manager.get_work_item_types.return_value = ["defect", "task"]
    mock_config_manager.get_combined_fields.side_effect = [
        ["id", "title", "status", "assignee", "customFields.severity"],
        ["id", "title", "status", "assignee", "customFields.storyPoints"],
    ]

    with patch("mcp_server.tools.config_manager", mock_config_manager):
        result = await mcp_server.tools.discover_work_item_types.fn("testproj")

        # Verify output structure for configured types
        assert "Work Item Types for 'TEST_PROJ' (from configuration)" in result
        assert "- defect" in result
        assert "- task" in result

        # Verify fields are shown correctly
        assert "Standard fields: id, title, status, assignee" in result
        assert "Additional custom fields: severity" in result
        assert "Additional custom fields: storyPoints" in result

        # Verify it didn't try to query Polarion (since types are configured)
        assert "Total: 2 configured types" in result


@pytest.mark.asyncio
async def test_field_display_no_custom_fields():
    """Test field display when there are no custom fields configured."""
    import mcp_server.tools

    # Mock config manager with no custom fields
    mock_config_manager = Mock(spec=ConfigManager)
    mock_config_manager.get_project_config.return_value = Mock(
        name="Simple Project", work_item_types=["task"]
    )
    mock_config_manager.get_combined_fields.return_value = [
        "id",
        "title",
        "status",
        "type",
    ]

    with patch("mcp_server.tools.config_manager", mock_config_manager):
        result = await mcp_server.tools.get_project_types.fn("simple")

        # Verify standard fields are shown
        assert "Standard fields: id, title, status, type" in result

        # Verify no "Additional custom fields" line appears
        assert "Additional custom fields:" not in result
