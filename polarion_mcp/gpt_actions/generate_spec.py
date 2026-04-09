"""
Generate the OpenAPI 3.0 specification for the GPT Actions REST endpoints.

The spec is derived directly from TOOL_ROUTE_MAP and the live tool definitions,
so it stays in sync with the codebase automatically.

Usage
-----
    python -m polarion_mcp.gpt_actions.generate_spec
    mcp-polarion generate-openapi [--output PATH]
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import yaml
from fastmcp.tools.tool import FunctionTool

from polarion_mcp.gpt_actions.routes import TOOL_ROUTE_MAP
from polarion_mcp.mcp.tools import mcp

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "openapi.yaml"


def _pydantic_type_to_openapi(pydantic_type: str | list | None) -> dict[str, Any]:
    """Convert a pydantic schema type to an OpenAPI schema snippet."""
    if isinstance(pydantic_type, list):
        # e.g. ["string", "null"] → nullable string
        non_null = [t for t in pydantic_type if t != "null"]
        base = non_null[0] if non_null else "string"
        return {"type": base, "nullable": True}
    type_map = {
        "string": "string",
        "integer": "integer",
        "number": "number",
        "boolean": "boolean",
        "array": "array",
        "object": "object",
    }
    return {"type": type_map.get(pydantic_type or "string", "string")}


async def _build_spec() -> dict[str, Any]:
    """Construct the full OpenAPI 3.0 spec dict."""
    # Collect live tool definitions
    all_tools = await mcp._tool_manager.get_tools()
    tool_defs: dict[str, FunctionTool] = {
        name: t for name, t in all_tools.items() if isinstance(t, FunctionTool)
    }

    paths: dict[str, Any] = {}

    for (http_method, route), tool_name in TOOL_ROUTE_MAP.items():
        method = http_method.lower()
        tool = tool_defs.get(tool_name)

        # Path parameters extracted from the route template
        import re
        path_param_names = re.findall(r"\{(\w+)\}", route)

        parameters: list[dict[str, Any]] = []
        for param in path_param_names:
            parameters.append(
                {
                    "name": param,
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                }
            )

        # Build a minimal operation object
        operation: dict[str, Any] = {
            "x-tool-name": tool_name,
            "operationId": tool_name,
            "parameters": parameters,
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "tool": {"type": "string"},
                                    "result_text": {"type": "string"},
                                },
                            }
                        }
                    },
                }
            },
        }

        # Add summary / description from tool docstring
        if tool and tool.description:
            first_line = tool.description.strip().splitlines()[0]
            operation["summary"] = first_line
            operation["description"] = tool.description.strip()

        # POST methods get a requestBody derived from the tool schema
        if method == "post" and tool and tool.parameters:
            props = tool.parameters.get("properties", {}) or {}
            required = tool.parameters.get("required", []) or []

            # Exclude path parameters from the body schema
            body_props = {
                k: v for k, v in props.items() if k not in path_param_names + ["project_alias"]
            }

            if body_props:
                operation["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": body_props,
                                "required": [r for r in required if r in body_props],
                            }
                        }
                    },
                }

        if route not in paths:
            paths[route] = {}
        paths[route][method] = operation

    spec: dict[str, Any] = {
        "openapi": "3.0.0",
        "info": {
            "title": "Polarion MCP — GPT Actions API",
            "version": "1.0.0",
            "description": (
                "REST endpoints that expose Polarion MCP tools to GPT Actions "
                "and other HTTP consumers. Each endpoint wraps the corresponding "
                "FastMCP tool and returns a JSON envelope with `tool` and `result_text`."
            ),
        },
        "servers": [{"url": "https://your-server/", "description": "Replace with your actual server URL"}],
        "paths": paths,
    }
    return spec


def generate_spec(output: Path | None = None) -> Path:
    """
    Build the OpenAPI spec and write it to *output* (default: openapi.yaml).

    Returns the path of the written file.
    """
    target = output or DEFAULT_OUTPUT
    spec = asyncio.run(_build_spec())
    target.write_text(
        yaml.dump(spec, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return target


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate OpenAPI spec for GPT Actions.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"Output path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()
    path = generate_spec(args.output)
    print(f"Wrote OpenAPI spec to {path}")
