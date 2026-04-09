# XML Custom Fields Parser

Quick utility to parse Polarion XML custom field definitions and update the local Polarion config file.

## Usage

Recommended workflow:

```bash
mcp-polarion import-custom-fields --path local/custom-fields/dlco-platform
```

Single-file import still works:

```bash
mcp-polarion import-custom-fields --path local/custom-fields/dlco-platform/regulatoryRequirement-custom-fields.xml
```

## Options

- `--path`: Path to an XML file or a folder of `*-custom-fields.xml` files
- `--project`: Project alias in config; defaults to the folder name
- `--dry-run`: Preview changes without saving
- `--config-file`: Custom config file path; otherwise the CLI auto-discovers one

Folder import infers the work item type from `<name>-custom-fields.xml`, uses the folder name as the default project alias, repairs common malformed export content such as raw `&` and `<br>`, and updates only existing project aliases in the config. By default the CLI auto-discovers `local/polarion_config.yaml` before falling back to a repo-root config file.
