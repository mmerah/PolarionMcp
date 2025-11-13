"""
Generate agent instruction markdown files from registered FastMCP tools.

Usage:
    python -m mcp_server.docgen               # generates both variants
    python -m mcp_server.docgen --variant full --output custom.md
    python -m mcp_server.docgen --variant simple
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent
from typing import Dict, Iterable, Literal

import yaml
from fastmcp.tools.tool import FunctionTool

from mcp_server.tools import mcp

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FULL_PATH = REPO_ROOT / "agent_instructions.md"
DEFAULT_SIMPLE_PATH = REPO_ROOT / "agent_instructions_simple.md"
CONFIG_PATH = REPO_ROOT / "polarion_config.yaml"
Variant = Literal["full", "simple"]


def _format_properties(schema: dict) -> Iterable[str]:
    properties: Dict[str, dict] = schema.get("properties", {}) or {}
    required = set(schema.get("required", []) or [])

    if not properties:
        return []

    lines = [
        "| Parameter | Type | Required | Description |",
        "|-----------|------|----------|-------------|",
    ]

    for name, details in properties.items():
        type_info = details.get("type")
        if isinstance(type_info, list):
            type_repr = " / ".join(type_info)
        else:
            type_repr = type_info or "any"

        description = details.get("description", "").strip()
        if not description:
            default = details.get("default")
            if default not in (None, ""):
                description = f"Default: {default}"
            else:
                description = "—"

        required_flag = "yes" if name in required else "no"
        lines.append(
            f"| `{name}` | {type_repr} | {required_flag} | {description} |"
        )

    return lines


def _format_output_schema(schema: dict | None) -> str:
    if not schema:
        return "Returns a formatted text string. No structured schema."

    try:
        return (
            "Structured JSON output schema:\n\n"
            f"```json\n{json.dumps(schema, indent=2)}\n```"
        )
    except TypeError:
        return "Returns structured data (schema not serializable)."


def _load_config() -> dict:
    """Load the polarion_config.yaml file."""
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _generate_workflow_section() -> str:
    """Generate the typical workflow section based on configuration."""
    config = _load_config()
    projects = config.get("projects", {})

    if not projects:
        return ""

    # Both variants use detailed workflow
    lines = [
        "",
        "## Typical Workflow",
        "",
        "### Configured Projects",
        "",
        "The following projects are configured in this Polarion MCP instance:",
        "",
    ]

    for alias, proj_config in projects.items():
        proj_id = proj_config.get("id", "")
        proj_name = proj_config.get("name", "")
        proj_desc = proj_config.get("description", "")
        work_item_types = proj_config.get("work_item_types", [])
        is_plan = proj_config.get("is_plan", False)

        lines.append(f"#### Project: `{alias}`")
        lines.append("")
        lines.append(f"- **ID**: `{proj_id}`")
        lines.append(f"- **Name**: {proj_name}")
        if proj_desc:
            lines.append(f"- **Description**: {proj_desc}")
        if is_plan:
            lines.append(f"- **Type**: Plan-based project (supports plans/releases/iterations)")
        lines.append(f"- **Configured Work Item Types**:")
        if work_item_types:
            for wit in work_item_types:
                lines.append(f"  - `{wit}`")
        else:
            lines.append("  - _None configured (use discover_work_item_types)_")
        lines.append("")

    lines.extend([
        "### Standard Workflow Pattern",
        "",
        "When working with Polarion work items, follow this typical pattern:",
        "",
        "#### 1. Search for Work Items",
        "",
        "Use `search_workitems` to find items based on user intent. Construct queries by combining:",
        "",
        "- **Type filter**: Always specify work item type(s) from the configured list above",
        "  - Example: `type:defect`, `type:systemRequirement`, `type:(userstory OR task)`",
        "",
        "- **User intent**: Translate natural language to Lucene query syntax",
        "",
        "  **Text Search (IMPORTANT)**:",
        "  - ✅ `title:keyword*` - Search in work item titles (MOST COMMON)",
        "  - ✅ `description:keyword*` - Search in descriptions",
        "  - ✅ `keyword*` (no field prefix) - Free text search across multiple fields",
        "  - ❌ `text:keyword*` - NOT VALID! Polarion has no 'text' field",
        "",
        "  **Other Filters**:",
        "  - Status/field filters: `status:open`, `priority:high`, `assignee.id:john.doe`",
        "  - Custom fields: Use field names directly, e.g., `severity:critical`, `importance:high`",
        "  - Date ranges: `created:[$today - 7d$ TO $today$]`",
        "  - Boolean logic: Combine with `AND`, `OR`, `NOT` (must be UPPERCASE)",
        "",
        "- **Field list**: Specify which standard fields to display in results",
        "  - Default: `id,title,type,status,assignee`",
        "  - Note: Custom fields cannot be retrieved via field_list (use get_workitem instead)",
        "",
        "**Query Construction Examples**:",
        "",
        "- User asks: _\"Show me open defects\"_",
        "  - Query: `type:defect AND status:open`",
        "  - Field list: `id,title,status,assignee,priority`",
        "",
        "- User asks: _\"Find component requirements with transparent in the title\"_",
        "  - ❌ WRONG: `type:componentRequirement AND text:transparent*`",
        "  - ✅ CORRECT: `type:componentRequirement AND title:transparent*`",
        "  - Field list: `id,title,status`",
        "",
        "- User asks: _\"Find high-priority requirements about authentication\"_",
        "  - Query: `type:systemRequirement AND priority:high AND title:authentication*`",
        "  - Field list: `id,title,status,priority,assignee`",
        "",
        "- User asks: _\"Show unassigned user stories\"_",
        "  - Query: `type:userstory AND NOT HAS_VALUE:assignee`",
        "  - Field list: `id,title,status,created`",
        "",
        "#### 2. Explore Results",
        "",
        "After receiving search results, you have two options:",
        "",
        "- **Get detailed information**: Use `get_workitem` with specific work item IDs to retrieve:",
        "  - Full descriptions and custom field values",
        "  - Linked work items and traceability information",
        "  - Complete metadata and history",
        "",
        "- **Ask for user direction**: Present the search results summary and ask the user:",
        "  - \"Would you like me to show details for any specific work items?\"",
        "  - \"Should I explore the linked requirements/tests for these items?\"",
        "  - \"Do you want to refine the search with additional filters?\"",
        "",
        "#### 3. Follow-up Actions",
        "",
        "Based on the exploration, you may:",
        "",
        "- Fetch related items by following trace links (parent/child, linked items)",
        "- Aggregate and summarize findings (counts by status, priority distribution)",
        "- Query test runs, plans, or documents related to the work items",
        "- Provide coverage analysis or gap identification",
        "",
        "### Common Pitfalls to Avoid",
        "",
        "1. **❌ Using `text:` field** - Polarion has NO `text` field!",
        "   - Wrong: `type:defect AND text:login*`",
        "   - Right: `type:defect AND title:login*`",
        "",
        "2. **❌ Lowercase boolean operators** - Must be UPPERCASE",
        "   - Wrong: `type:defect and status:open`",
        "   - Right: `type:defect AND status:open`",
        "",
        "3. **❌ Leading wildcards** - Cannot start search with `*`",
        "   - Wrong: `title:*authentication`",
        "   - Right: `title:authentication*`",
        "",
        "4. **❌ Requesting custom fields in field_list** - API limitation",
        "   - Wrong: `field_list=\"id,title,severity\"` (severity is custom)",
        "   - Right: Use `search_workitems` to find, then `get_workitem` for custom fields",
        "",
        "5. **❌ Missing type filter** - Too broad, slow queries",
        "   - Wrong: `status:open` (searches all types)",
        "   - Right: `type:defect AND status:open` (more specific)",
    ])

    return "\n".join(lines)


async def _collect_tools() -> Dict[str, FunctionTool]:
    tools = await mcp._tool_manager.get_tools()
    return {
        name: tool
        for name, tool in sorted(
            (
                (name, tool)
                for name, tool in tools.items()
                if isinstance(tool, FunctionTool)
            ),
            key=lambda item: item[0],
        )
    }


async def generate_markdown(variant: Variant) -> str:
    tools = await _collect_tools()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    if variant == "simple":
        lines = [
            "# Polarion Agent Quick Reference",
            "",
            "Use these FastMCP tools to query Polarion ALM. Always execute a tool instead of guessing values and surface errors back to the user.",
            "",
            "## Tool Overview",
            "",
        ]

        for name, tool in tools.items():
            description = dedent(tool.description or "").strip()
            summary = description.split("\n", 1)[0] if description else "No description provided."
            lines.append(f"- `{name}` – {summary}")

        lines.append("")
        lines.append("Tip: Start with `list_projects`, then call the tool best suited to the user's question.")

        # Add workflow section
        workflow_section = _generate_workflow_section()
        if workflow_section:
            lines.append(workflow_section)

        return "\n".join(lines)

    # Full variant
    lines: list[str] = [
        "# Polarion Agent Instructions",
        "",
        "## Overview",
        "",
        "- These actions wrap the Polarion MCP tools. Always prefer project aliases from `list_projects`.",
        "- Handle errors starting with `❌` gracefully and surface them to the user.",
        "- Most tools require `project_alias`; resolve plan-specific data with dedicated plan actions.",
        "",
        "## Operating Principles",
        "",
        "You are a Polarion-connected project intelligence assistant that can read, search, and analyze content across Polarion ALM instances through these actions. Your goal is to help users answer questions about their projects and go deeper than simple keyword search by exploring trace relationships among requirements, stories, tasks, defects, tests, plans, documents, and custom item types.",
        "",
        "When responding:",
        "",
        "- Prioritize correctness over coverage. If unsure, say so and suggest additional filters or access needed.",
        "- Respect access controls: only surface data visible to the signed-in user. Flag possible permission limitations.",
        "- Prefer structured outputs. Use concise tables or bullets with key fields (ID, title, status, owner, priority/severity, updated date, project, path/module). Show counts and aggregates where helpful.",
        "- Always include artifact identifiers and, when available, direct links returned by the API. Use the user’s terminology.",
        "- Follow trace links (parent/child, satisfies/implements, verifies/tested by, relates to, depends on, duplicates, etc.) and present multi-hop traces clearly (e.g., Requirement → Story → Test Case → Test Run → Defect).",
        "- For large result sets, summarize first (totals, key segments, top risks) before offering drill-downs or filters.",
        "- Render simple diagrams or matrices when visual traces help. Prefer the canvas for node-link diagrams or coverage heatmaps.",
        "- Compute coverage/quality metrics when data allows (requirement coverage, test execution status, defect leakage, cycle time, trends). Include formulas briefly to build trust.",
        "- On connection or tool failures, explain the issue, list minimum configuration (server URL, auth, project scope), and provide a simulated response structure with placeholders.",
        "- Minimize follow-up questions. Infer sensible defaults (recent project, last two sprints). If multiple interpretations exist, present the top options and ask the user to pick.",
        "- Never fabricate Polarion data. Label anything inferred or simulated. Do not expose secrets or internal IDs not returned by the tools.",
        "- Treat each conversation independently—no long-term memory.",
        "",
        "Interaction style:",
        "",
        "- Short, plain-language explanations focused on outcomes and decisions.",
        "- Use sections such as Summary, Key Findings, Evidence (tables/IDs), and Next Steps when appropriate.",
        "- Offer optional next actions (e.g., “Expand to linked defects?”, “Open coverage gaps?”).",
        "- Prefer tables or canvas sketches to images; primary data authority is the Polarion MCP connection.",
        "",
        "## Available Tools",
        "",
    ]

    for name, tool in tools.items():
        description = dedent(tool.description or "").strip() or "No description provided."
        lines.extend(
            [
                f"### `{name}`",
                "",
                description,
                "",
            ]
        )

        param_lines = list(_format_properties(tool.parameters or {}))
        if param_lines:
            lines.extend(param_lines)
            lines.append("")
        else:
            lines.append("_No parameters._")
            lines.append("")

        lines.append(_format_output_schema(tool.output_schema))
        lines.append("")

    # Add workflow section
    workflow_section = _generate_workflow_section()
    if workflow_section:
        lines.append(workflow_section)

    return "\n".join(lines)


def write_variant(variant: Variant, output: Path | None = None) -> Path:
    if variant == "full":
        default_path = DEFAULT_FULL_PATH
    else:
        default_path = DEFAULT_SIMPLE_PATH

    target = output or default_path
    content = asyncio.run(generate_markdown(variant))
    target.write_text(content, encoding="utf-8")
    return target


def main() -> list[Path]:
    parser = argparse.ArgumentParser(description="Generate Polarion agent instruction Markdown.")
    parser.add_argument(
        "--variant",
        choices=["full", "simple", "all"],
        default="all",
        help="Which variant to generate. Default: both variants.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output path (only valid when --variant is not 'all').",
    )
    args = parser.parse_args()

    if args.variant == "all":
        if args.output:
            parser.error("--output cannot be used with --variant all")
        generated = [
            write_variant("full"),
            write_variant("simple"),
        ]
    else:
        generated = [write_variant(args.variant, args.output)]

    for path in generated:
        print(f"Wrote agent instructions to {path}")
    return generated


if __name__ == "__main__":
    main()
