"""
Unit tests for the configuration management system.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from mcp_server.config import ConfigManager, PolarionConfig, ProjectConfig


class TestConfigManager:
    """Test suite for ConfigManager."""

    def test_init_without_config_file(self):
        """Test initialization without a configuration file."""
        with patch("mcp_server.config.Path.exists", return_value=False):
            manager = ConfigManager()
            assert manager.config is not None
            assert isinstance(manager.config, PolarionConfig)
            assert len(manager.config.projects) == 0

    def test_load_yaml_config(self):
        """Test loading configuration from YAML file."""
        config_data = {
            "projects": {
                "webstore": {
                    "id": "WEBSTORE_V3",
                    "name": "Web Store Project",
                    "work_item_types": ["defect", "requirement"],
                    "custom_fields": {
                        "defect": ["severity", "priority"],
                        "requirement": ["businessValue"],
                    },
                    "default_queries": {"open_bugs": "type:defect AND status:open"},
                }
            },
            "display_fields": ["id", "title", "status"],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            manager = ConfigManager(config_path=temp_path)

            # Check project loaded correctly
            assert "webstore" in manager.config.projects
            project = manager.config.projects["webstore"]
            assert project.id == "WEBSTORE_V3"
            assert project.name == "Web Store Project"
            assert project.work_item_types == ["defect", "requirement"]
            assert "defect" in project.custom_fields
            assert "severity" in project.custom_fields["defect"]

            # Check global config
            assert manager.config.display_fields == ["id", "title", "status"]
        finally:
            Path(temp_path).unlink()

    def test_load_json_config(self):
        """Test loading configuration from JSON file."""
        config_data = {
            "projects": {
                "testproj": {"id": "TEST_PROJECT", "description": "Test project"}
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name

        try:
            manager = ConfigManager(config_path=temp_path)
            assert "testproj" in manager.config.projects
            assert manager.config.projects["testproj"].id == "TEST_PROJECT"
        finally:
            Path(temp_path).unlink()

    def test_resolve_project_id(self):
        """Test project ID resolution from aliases."""
        config_data = {
            "projects": {
                "webstore": {"id": "WEBSTORE_V3"},
                "MyProject": {"id": "PROJ_123"},
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            manager = ConfigManager(config_path=temp_path)

            # Test alias resolution (case-insensitive)
            assert manager.resolve_project_id("webstore") == "WEBSTORE_V3"
            assert manager.resolve_project_id("WEBSTORE") == "WEBSTORE_V3"
            assert manager.resolve_project_id("WebStore") == "WEBSTORE_V3"
            assert manager.resolve_project_id("myproject") == "PROJ_123"

            # Test direct ID pass-through
            assert manager.resolve_project_id("WEBSTORE_V3") == "WEBSTORE_V3"
            assert manager.resolve_project_id("UNKNOWN_ID") == "UNKNOWN_ID"
        finally:
            Path(temp_path).unlink()

    def test_get_work_item_types(self):
        """Test retrieving work item types for a project."""
        config_data = {
            "projects": {
                "webstore": {
                    "id": "WEBSTORE_V3",
                    "work_item_types": ["defect", "requirement", "task"],
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            manager = ConfigManager(config_path=temp_path)

            # Test by alias
            types = manager.get_work_item_types("webstore")
            assert types == ["defect", "requirement", "task"]

            # Test by ID
            types = manager.get_work_item_types("WEBSTORE_V3")
            assert types == ["defect", "requirement", "task"]

            # Test unknown project
            types = manager.get_work_item_types("unknown")
            assert types is None
        finally:
            Path(temp_path).unlink()

    def test_get_custom_fields(self):
        """Test retrieving custom fields for work item types."""
        config_data = {
            "projects": {
                "webstore": {
                    "id": "WEBSTORE_V3",
                    "custom_fields": {
                        "defect": ["severity", "priority", "foundIn"],
                        "requirement": ["businessValue", "riskLevel"],
                    },
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            manager = ConfigManager(config_path=temp_path)

            # Test getting custom fields
            fields = manager.get_custom_fields("webstore", "defect")
            assert fields == ["severity", "priority", "foundIn"]

            fields = manager.get_custom_fields("webstore", "requirement")
            assert fields == ["businessValue", "riskLevel"]

            # Test unknown type
            fields = manager.get_custom_fields("webstore", "unknown_type")
            assert fields is None

            # Test unknown project
            fields = manager.get_custom_fields("unknown", "defect")
            assert fields is None
        finally:
            Path(temp_path).unlink()

    def test_resolve_named_queries(self):
        """Test resolving named queries with placeholders."""
        config_data = {
            "projects": {
                "webstore": {
                    "id": "WEBSTORE_V3",
                    "default_queries": {
                        "open_bugs": "type:defect AND status:open",
                        "my_items": "assignee.id:$current_user AND project.id:$project_id",
                    },
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            manager = ConfigManager(config_path=temp_path)

            # Test project-specific query
            query = manager.get_named_query("webstore", "open_bugs")
            assert query == "type:defect AND status:open"

            # Test query with placeholders
            query = manager.get_named_query("webstore", "my_items")
            assert "assignee.id:current.user" in query
            assert "project.id:WEBSTORE_V3" in query

            # Test unknown query
            query = manager.get_named_query("webstore", "unknown")
            assert query is None
        finally:
            Path(temp_path).unlink()

    def test_resolve_query_with_named_queries(self):
        """Test resolving queries that reference named queries."""
        config_data = {
            "projects": {
                "webstore": {
                    "id": "WEBSTORE_V3",
                    "default_queries": {"open_bugs": "type:defect AND status:open"},
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            manager = ConfigManager(config_path=temp_path)

            # Test named query resolution
            resolved = manager.resolve_query("webstore", "query:open_bugs")
            assert resolved == "type:defect AND status:open"

            # Test regular query pass-through
            resolved = manager.resolve_query("webstore", "type:requirement")
            assert resolved == "type:requirement"

            # Test unknown named query (should return as-is)
            resolved = manager.resolve_query("webstore", "query:unknown")
            assert resolved == "query:unknown"
        finally:
            Path(temp_path).unlink()

    def test_get_display_fields(self):
        """Test retrieving display fields."""
        config_data = {
            "display_fields": ["id", "title", "status", "assignee"]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            manager = ConfigManager(config_path=temp_path)

            # Test getting display fields
            fields = manager.get_display_fields()
            assert fields == ["id", "title", "status", "assignee"]

            # Test fallback when not configured
            manager.config.display_fields = []
            fields = manager.get_display_fields()
            assert fields == [
                "id",
                "title",
                "type",
                "status",
                "assignee",
            ]  # Default fallback
        finally:
            Path(temp_path).unlink()

    def test_list_projects(self):
        """Test listing all configured projects."""
        config_data = {
            "projects": {
                "webstore": {
                    "id": "WEBSTORE_V3",
                    "name": "Web Store",
                    "description": "E-commerce platform",
                },
                "internal": {"id": "INTERNAL_TOOLS", "name": "Internal Tools"},
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            manager = ConfigManager(config_path=temp_path)

            projects = manager.list_projects()
            assert len(projects) == 2

            # Check webstore project
            webstore = next(p for p in projects if p["alias"] == "webstore")
            assert webstore["id"] == "WEBSTORE_V3"
            assert webstore["name"] == "Web Store"
            assert webstore["description"] == "E-commerce platform"

            # Check internal project
            internal = next(p for p in projects if p["alias"] == "internal")
            assert internal["id"] == "INTERNAL_TOOLS"
            assert internal["name"] == "Internal Tools"
            assert internal["description"] == ""
        finally:
            Path(temp_path).unlink()

    def test_config_with_invalid_file(self):
        """Test handling of invalid configuration files."""
        # Test with non-existent file
        manager = ConfigManager(config_path="/non/existent/path.yaml")
        assert manager.config is not None
        assert len(manager.config.projects) == 0

        # Test with invalid YAML
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: {{}}")
            temp_path = f.name

        try:
            manager = ConfigManager(config_path=temp_path)
            # Should fall back to empty config
            assert manager.config is not None
            assert len(manager.config.projects) == 0
        finally:
            Path(temp_path).unlink()

    def test_environment_variable_config_path(self):
        """Test loading config path from environment variable."""
        config_data = {"projects": {"envtest": {"id": "ENV_TEST"}}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            with patch.dict("os.environ", {"POLARION_CONFIG_PATH": temp_path}):
                manager = ConfigManager()
                assert "envtest" in manager.config.projects
                assert manager.config.projects["envtest"].id == "ENV_TEST"
        finally:
            Path(temp_path).unlink()

    def test_get_combined_fields(self):
        """Test combining standard and custom fields for work items."""
        config_data = {
            "projects": {
                "webstore": {
                    "id": "WEBSTORE_V3",
                    "custom_fields": {
                        "systemRequirement": [
                            "acceptanceCriteria",
                            "riskRelevance",
                            "importance",
                        ],
                        "defect": ["severity", "foundIn"],
                    },
                }
            },
            "display_fields": ["id", "title", "status"],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            manager = ConfigManager(config_path=temp_path)

            # Test with systemRequirement type
            fields = manager.get_combined_fields("webstore", "systemRequirement")
            assert "id" in fields
            assert "title" in fields
            assert "status" in fields
            assert "customFields.acceptanceCriteria" in fields
            assert "customFields.riskRelevance" in fields
            assert "customFields.importance" in fields

            # Test with defect type
            fields = manager.get_combined_fields("webstore", "defect")
            assert "id" in fields
            assert "title" in fields
            assert "status" in fields
            assert "customFields.severity" in fields
            assert "customFields.foundIn" in fields

            # Test with no custom fields defined
            fields = manager.get_combined_fields("webstore", "unknownType")
            assert "id" in fields
            assert "title" in fields
            assert "status" in fields
            assert not any(f.startswith("customFields.") for f in fields)

            # Test with no work item type specified
            fields = manager.get_combined_fields("webstore", None)
            assert "id" in fields
            assert "title" in fields
            assert "status" in fields
            assert not any(f.startswith("customFields.") for f in fields)
        finally:
            Path(temp_path).unlink()
