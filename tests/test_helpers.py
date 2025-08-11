"""Unit tests for helper functions."""

from unittest.mock import Mock

import pytest

from mcp_server.config import ConfigManager
from mcp_server.helpers import (
    extract_workitem_fields,
    format_search_result,
    format_search_results,
    format_workitem_details,
)


class TestExtractWorkitemFields:
    """Test the extract_workitem_fields helper function."""

    def test_extract_basic_fields(self):
        """Test extraction of basic work item fields."""
        mock_item = Mock()
        mock_item.id = "TEST-123"
        mock_item.title = "Test Item"
        mock_item.type = Mock(id="defect")
        mock_item.status = Mock(id="open")
        mock_item.author = Mock(id="john.doe")
        mock_item.created = "2024-01-01"
        mock_item.description = Mock(content="Test description")

        mock_config = Mock(spec=ConfigManager)
        mock_config.get_custom_fields.return_value = None

        details = extract_workitem_fields(mock_item, "test_project", mock_config)

        assert details["ID"] == "TEST-123"
        assert details["Title"] == "Test Item"
        assert details["Type"] == "defect"
        assert details["Status"] == "open"
        assert details["Author"] == "john.doe"
        assert details["Created"] == "2024-01-01"
        assert details["Description"] == "Test description"

    def test_extract_with_custom_fields(self):
        """Test extraction including custom fields."""
        mock_item = Mock()
        mock_item.id = "TEST-456"
        mock_item.title = "Test Requirement"
        mock_item.type = Mock(id="requirement")
        mock_item.status = Mock(id="draft")

        # Set up getCustomField method to return proper values
        def get_custom_field(field_name):
            custom_values = {
                "priority": "high",
                "businessValue": "critical",
            }
            return custom_values.get(field_name)
        
        mock_item.getCustomField = Mock(side_effect=get_custom_field)

        mock_config = Mock(spec=ConfigManager)
        mock_config.get_custom_fields.return_value = [
            "priority",
            "businessValue",
            "missingField",
        ]

        details = extract_workitem_fields(mock_item, "test_project", mock_config)

        assert details["Custom.priority"] == "high"
        assert details["Custom.businessValue"] == "critical"
        assert "Custom.missingField" not in details

    def test_extract_with_field_errors(self):
        """Test extraction handles field access errors gracefully."""
        mock_item = Mock()
        mock_item.id = "TEST-789"
        mock_item.title = "Test Item"
        mock_item.type = Mock(id="task")

        # Make status raise an error
        mock_status = Mock()
        type(mock_status).id = property(
            lambda self: (_ for _ in ()).throw(Exception("Status error"))
        )
        mock_item.status = mock_status

        mock_config = Mock(spec=ConfigManager)
        mock_config.get_custom_fields.return_value = None

        details = extract_workitem_fields(mock_item, "test_project", mock_config)

        assert details["ID"] == "TEST-789"
        assert details["Title"] == "Test Item"
        assert details["Status"] == "N/A"  # Should be N/A due to error


class TestFormatWorkitemDetails:
    """Test the format_workitem_details helper function."""

    def test_format_details(self):
        """Test formatting of work item details."""
        details = {
            "ID": "TEST-123",
            "Title": "Test Item",
            "Status": "open",
            "Custom.severity": "high",
        }

        result = format_workitem_details(details, "TEST-123")

        assert "Work Item Details for 'TEST-123':" in result
        assert "- ID: TEST-123" in result
        assert "- Title: Test Item" in result
        assert "- Status: open" in result
        assert "- Custom.severity: high" in result


class TestFormatSearchResult:
    """Test the format_search_result helper function."""

    def test_format_simple_dict(self):
        """Test formatting of a simple dictionary result."""
        item = {
            "id": "TEST-123",
            "title": "Test Item",
            "status": {"id": "open"},
            "priority": "high",
        }

        # Test with specific requested fields
        result = format_search_result(item, ["id", "title", "status"])

        assert "id: TEST-123" in result
        assert "title: Test Item" in result
        assert "status: open" in result
        assert "priority: high" not in result  # Not requested

    def test_format_with_custom_fields(self):
        """Test formatting with customFields dictionary."""
        item = {
            "id": "TEST-456",
            "title": "Test Bug",
            "customFields": {"severity": "critical", "foundIn": "v1.0"},
        }

        result = format_search_result(item, ["id", "title", "customFields"])

        assert "id: TEST-456" in result
        assert "title: Test Bug" in result
        assert "customFields: {'severity': 'critical', 'foundIn': 'v1.0'}" in result

    def test_format_with_null_values(self):
        """Test formatting skips null values."""
        item = {
            "id": "TEST-789",
            "title": None,
            "description": "Has value",
        }

        result = format_search_result(item, ["id", "title", "description"])

        assert "id: TEST-789" in result
        assert "title" not in result  # Should be skipped because it's None
        assert "description: Has value" in result


class TestFormatSearchResults:
    """Test the format_search_results helper function."""

    def test_format_empty_results(self):
        """Test formatting when no results found."""
        results = []

        output = format_search_results(
            results, "type:defect", "type:defect", "TEST_PROJECT", ["id", "title"]
        )

        assert "No work items found in project 'TEST_PROJECT'" in output
        assert "for query: 'type:defect'" in output

    def test_format_with_named_query(self):
        """Test formatting with named query expansion."""
        results = []

        output = format_search_results(
            results, "query:open_bugs", "type:defect AND status:open", "TEST_PROJECT", ["id", "title"]
        )

        assert "No work items found in project 'TEST_PROJECT'" in output
        assert "for named query 'query:open_bugs'" in output
        assert "(expanded to: 'type:defect AND status:open')" in output

    def test_format_multiple_results(self):
        """Test formatting multiple search results."""
        results = [
            {"id": "TEST-1", "title": "Item 1", "status": "open"},
            {"id": "TEST-2", "title": "Item 2", "status": "closed"},
            {"id": "TEST-3", "title": "Item 3", "status": "draft"},
        ]

        output = format_search_results(
            results, "type:task", "type:task", "TEST_PROJECT", ["id", "title"]
        )

        assert "Found 3 work items" in output
        assert "1. id: TEST-1, title: Item 1" in output
        assert "2. id: TEST-2, title: Item 2" in output
        assert "3. id: TEST-3, title: Item 3" in output
        # Status should not appear since it wasn't requested
        assert "status" not in output

    def test_format_truncated_results(self):
        """Test formatting when results exceed max_items."""
        results = [{"id": f"TEST-{i}", "title": f"Item {i}"} for i in range(25)]

        output = format_search_results(
            results, "type:all", "type:all", "TEST_PROJECT", ["id", "title"], max_items=20
        )

        assert "Found 25 work items" in output
        assert "20. id: TEST-19, title: Item 19" in output
        assert "...and 5 more." in output
        assert "21. id: TEST-20" not in output  # Should be truncated


class TestTestRunHelpers:
    """Test helper functions for test runs."""

    def test_format_test_runs_empty(self):
        """Test formatting when no test runs found."""
        from mcp_server.helpers import format_test_runs
        
        result = format_test_runs([], "TEST_PROJECT")
        
        assert result == "No test runs found in project 'TEST_PROJECT'."

    def test_format_test_runs_multiple(self):
        """Test formatting multiple test runs."""
        from mcp_server.helpers import format_test_runs
        
        mock_runs = []
        for i in range(3):
            run = Mock()
            run.id = f"TR-{i}"
            run.title = f"Test Run {i}"
            run.status = "passed" if i % 2 == 0 else "failed"
            mock_runs.append(run)
        
        result = format_test_runs(mock_runs, "TEST_PROJECT")
        
        assert "Found 3 test runs" in result
        assert "1. ID: TR-0, Title: Test Run 0, Status: passed" in result
        assert "2. ID: TR-1, Title: Test Run 1, Status: failed" in result
        assert "3. ID: TR-2, Title: Test Run 2, Status: passed" in result

    def test_extract_test_run_details(self):
        """Test extracting test run details."""
        from mcp_server.helpers import extract_test_run_details
        
        mock_run = Mock()
        mock_run.id = "TR-123"
        mock_run.title = "Regression Test"
        mock_run.status = "finished"
        mock_run.created = "2024-01-01"
        mock_run.finished = "2024-01-02"
        mock_run.records = [1, 2, 3, 4, 5]  # Mock 5 test cases
        
        details = extract_test_run_details(mock_run)
        
        assert details["ID"] == "TR-123"
        assert details["Title"] == "Regression Test"
        assert details["Status"] == "finished"
        assert details["Created"] == "2024-01-01"
        assert details["Finished"] == "2024-01-02"
        assert details["Test Cases"] == "5"

    def test_format_test_run_details(self):
        """Test formatting test run details."""
        from mcp_server.helpers import format_test_run_details
        
        details = {
            "ID": "TR-456",
            "Title": "Smoke Test",
            "Status": "running",
            "Test Cases": "10",
        }
        
        result = format_test_run_details(details, "TR-456")
        
        assert "Test Run Details for 'TR-456':" in result
        assert "- ID: TR-456" in result
        assert "- Title: Smoke Test" in result
        assert "- Status: running" in result
        assert "- Test Cases: 10" in result


class TestWorkItemTypeHelpers:
    """Test helper functions for work item type discovery."""

    def test_extract_work_item_types_from_results(self):
        """Test extracting work item types from search results."""
        from mcp_server.helpers import extract_work_item_types_from_results
        
        results = [
            {"id": "TEST-1", "type": {"id": "defect"}},
            {"id": "TEST-2", "type": {"id": "requirement"}},
            {"id": "TEST-3", "type": {"id": "defect"}},
            {"id": "TEST-4", "type": {"id": "task"}},
            {"id": "TEST-5", "type": {"id": "defect"}},
        ]
        
        types_count = extract_work_item_types_from_results(results)
        
        assert types_count["defect"] == 3
        assert types_count["requirement"] == 1
        assert types_count["task"] == 1

    def test_format_discovered_types(self):
        """Test formatting discovered work item types."""
        from mcp_server.helpers import format_discovered_types
        
        types_count = {
            "defect": 10,
            "requirement": 5,
            "task": 3,
        }
        
        result = format_discovered_types(types_count, "TEST_PROJECT", 18)
        
        assert "Discovered work item types in project 'TEST_PROJECT' (sampled 18 items):" in result
        assert "- defect: 10 occurrences" in result
        assert "- requirement: 5 occurrences" in result
        assert "- task: 3 occurrences" in result
        assert "💡 Tip: Add these types to polarion_config.yaml" in result

    def test_format_discovered_types_empty(self):
        """Test formatting when no types discovered."""
        from mcp_server.helpers import format_discovered_types
        
        result = format_discovered_types({}, "TEST_PROJECT", 0)
        
        assert result == "Could not discover work item types in project 'TEST_PROJECT'."

    def test_format_configured_types(self):
        """Test formatting configured work item types."""
        from mcp_server.helpers import format_configured_types
        
        mock_config = Mock()
        mock_config.get_combined_fields.side_effect = [
            ["id", "title", "status", "customFields.severity"],
            ["id", "title", "status", "customFields.businessValue"],
        ]
        
        configured_types = ["defect", "requirement"]
        
        result = format_configured_types(
            configured_types, "test_alias", "TEST_PROJECT", mock_config
        )
        
        assert "Work Item Types for 'TEST_PROJECT' (from configuration):" in result
        assert "- defect" in result
        assert "- requirement" in result
        assert "Standard fields: id, title, status" in result
        assert "Additional custom fields: severity" in result
        assert "Additional custom fields: businessValue" in result
        assert "Total: 2 configured types" in result
