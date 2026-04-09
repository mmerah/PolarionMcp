"""
Generate the OpenAPI 3.1.0 specification for the REST API endpoints.

The spec is derived directly from TOOL_ROUTE_MAP and the live tool definitions,
so it stays in sync with the codebase automatically.

Usage
-----
    python -m polarion_mcp.rest_api.generate_spec
    mcp-polarion generate-openapi [--output PATH]
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

import yaml
from fastmcp.tools.tool import FunctionTool

from polarion_mcp.mcp.tools import mcp
from polarion_mcp.rest_api.routes import TOOL_ROUTE_MAP

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "generated" / "openapi.yaml"

# Map route → extra error response codes (beyond 200).
# Derived from the actual status codes returned by the route handlers.
_ERROR_RESPONSES: dict[tuple[str, str], dict[str, str]] = {
    ("GET", "/actions/health"): {"502": "Polarion connection failed"},
    ("GET", "/actions/projects/{project_alias}"): {"404": "Project not found"},
    ("GET", "/actions/projects/{project_alias}/workitems/{workitem_id}"): {
        "404": "Work item not found",
    },
    ("POST", "/actions/projects/{project_alias}/workitems/get"): {
        "400": "Invalid request",
    },
    ("POST", "/actions/projects/{project_alias}/workitems/search"): {
        "400": "Invalid request",
    },
    ("GET", "/actions/projects/{project_alias}/documents"): {
        "400": "Invalid limit supplied",
    },
    ("GET", "/actions/projects/{project_alias}/workitems/discover"): {
        "400": "Invalid limit supplied",
    },
    ("GET", "/actions/projects/{project_alias}/test-runs/{test_run_id}"): {
        "404": "Test run not found",
    },
    ("GET", "/actions/projects/{project_alias}/documents/content"): {
        "400": "Missing document path",
        "404": "Document not found",
    },
    ("GET", "/actions/projects/{project_alias}/documents/test-specs"): {
        "400": "Missing document path",
        "404": "Document not found",
    },
    ("GET", "/actions/projects/{project_alias}/plans/{plan_id}"): {
        "404": "Plan not found",
    },
    ("GET", "/actions/projects/{project_alias}/plans/{plan_id}/workitems"): {
        "404": "Plan not found",
    },
    ("POST", "/actions/projects/{project_alias}/plans/search"): {
        "400": "Invalid request",
    },
}

# Query parameters used by specific routes (not derivable from tool schemas).
_QUERY_PARAMS: dict[tuple[str, str], list[dict[str, Any]]] = {
    ("GET", "/actions/projects/{project_alias}/workitems/discover"): [
        {
            "name": "limit",
            "in": "query",
            "required": False,
            "description": "Maximum number of items to sample.",
            "schema": {"type": "integer", "minimum": 1},
        },
    ],
    ("GET", "/actions/projects/{project_alias}/documents/content"): [
        {
            "name": "document_path",
            "in": "query",
            "required": True,
            "description": "Document path such as `QA/TestSpecs`.",
            "schema": {"type": "string"},
        },
    ],
    ("GET", "/actions/projects/{project_alias}/documents"): [
        {
            "name": "limit",
            "in": "query",
            "required": False,
            "description": "Maximum number of documents to display.",
            "schema": {"type": "integer", "minimum": 1},
        },
    ],
    ("GET", "/actions/projects/{project_alias}/documents/test-specs"): [
        {
            "name": "document_path",
            "in": "query",
            "required": True,
            "description": "Document path such as `QA/TestSpecs`.",
            "schema": {"type": "string"},
        },
    ],
}

# Path parameter descriptions.
_PARAM_DESCRIPTIONS: dict[str, str] = {
    "project_alias": "Polarion project alias or ID.",
    "workitem_id": "Work item ID including the project prefix (e.g. `MYPROJ-123`).",
    "test_run_id": "Polarion test run identifier.",
    "plan_id": "Polarion plan identifier (release, iteration, etc.).",
}

# Shared component schemas.
_COMPONENTS: dict[str, Any] = {
    "schemas": {
        "ActionResponse": {
            "type": "object",
            "description": "Standard response envelope returned by REST API routes.",
            "required": ["tool"],
            "properties": {
                "tool": {
                    "type": "string",
                    "description": "Name of the underlying MCP tool that was invoked.",
                },
                "result_text": {
                    "type": "string",
                    "description": "Human-readable text returned by the tool.",
                },
                "structured_result": {
                    "type": "object",
                    "nullable": True,
                    "additionalProperties": True,
                    "description": "Optional structured data if the MCP tool provided it.",
                },
                "error": {
                    "type": "string",
                    "description": "Error message when the action failed.",
                },
                "details": {
                    "type": "object",
                    "additionalProperties": True,
                    "description": "Additional error context.",
                },
            },
        },
        "SearchWorkitemsRequest": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Lucene query string or named query (e.g. `query:open_bugs`).",
                },
                "field_list": {
                    "type": "string",
                    "description": "Optional comma-separated list of fields to include.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Optional maximum number of results to fetch and display.",
                },
            },
        },
        "GetWorkitemsRequest": {
            "type": "object",
            "required": ["workitem_id"],
            "properties": {
                "workitem_id": {
                    "description": "Single work item ID or a list of work item IDs.",
                    "oneOf": [
                        {"type": "string"},
                        {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                        },
                    ],
                },
            },
        },
        "SearchPlansRequest": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Lucene query string used to filter plans. Defaults to an "
                        "empty query which returns all plans."
                    ),
                },
            },
        },
    },
}

# Map POST route → request body $ref.
_REQUEST_BODY_REFS: dict[str, str] = {
    "/actions/projects/{project_alias}/workitems/get": "#/components/schemas/GetWorkitemsRequest",
    "/actions/projects/{project_alias}/workitems/search": "#/components/schemas/SearchWorkitemsRequest",
    "/actions/projects/{project_alias}/plans/search": "#/components/schemas/SearchPlansRequest",
}


def _to_camel_case(snake: str) -> str:
    """Convert snake_case to camelCase."""
    parts = snake.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _action_response_ref() -> dict[str, Any]:
    return {
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ActionResponse"},
            },
        },
    }


def _artifact_response() -> dict[str, Any]:
    return {
        "description": "Downloadable PDF artifact.",
        "content": {
            "application/pdf": {
                "schema": {"type": "string", "format": "binary"},
            }
        },
    }


async def _build_spec() -> dict[str, Any]:
    """Construct the full OpenAPI 3.1.0 spec dict."""
    all_tools = await mcp._tool_manager.get_tools()
    tool_defs: dict[str, FunctionTool] = {
        name: t for name, t in all_tools.items() if isinstance(t, FunctionTool)
    }

    paths: dict[str, Any] = {}

    for (http_method, route), tool_name in TOOL_ROUTE_MAP.items():
        method = http_method.lower()
        tool = tool_defs.get(tool_name)
        key = (http_method, route)

        # Path parameters
        path_param_names = re.findall(r"\{(\w+)\}", route)
        parameters: list[dict[str, Any]] = []
        for param in path_param_names:
            parameters.append(
                {
                    "name": param,
                    "in": "path",
                    "required": True,
                    "description": _PARAM_DESCRIPTIONS.get(param, ""),
                    "schema": {"type": "string"},
                }
            )

        # Query parameters
        extra_query = _QUERY_PARAMS.get(key, [])
        parameters.extend(extra_query)

        # Summary from tool docstring
        summary = ""
        if tool and tool.description:
            summary = tool.description.strip().splitlines()[0]

        operation: dict[str, Any] = {
            "summary": summary,
            "description": "Refer to the agent instructions for usage and parameters.",
            "operationId": _to_camel_case(tool_name),
        }

        if parameters:
            operation["parameters"] = parameters

        # Responses
        responses: dict[str, Any] = {
            "200": {
                "description": (
                    "Successful response"
                    if method != "get"
                    else _success_description(route)
                ),
                **_action_response_ref(),
            },
        }

        for code, desc in _ERROR_RESPONSES.get(key, {}).items():
            responses[code] = {"description": desc, **_action_response_ref()}

        operation["responses"] = responses

        # Request body for POST endpoints
        ref = _REQUEST_BODY_REFS.get(route)
        if method == "post" and ref:
            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": ref},
                    },
                },
            }

        if route not in paths:
            paths[route] = {}
        paths[route][method] = operation

    paths["/artifacts/{artifact_id}"] = {
        "get": {
            "summary": "Download a temporary PDF artifact.",
            "description": "Streams a previously generated PDF artifact by ID.",
            "operationId": "downloadArtifact",
            "parameters": [
                {
                    "name": "artifact_id",
                    "in": "path",
                    "required": True,
                    "description": "Temporary server-side artifact identifier.",
                    "schema": {"type": "string"},
                }
            ],
            "responses": {
                "200": _artifact_response(),
                "404": {"description": "Artifact not found or expired."},
            },
        }
    }

    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Polarion MCP Server",
            "description": (
                "HTTP wrapper around the Polarion MCP tools so agents can interact "
                "with Polarion ALM projects, work items, plans, test runs, and documents."
            ),
            "version": "1.0.0",
        },
        "servers": [{"url": "https://yourhost.com"}],
        "paths": paths,
        "components": _COMPONENTS,
    }


def _success_description(route: str) -> str:
    """Derive a short success description from the route."""
    # /actions/health → "Health check result"
    # /actions/projects → "Projects listing"
    last = route.rstrip("/").rsplit("/", 1)[-1]
    # Remove braces
    last = re.sub(r"\{.*?\}", "", last).strip("/")
    if not last:
        return "Successful response"
    return last.replace("-", " ").replace("_", " ").capitalize() + " result"


def generate_spec(output: Path | None = None) -> Path:
    """Build the OpenAPI spec and write it to *output*.

    Returns the path of the written file.
    """
    target = output or DEFAULT_OUTPUT
    target.parent.mkdir(parents=True, exist_ok=True)
    spec = asyncio.run(_build_spec())
    target.write_text(
        yaml.dump(spec, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return target


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate OpenAPI spec for the REST API."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"Output path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()
    path = generate_spec(args.output)
    print(f"Wrote OpenAPI spec to {path}")
