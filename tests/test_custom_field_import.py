"""Tests for the custom field import utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from polarion_mcp.config.importer import import_custom_fields, parse_xml_custom_fields


def _write_config(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "projects:",
                "  demo:",
                "    id: DEMO_PROJECT",
                "    work_item_types:",
                "      - existingType",
                "    custom_fields:",
                "      existingType:",
                "        - existingField",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_parse_xml_custom_fields_repairs_ampersands() -> None:
    xml_content = (
        '<fields><field id="summary" description="R&D & QA" />'
        '<field id="summary" description="duplicate" /></fields>'
    )

    assert parse_xml_custom_fields(xml_content) == ["summary"]


def test_parse_xml_custom_fields_repairs_br_tags() -> None:
    xml_content = '<fields><field id="notes" description="Line 1 <br> Line 2" /></fields>'

    assert parse_xml_custom_fields(xml_content) == ["notes"]


def test_parse_xml_custom_fields_rejects_unrecoverable_xml() -> None:
    xml_content = '<fields><field id="broken"></fields'

    with pytest.raises(ValueError, match="Could not parse XML after applying common repairs"):
        parse_xml_custom_fields(xml_content)


def test_import_custom_fields_directory_is_sorted_and_dry_run(tmp_path: Path) -> None:
    config_path = tmp_path / "polarion_config.yaml"
    input_dir = tmp_path / "demo"
    _write_config(config_path)
    input_dir.mkdir()

    (input_dir / "zeta-custom-fields.xml").write_text(
        '<fields><field id="z2" /><field id="z1" /></fields>',
        encoding="utf-8",
    )
    (input_dir / "alpha-custom-fields.xml").write_text(
        '<fields><field id="alpha" /><field id="alpha" /></fields>',
        encoding="utf-8",
    )
    (input_dir / "notes.xml").write_text("<fields />", encoding="utf-8")

    before = config_path.read_text(encoding="utf-8")
    result = import_custom_fields(path=input_dir, config_file=config_path, dry_run=True)
    after = config_path.read_text(encoding="utf-8")

    assert result.project == "demo"
    assert result.imported_types == ["alpha", "zeta"]
    assert "Ignored 'notes.xml'" in result.warnings[0]
    assert before == after


def test_import_custom_fields_updates_existing_project(tmp_path: Path) -> None:
    config_path = tmp_path / "polarion_config.yaml"
    xml_path = tmp_path / "demo" / "requirement-custom-fields.xml"
    _write_config(config_path)
    xml_path.parent.mkdir()
    xml_path.write_text(
        '<fields><field id="severity" /><field id="priority" /></fields>',
        encoding="utf-8",
    )

    result = import_custom_fields(path=xml_path, config_file=config_path)
    written = config_path.read_text(encoding="utf-8")

    assert result.project == "demo"
    assert result.imported_types == ["requirement"]
    assert "requirement" in written
    assert "severity" in written
    assert "priority" in written


def test_import_custom_fields_fails_for_unknown_alias(tmp_path: Path) -> None:
    config_path = tmp_path / "polarion_config.yaml"
    xml_path = tmp_path / "demo" / "requirement-custom-fields.xml"
    _write_config(config_path)
    xml_path.parent.mkdir()
    xml_path.write_text('<fields><field id="severity" /></fields>', encoding="utf-8")

    with pytest.raises(ValueError, match="does not exist in the config"):
        import_custom_fields(path=xml_path, config_file=config_path, project="missing")
