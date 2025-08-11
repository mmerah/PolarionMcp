"""Test the improved get_workitem functionality with custom fields and error handling."""

import pytest
from unittest.mock import Mock, patch
from mcp_server.config import ConfigManager


@pytest.mark.asyncio
async def test_get_workitem_with_custom_fields():
    """Test get_workitem includes custom fields for the work item type."""
    import mcp_server.tools
    from mcp_server.settings import PolarionSettings

    mock_settings = Mock(spec=PolarionSettings)
    mock_settings.polarion_url = "https://test.com"
    mock_settings.polarion_user = "test@example.com"
    mock_settings.polarion_token = "test-token"

    # Mock work item with custom fields
    mock_item = Mock()
    mock_item.id = "TEST-123"
    mock_item.title = "Test Requirement"
    mock_item.type = Mock(id="systemRequirement")
    mock_item.status = Mock(id="open")
    mock_item.author = Mock(id="test@example.com")
    mock_item.created = "2024-01-01"
    mock_item.description = Mock(content="Test description")

    # Set up getCustomField method to return proper values
    def get_custom_field(field_name):
        custom_values = {
            "acceptanceCriteria": "Must pass all tests",
            "riskRelevance": "High",
        }
        return custom_values.get(field_name)
    
    mock_item.getCustomField = Mock(side_effect=get_custom_field)

    # Mock config manager
    mock_config = Mock(spec=ConfigManager)
    mock_config.resolve_project_id.return_value = "TEST_PROJECT"
    mock_config.get_custom_fields.return_value = [
        "acceptanceCriteria",
        "riskRelevance",
        "importance",
    ]
    mock_config.is_plan_project.return_value = False  # Not a plan project

    with patch("mcp_server.tools.PolarionDriver") as mock_driver_class:
        mock_driver = Mock()
        mock_driver_class.return_value.__enter__.return_value = mock_driver
        mock_driver.get_workitem.return_value = mock_item

        with patch("mcp_server.tools.settings", mock_settings):
            with patch("mcp_server.tools.config_manager", mock_config):
                result = await mcp_server.tools.get_workitem.fn(
                    "TEST_PROJECT", "TEST-123"
                )

                # Verify standard fields
                assert "ID: TEST-123" in result
                assert "Title: Test Requirement" in result
                assert "Type: systemRequirement" in result
                assert "Status: open" in result

                # Verify custom fields are included
                assert "Custom.acceptanceCriteria: Must pass all tests" in result
                assert "Custom.riskRelevance: High" in result

                # Verify missing custom field is not shown
                assert "Custom.importance" not in result


@pytest.mark.asyncio
async def test_get_workitem_with_error_handling():
    """Test get_workitem handles errors gracefully when accessing fields."""
    import mcp_server.tools
    from mcp_server.settings import PolarionSettings

    mock_settings = Mock(spec=PolarionSettings)
    mock_settings.polarion_url = "https://test.com"
    mock_settings.polarion_user = "test@example.com"
    mock_settings.polarion_token = "test-token"

    # Mock work item with some fields that raise errors
    mock_item = Mock()
    mock_item.id = "TEST-456"
    mock_item.title = "Test Item"
    mock_item.type = Mock(id="defect")

    # Make status raise an exception when accessing id
    mock_status = Mock()
    type(mock_status).id = property(
        lambda self: (_ for _ in ()).throw(Exception("Status error"))
    )
    mock_item.status = mock_status

    mock_item.author = Mock(id="john.doe")
    mock_item.created = "2024-01-02"
    mock_item.description = Mock(content="Working description")

    # Mock getCustomField method that causes an error for custom fields
    def get_custom_field_error(field_name):
        raise Exception(f"Custom field {field_name} error")

    mock_item.getCustomField = Mock(side_effect=get_custom_field_error)

    # Mock config manager
    mock_config = Mock(spec=ConfigManager)
    mock_config.resolve_project_id.return_value = "TEST_PROJECT"
    mock_config.get_custom_fields.return_value = ["severity", "priority"]
    mock_config.is_plan_project.return_value = False  # Not a plan project

    with patch("mcp_server.tools.PolarionDriver") as mock_driver_class:
        mock_driver = Mock()
        mock_driver_class.return_value.__enter__.return_value = mock_driver
        mock_driver.get_workitem.return_value = mock_item

        with patch("mcp_server.tools.settings", mock_settings):
            with patch("mcp_server.tools.config_manager", mock_config):
                result = await mcp_server.tools.get_workitem.fn(
                    "TEST_PROJECT", "TEST-456"
                )

                # Verify fields that work are included
                assert "ID: TEST-456" in result
                assert "Title: Test Item" in result
                assert "Type: defect" in result
                assert "Author: john.doe" in result
                assert "Description: Working description" in result

                # Verify fields that error show N/A
                assert "Status: N/A" in result

                # Verify custom fields are not shown when they error
                assert "Custom.severity" not in result
                assert "Custom.priority" not in result


@pytest.mark.asyncio
async def test_get_workitem_no_custom_fields():
    """Test get_workitem when work item type has no custom fields configured."""
    import mcp_server.tools
    from mcp_server.settings import PolarionSettings

    mock_settings = Mock(spec=PolarionSettings)
    mock_settings.polarion_url = "https://test.com"
    mock_settings.polarion_user = "test@example.com"
    mock_settings.polarion_token = "test-token"

    # Mock work item
    mock_item = Mock()
    mock_item.id = "TEST-789"
    mock_item.title = "Simple Task"
    mock_item.type = Mock(id="task")
    mock_item.status = Mock(id="done")
    mock_item.author = Mock(id="jane.doe")
    mock_item.created = "2024-01-03"
    mock_item.description = Mock(content="Task description")

    # Mock config manager with no custom fields for 'task' type
    mock_config = Mock(spec=ConfigManager)
    mock_config.resolve_project_id.return_value = "TEST_PROJECT"
    mock_config.get_custom_fields.return_value = None  # No custom fields configured
    mock_config.is_plan_project.return_value = False  # Not a plan project

    with patch("mcp_server.tools.PolarionDriver") as mock_driver_class:
        mock_driver = Mock()
        mock_driver_class.return_value.__enter__.return_value = mock_driver
        mock_driver.get_workitem.return_value = mock_item

        with patch("mcp_server.tools.settings", mock_settings):
            with patch("mcp_server.tools.config_manager", mock_config):
                result = await mcp_server.tools.get_workitem.fn(
                    "TEST_PROJECT", "TEST-789"
                )

                # Verify standard fields
                assert "ID: TEST-789" in result
                assert "Title: Simple Task" in result
                assert "Type: task" in result
                assert "Status: done" in result
                assert "Author: jane.doe" in result

                # Verify no custom fields are shown
                assert "Custom." not in result
