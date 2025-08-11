# XML Custom Fields Parser

Quick utility to parse Polarion XML custom field definitions and update `polarion_config.yaml`.

## Usage

```bash
python scripts/parse_custom_fields.py --xml fields.xml --project dlco --work-item-type regulatoryRequirement
```

## Options

- `--xml`: Path to XML file with `<field id="..." />` definitions
- `--project`: Project ID in config
- `--work-item-type`: Work item type name
- `--dry-run`: Preview changes without saving
- `--config-file`: Custom config file path (default: `polarion_config.yaml`)

Automatically creates backup and extracts all field IDs from XML.