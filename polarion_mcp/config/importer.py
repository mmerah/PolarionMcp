"""Utilities for importing Polarion custom field XML exports into config."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from ruamel.yaml import YAML

from polarion_mcp.core.config import find_config_path

FILENAME_PATTERN = re.compile(r"^(?P<work_item_type>.+)-custom-fields\.xml$")
VALID_XML_ENTITY = re.compile(r"&(?!(?:#\d+|#x[0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]+);)")
BR_TAG_PATTERN = re.compile(r"<br\s*/?>", re.IGNORECASE)


@dataclass
class ImportResult:
    """Result of a custom field import operation."""

    project: str
    config_path: Path
    dry_run: bool
    imported_types: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def render(self) -> str:
        action = "Would update" if self.dry_run else "Updated"
        lines = [f"{action} {self.config_path}", f"Project: {self.project}"]

        if self.imported_types:
            lines.append("Imported work item types:")
            for work_item_type in self.imported_types:
                lines.append(f"  - {work_item_type}")

        if self.warnings:
            lines.append("Warnings:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        return "\n".join(lines)


def sanitize_xml_content(xml_content: str) -> str:
    """Repair common Polarion export issues before XML parsing."""
    sanitized = BR_TAG_PATTERN.sub("&lt;br/&gt;", xml_content)
    sanitized = VALID_XML_ENTITY.sub("&amp;", sanitized)
    return sanitized


def parse_xml_custom_fields(xml_content: str) -> list[str]:
    """Parse XML custom field definitions and extract unique field IDs."""
    sanitized = sanitize_xml_content(xml_content)

    try:
        root = ET.fromstring(sanitized)
    except ET.ParseError as exc:
        raise ValueError(
            "Could not parse XML after applying common repairs for '&' and '<br>' "
            f"issues: {exc}"
        ) from exc

    if root.tag == "fields":
        fields = root.findall("field")
    elif root.tag == "field":
        fields = [root]
    else:
        raise ValueError(
            f"Unsupported XML root '{root.tag}'. Expected <fields> or <field>."
        )

    seen: set[str] = set()
    field_ids: list[str] = []
    for field in fields:
        field_id = field.get("id")
        if field_id and field_id not in seen:
            seen.add(field_id)
            field_ids.append(field_id)

    if not field_ids:
        raise ValueError('No <field id="..."> entries found in XML.')

    return field_ids


def infer_work_item_type(path: Path) -> str | None:
    """Infer the work item type from a '*-custom-fields.xml' filename."""
    match = FILENAME_PATTERN.match(path.name)
    if match is None:
        return None
    return match.group("work_item_type")


def load_yaml_config(config_path: Path) -> Any:
    """Load YAML configuration while preserving formatting and comments."""
    if not config_path.exists():
        raise ValueError(f"Configuration file not found: {config_path}")

    yaml = YAML()
    yaml.preserve_quotes = True

    try:
        with config_path.open("r", encoding="utf-8") as handle:
            config = yaml.load(handle) or {}
    except Exception as exc:  # pragma: no cover - ruamel provides mixed errors
        raise ValueError(f"Invalid YAML format in {config_path}: {exc}") from exc

    if "projects" not in config or not isinstance(config["projects"], dict):
        raise ValueError(f"{config_path} does not contain a valid 'projects' mapping.")

    return config


def save_yaml_config(config: Any, config_path: Path) -> None:
    """Save YAML configuration while preserving formatting and comments."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)

    with config_path.open("w", encoding="utf-8") as handle:
        yaml.dump(config, handle)


def _ensure_list(container: Any, key: str) -> list[str]:
    value = container.get(key)
    if value is None:
        container[key] = []
        return container[key]
    if not isinstance(value, list):
        raise ValueError(f"Expected '{key}' to be a list.")
    return value


def _ensure_mapping(container: Any, key: str) -> Any:
    value = container.get(key)
    if value is None:
        container[key] = {}
        return container[key]
    if not isinstance(value, dict):
        raise ValueError(f"Expected '{key}' to be a mapping.")
    return value


def update_project_custom_fields(
    config: Any,
    project_alias: str,
    work_item_type: str,
    custom_fields: list[str],
) -> None:
    """Update config for an existing project alias."""
    projects = config["projects"]
    if project_alias not in projects:
        raise ValueError(
            f"Project alias '{project_alias}' does not exist in the config. "
            "Create the project entry with its real Polarion id first."
        )

    project_config = projects[project_alias]
    work_item_types = _ensure_list(project_config, "work_item_types")
    custom_field_map = _ensure_mapping(project_config, "custom_fields")

    if work_item_type not in work_item_types:
        work_item_types.append(work_item_type)

    custom_field_map[work_item_type] = list(custom_fields)


def _iter_input_files(path: Path) -> tuple[list[tuple[Path, str]], list[str]]:
    """Collect and validate import files from a file or directory path."""
    if not path.exists():
        raise ValueError(f"Input path not found: {path}")

    if path.is_file():
        work_item_type = infer_work_item_type(path)
        if work_item_type is None:
            raise ValueError(
                "Could not infer work item type from filename. Expected "
                "'<type>-custom-fields.xml'."
            )
        return [(path, work_item_type)], []

    warnings: list[str] = []
    files: list[tuple[Path, str]] = []
    for child in sorted(path.iterdir(), key=lambda item: item.name.lower()):
        if not child.is_file() or child.suffix.lower() != ".xml":
            continue
        work_item_type = infer_work_item_type(child)
        if work_item_type is None:
            warnings.append(
                f"Ignored '{child.name}' because it does not match "
                "'<type>-custom-fields.xml'."
            )
            continue
        files.append((child, work_item_type))

    if not files:
        raise ValueError(
            f"No matching '*-custom-fields.xml' files found in directory: {path}"
        )

    return files, warnings


def resolve_project_alias(path: Path, explicit_project: str | None) -> str:
    """Resolve the project alias from CLI input."""
    if explicit_project:
        return explicit_project
    if path.is_dir():
        return path.name
    return path.parent.name


def _resolve_config_path(config_file: str | Path | None) -> Path:
    resolved = find_config_path(str(config_file) if config_file else None)
    if resolved is None:
        raise ValueError(
            "No Polarion config file found. Create local/polarion_config.yaml "
            "or pass --config-file."
        )
    return resolved


def import_custom_fields(
    *,
    path: str | Path,
    project: str | None = None,
    config_file: str | Path | None = None,
    dry_run: bool = False,
    work_item_type: str | None = None,
) -> ImportResult:
    """Import custom fields from XML exports into a Polarion config file."""
    input_path = Path(path)
    config_path = _resolve_config_path(config_file)
    project_alias = resolve_project_alias(input_path, project)

    files, warnings = _iter_input_files(input_path)
    config = load_yaml_config(config_path)

    imported_types: list[str] = []
    for file_path, inferred_type in files:
        resolved_type = (
            work_item_type if input_path.is_file() and work_item_type else inferred_type
        )
        xml_content = file_path.read_text(encoding="utf-8")
        custom_fields = parse_xml_custom_fields(xml_content)
        update_project_custom_fields(
            config, project_alias, resolved_type, custom_fields
        )
        imported_types.append(resolved_type)

    if not dry_run:
        save_yaml_config(config, config_path)

    return ImportResult(
        project=project_alias,
        config_path=config_path,
        dry_run=dry_run,
        imported_types=imported_types,
        warnings=warnings,
    )
