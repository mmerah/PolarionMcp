"""
Configuration management for Polarion MCP Server.
Handles project aliases, work item types, and named queries.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ProjectConfig(BaseModel):
    """Configuration for a single Polarion project."""

    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    is_plan: bool = False
    work_item_types: Optional[List[str]] = None
    custom_fields: Dict[str, List[str]] = Field(default_factory=dict)
    default_queries: Dict[str, str] = Field(default_factory=dict)


class PolarionConfig(BaseModel):
    """Root configuration model."""

    projects: Dict[str, ProjectConfig] = Field(default_factory=dict)
    display_fields: List[str] = Field(default_factory=list)


class ConfigManager:
    """Manages Polarion project configuration."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.

        Args:
            config_path: Path to configuration file. If None, looks for:
                        1. Environment variable POLARION_CONFIG_PATH
                        2. ./polarion_config.yaml
                        3. ./polarion_config.json
        """
        self.config_path = self._find_config_path(config_path)
        self.config: PolarionConfig = PolarionConfig()
        # alias -> id
        self._project_id_map: Dict[str, str] = {}
        # id -> alias
        self._reverse_map: Dict[str, str] = {}

        if self.config_path and self.config_path.exists():
            self.load_config()
        else:
            logger.info("No configuration file found. Using defaults.")

    def _find_config_path(self, config_path: Optional[str]) -> Optional[Path]:
        """Find the configuration file path."""
        if config_path:
            return Path(config_path)

        # Check environment variable
        env_path = os.getenv("POLARION_CONFIG_PATH")
        if env_path:
            return Path(env_path)

        # Check default locations
        for filename in [
            "polarion_config.yaml",
            "polarion_config.yml",
            "polarion_config.json",
        ]:
            path = Path(filename)
            if path.exists():
                return path

        return None

    def load_config(self) -> None:
        """Load configuration from file."""
        if not self.config_path or not self.config_path.exists():
            logger.warning(f"Configuration file not found: {self.config_path}")
            self.config = PolarionConfig()
            return

        try:
            with open(self.config_path, "r") as f:
                if self.config_path.suffix in [".yaml", ".yml"]:
                    data = yaml.safe_load(f)
                elif self.config_path.suffix == ".json":
                    data = json.load(f)
                else:
                    raise ValueError(
                        f"Unsupported config format: {self.config_path.suffix}"
                    )

            self.config = PolarionConfig(**data) if data else PolarionConfig()

            # Build project ID mappings
            self._build_project_maps()

            logger.info(f"Loaded configuration from {self.config_path}")
            logger.info(f"Configured projects: {list(self.config.projects.keys())}")

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            self.config = PolarionConfig()

    def _build_project_maps(self) -> None:
        """Build bidirectional project alias/ID mappings."""
        self._project_id_map = {}
        self._reverse_map = {}

        for alias, project in self.config.projects.items():
            self._project_id_map[alias.lower()] = project.id
            self._reverse_map[project.id] = alias

    def resolve_project_id(self, project_alias_or_id: str) -> str:
        """
        Resolve a project alias to its actual Polarion ID.

        Args:
            project_alias_or_id: Project alias or actual ID

        Returns:
            The actual Polarion project ID
        """
        # Check if it's an alias (case-insensitive)
        lower_input = project_alias_or_id.lower()
        if lower_input in self._project_id_map:
            return self._project_id_map[lower_input]

        # Check if it's already an ID that has an alias
        if project_alias_or_id in self._reverse_map:
            return project_alias_or_id

        # Assume it's a direct project ID
        return project_alias_or_id

    def get_project_config(self, project_alias_or_id: str) -> Optional[ProjectConfig]:
        """
        Get configuration for a project.

        Args:
            project_alias_or_id: Project alias or actual ID

        Returns:
            ProjectConfig if found, None otherwise
        """
        # Try as alias first
        lower_input = project_alias_or_id.lower()
        for alias, config in self.config.projects.items():
            if alias.lower() == lower_input:
                return config

        # Try as ID
        for alias, config in self.config.projects.items():
            if config.id == project_alias_or_id:
                return config

        return None

    def get_work_item_types(self, project_alias_or_id: str) -> Optional[List[str]]:
        """
        Get configured work item types for a project.

        Args:
            project_alias_or_id: Project alias or actual ID

        Returns:
            List of work item types if configured, None otherwise
        """
        config = self.get_project_config(project_alias_or_id)
        return config.work_item_types if config else None

    def get_custom_fields(
        self, project_alias_or_id: str, work_item_type: str
    ) -> Optional[List[str]]:
        """
        Get custom fields for a specific work item type.

        Args:
            project_alias_or_id: Project alias or actual ID
            work_item_type: Work item type name

        Returns:
            List of custom field names if configured, None otherwise
        """
        config = self.get_project_config(project_alias_or_id)
        if config and work_item_type in config.custom_fields:
            return config.custom_fields[work_item_type]
        return None

    def get_named_query(
        self, project_alias_or_id: str, query_name: str
    ) -> Optional[str]:
        """
        Get a named query for a project.

        Args:
            project_alias_or_id: Project alias or actual ID
            query_name: Name of the query

        Returns:
            Query string if found, None otherwise
        """
        # Check project-specific queries
        config = self.get_project_config(project_alias_or_id)
        if config and query_name in config.default_queries:
            query = config.default_queries[query_name]
            # Replace placeholders
            project_id = self.resolve_project_id(project_alias_or_id)
            query = query.replace("$project_id", project_id)
            query = query.replace("$current_user", "current.user")
            query = query.replace("$current_sprint", "current.sprint")
            return query

        return None

    def resolve_query(self, project_alias_or_id: str, query: str) -> str:
        """
        Resolve a query, expanding named queries if needed.

        Args:
            project_alias_or_id: Project alias or actual ID
            query: Query string (may be a named query like "query:open_bugs")

        Returns:
            Resolved Lucene query string
        """
        # Check if it's a named query
        if query.startswith("query:"):
            query_name = query[6:]  # Remove 'query:' prefix
            named_query = self.get_named_query(project_alias_or_id, query_name)
            if named_query:
                return named_query
            else:
                logger.warning(
                    f"Named query '{query_name}' not found for project {project_alias_or_id}"
                )
                return query  # Return as-is if not found

        # Check for type expansions
        config = self.get_project_config(project_alias_or_id)
        if config and config.work_item_types:
            # Replace $requirements, $bugs, etc. with actual types
            if "$requirements" in query and config.work_item_types:
                req_types = [
                    t
                    for t in config.work_item_types
                    if "requirement" in t.lower() or "specification" in t.lower()
                ]
                if req_types:
                    query = query.replace(
                        "$requirements", f"({' OR '.join(req_types)})"
                    )

            if "$bugs" in query and config.work_item_types:
                bug_types = [
                    t
                    for t in config.work_item_types
                    if "bug" in t.lower() or "defect" in t.lower()
                ]
                if bug_types:
                    query = query.replace("$bugs", f"({' OR '.join(bug_types)})")

        return query

    def get_display_fields(self) -> List[str]:
        """
        Get field list for display.

        Returns:
            List of fields to display (returns a copy to prevent mutation)
        """
        if self.config.display_fields:
            # Return a copy to prevent accidental mutation of the config
            return self.config.display_fields.copy()

        # Default standard fields if not configured
        return ["id", "title", "type", "status", "assignee"]

    def get_combined_fields(
        self,
        project_alias_or_id: str,
        work_item_type: Optional[str] = None,
    ) -> List[str]:
        """
        Get combined standard and custom fields for a work item type.

        Args:
            project_alias_or_id: Project alias or actual ID
            work_item_type: Optional work item type to get custom fields for

        Returns:
            List of standard fields plus custom fields if available
        """
        # Start with display fields (standard fields)
        fields = self.get_display_fields()

        # Add custom fields if work item type is specified
        if work_item_type:
            custom_fields = self.get_custom_fields(project_alias_or_id, work_item_type)
            if custom_fields:
                # Convert custom field names to Polarion format
                for field in custom_fields:
                    custom_field_name = f"customFields.{field}"
                    if custom_field_name not in fields:
                        fields.append(custom_field_name)

        return fields

    def is_plan_project(self, project_alias_or_id: str) -> bool:
        """
        Check if a project is configured as a plan-based project.

        Args:
            project_alias_or_id: Project alias or actual ID

        Returns:
            True if project is a plan, False otherwise
        """
        config = self.get_project_config(project_alias_or_id)
        return config.is_plan if config else False

    def list_projects(self) -> List[Dict[str, Any]]:
        """
        List all configured projects.

        Returns:
            List of project info dicts with alias, id, name, description, and is_plan flag
        """
        projects = []
        for alias, config in self.config.projects.items():
            projects.append(
                {
                    "alias": alias,
                    "id": config.id,
                    "name": config.name or alias,
                    "description": config.description or "",
                    "is_plan": config.is_plan,
                }
            )
        return projects


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get or create the global configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def reload_config() -> None:
    """Reload the configuration from file."""
    manager = get_config_manager()
    manager.load_config()
