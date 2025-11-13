"""
HTTP routes and metadata that expose Polarion tools to GPT Actions.

These routes wrap the underlying FastMCP tools so they can be called through
standard HTTP requests defined in the OpenAPI definition that GPT Actions
consumes. The endpoints all return structured JSON responses that include the
plain-text result produced by the MCP tool along with any structured payload
if one is available.
"""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

import pydantic_core
import yaml
from fastmcp.exceptions import NotFoundError, ToolError
from mcp.types import TextContent
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from mcp_server.tools import mcp

logger = logging.getLogger(__name__)

# Paths for static metadata that back the routes below
REPO_ROOT = Path(__file__).resolve().parents[1]
OPENAPI_SPEC_PATH = REPO_ROOT / "openapi.yaml"

# Map HTTP method/path pairs to the underlying MCP tool name so we can surface
# the original docstrings inside the generated OpenAPI document.
TOOL_ROUTE_MAP: dict[tuple[str, str], str] = {
    ("GET", "/actions/health"): "health_check",
    ("GET", "/actions/projects"): "list_projects",
    ("GET", "/actions/projects/{project_alias}"): "get_project_info",
    ("GET", "/actions/projects/{project_alias}/types"): "get_project_types",
    ("GET", "/actions/projects/{project_alias}/named-queries"): "get_named_queries",
    ("GET", "/actions/projects/{project_alias}/workitems/{workitem_id}"): "get_workitem",
    ("POST", "/actions/projects/{project_alias}/workitems/search"): "search_workitems",
    ("GET", "/actions/projects/{project_alias}/workitems/discover"): "discover_work_item_types",
    ("GET", "/actions/projects/{project_alias}/test-runs"): "get_test_runs",
    ("GET", "/actions/projects/{project_alias}/test-runs/{test_run_id}"): "get_test_run",
    ("GET", "/actions/projects/{project_alias}/documents"): "get_documents",
    (
        "GET",
        "/actions/projects/{project_alias}/documents/test-specs",
    ): "get_test_specs_from_document",
    ("GET", "/actions/projects/{project_alias}/plans"): "get_plans",
    ("GET", "/actions/projects/{project_alias}/plans/{plan_id}"): "get_plan",
    (
        "GET",
        "/actions/projects/{project_alias}/plans/{plan_id}/workitems",
    ): "get_plan_workitems",
    ("POST", "/actions/projects/{project_alias}/plans/search"): "search_plans",
}

# Load the OpenAPI document once during startup so requests are fast. If the
# file is missing or invalid we log and continue; the routes will respond with
# a helpful error instead of crashing the server.
try:
    _OPENAPI_SPEC = yaml.safe_load(OPENAPI_SPEC_PATH.read_text(encoding="utf-8"))
except FileNotFoundError:
    logger.warning("OpenAPI specification not found at %s", OPENAPI_SPEC_PATH)
    _OPENAPI_SPEC = None
except yaml.YAMLError as exc:
    logger.error("Failed to parse OpenAPI specification: %s", exc)
    _OPENAPI_SPEC = None

async def _run_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Execute the underlying FastMCP tool and normalise the result into a JSON
    payload suitable for HTTP responses.
    """
    try:
        tool = await mcp._tool_manager.get_tool(tool_name)
    except NotFoundError:
        return {
            "tool": tool_name,
            "error": f"Tool '{tool_name}' is not registered on this server.",
        }

    try:
        tool_result = await tool.run(arguments)
    except pydantic_core.ValidationError as exc:
        logger.debug("Validation error for tool %s: %s", tool_name, exc)
        return {
            "tool": tool_name,
            "error": "Invalid arguments",
            "details": json.loads(exc.json()),
        }
    except ToolError as exc:
        logger.error("ToolError while running %s: %s", tool_name, exc)
        return {
            "tool": tool_name,
            "error": str(exc),
        }
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.exception("Unexpected error while running %s", tool_name)
        return {
            "tool": tool_name,
            "error": "Unexpected error while executing the tool",
            "details": str(exc),
        }

    text_parts: list[str] = []
    for block in tool_result.content or []:
        if isinstance(block, TextContent):
            text_parts.append(block.text)
        else:
            text_parts.append(str(block))

    payload: dict[str, Any] = {
        "tool": tool_name,
        "result_text": "".join(text_parts),
    }
    if tool_result.structured_content:
        payload["structured_result"] = tool_result.structured_content
    return payload


def _error_response(
    tool_name: str,
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    details: Any | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "tool": tool_name,
        "error": message,
    }
    if details is not None:
        body["details"] = details
    return JSONResponse(body, status_code=status_code)


@mcp.custom_route("/actions/health", methods=["GET"])
async def health_action(request: Request) -> JSONResponse:
    payload = await _run_tool("health_check", {})
    status_code = (
        status.HTTP_200_OK if "error" not in payload else status.HTTP_502_BAD_GATEWAY
    )
    return JSONResponse(payload, status_code=status_code)


@mcp.custom_route("/actions/projects", methods=["GET"])
async def list_projects_action(request: Request) -> JSONResponse:
    payload = await _run_tool("list_projects", {})
    return JSONResponse(payload)


@mcp.custom_route("/actions/projects/{project_alias}", methods=["GET"])
async def get_project_action(request: Request) -> JSONResponse:
    project_alias = request.path_params["project_alias"]
    payload = await _run_tool("get_project_info", {"project_alias": project_alias})
    status_code = (
        status.HTTP_200_OK if "error" not in payload else status.HTTP_404_NOT_FOUND
    )
    return JSONResponse(payload, status_code=status_code)


@mcp.custom_route("/actions/projects/{project_alias}/types", methods=["GET"])
async def get_project_types_action(request: Request) -> JSONResponse:
    project_alias = request.path_params["project_alias"]
    payload = await _run_tool(
        "get_project_types", {"project_alias_or_id": project_alias}
    )
    return JSONResponse(payload)


@mcp.custom_route("/actions/projects/{project_alias}/named-queries", methods=["GET"])
async def get_named_queries_action(request: Request) -> JSONResponse:
    project_alias = request.path_params["project_alias"]
    payload = await _run_tool(
        "get_named_queries", {"project_alias_or_id": project_alias}
    )
    return JSONResponse(payload)


@mcp.custom_route(
    "/actions/projects/{project_alias}/workitems/{workitem_id}",
    methods=["GET"],
)
async def get_workitem_action(request: Request) -> JSONResponse:
    params = request.path_params
    payload = await _run_tool(
        "get_workitem",
        {
            "project_alias": params["project_alias"],
            "workitem_id": params["workitem_id"],
        },
    )
    status_code = (
        status.HTTP_200_OK if "error" not in payload else status.HTTP_404_NOT_FOUND
    )
    return JSONResponse(payload, status_code=status_code)


@mcp.custom_route(
    "/actions/projects/{project_alias}/workitems/search",
    methods=["POST"],
)
async def search_workitems_action(request: Request) -> JSONResponse:
    project_alias = request.path_params["project_alias"]
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _error_response(
            "search_workitems",
            "Request body must be valid JSON.",
        )

    query = body.get("query")
    if not isinstance(query, str) or not query.strip():
        return _error_response(
            "search_workitems",
            "The 'query' field is required and must be a non-empty string.",
        )
    field_list = body.get("field_list")
    if field_list is not None and not isinstance(field_list, str):
        return _error_response(
            "search_workitems",
            "The 'field_list' field must be a comma-separated string when provided.",
        )

    payload = await _run_tool(
        "search_workitems",
        {
            "project_alias": project_alias,
            "query": query,
            "field_list": field_list,
        },
    )
    return JSONResponse(payload)


@mcp.custom_route(
    "/actions/projects/{project_alias}/workitems/discover",
    methods=["GET"],
)
async def discover_workitem_types_action(request: Request) -> JSONResponse:
    project_alias = request.path_params["project_alias"]
    limit_param = request.query_params.get("limit")
    limit = None
    if limit_param is not None:
        try:
            limit = int(limit_param)
            if limit <= 0:
                raise ValueError
        except ValueError:
            return _error_response(
                "discover_work_item_types",
                "Query parameter 'limit' must be a positive integer when supplied.",
            )

    arguments: dict[str, Any] = {"project_alias": project_alias}
    if limit is not None:
        arguments["limit"] = limit
    payload = await _run_tool("discover_work_item_types", arguments)
    return JSONResponse(payload)


@mcp.custom_route("/actions/projects/{project_alias}/test-runs", methods=["GET"])
async def list_test_runs_action(request: Request) -> JSONResponse:
    project_alias = request.path_params["project_alias"]
    payload = await _run_tool("get_test_runs", {"project_alias": project_alias})
    return JSONResponse(payload)


@mcp.custom_route(
    "/actions/projects/{project_alias}/test-runs/{test_run_id}",
    methods=["GET"],
)
async def get_test_run_action(request: Request) -> JSONResponse:
    params = request.path_params
    payload = await _run_tool(
        "get_test_run",
        {
            "project_alias": params["project_alias"],
            "test_run_id": params["test_run_id"],
        },
    )
    status_code = (
        status.HTTP_200_OK if "error" not in payload else status.HTTP_404_NOT_FOUND
    )
    return JSONResponse(payload, status_code=status_code)


@mcp.custom_route("/actions/projects/{project_alias}/documents", methods=["GET"])
async def list_documents_action(request: Request) -> JSONResponse:
    project_alias = request.path_params["project_alias"]
    payload = await _run_tool("get_documents", {"project_alias": project_alias})
    return JSONResponse(payload)


@mcp.custom_route(
    "/actions/projects/{project_alias}/documents/test-specs",
    methods=["GET"],
)
async def get_test_specs_from_document_action(request: Request) -> JSONResponse:
    project_alias = request.path_params["project_alias"]
    document_path = request.query_params.get("document_path")
    if not document_path:
        return _error_response(
            "get_test_specs_from_document",
            "Query parameter 'document_path' is required.",
        )
    payload = await _run_tool(
        "get_test_specs_from_document",
        {"project_alias": project_alias, "document_id": document_path},
    )
    status_code = (
        status.HTTP_200_OK if "error" not in payload else status.HTTP_404_NOT_FOUND
    )
    return JSONResponse(payload, status_code=status_code)


@mcp.custom_route("/actions/projects/{project_alias}/plans", methods=["GET"])
async def list_plans_action(request: Request) -> JSONResponse:
    project_alias = request.path_params["project_alias"]
    payload = await _run_tool("get_plans", {"project_alias": project_alias})
    return JSONResponse(payload)


@mcp.custom_route(
    "/actions/projects/{project_alias}/plans/{plan_id}",
    methods=["GET"],
)
async def get_plan_action(request: Request) -> JSONResponse:
    params = request.path_params
    payload = await _run_tool(
        "get_plan",
        {
            "project_alias": params["project_alias"],
            "plan_id": params["plan_id"],
        },
    )
    status_code = (
        status.HTTP_200_OK if "error" not in payload else status.HTTP_404_NOT_FOUND
    )
    return JSONResponse(payload, status_code=status_code)


@mcp.custom_route(
    "/actions/projects/{project_alias}/plans/{plan_id}/workitems",
    methods=["GET"],
)
async def get_plan_workitems_action(request: Request) -> JSONResponse:
    params = request.path_params
    payload = await _run_tool(
        "get_plan_workitems",
        {
            "project_alias": params["project_alias"],
            "plan_id": params["plan_id"],
        },
    )
    status_code = (
        status.HTTP_200_OK if "error" not in payload else status.HTTP_404_NOT_FOUND
    )
    return JSONResponse(payload, status_code=status_code)


@mcp.custom_route(
    "/actions/projects/{project_alias}/plans/search",
    methods=["POST"],
)
async def search_plans_action(request: Request) -> JSONResponse:
    project_alias = request.path_params["project_alias"]
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _error_response(
            "search_plans",
            "Request body must be valid JSON.",
        )

    query = body.get("query", "")
    if not isinstance(query, str):
        return _error_response(
            "search_plans",
            "The 'query' field must be a string.",
        )

    payload = await _run_tool(
        "search_plans",
        {
            "project_alias": project_alias,
            "query": query,
        },
    )
    return JSONResponse(payload)


@mcp.custom_route("/openapi.yaml", methods=["GET"])
async def openapi_yaml(request: Request) -> Response:
    if _OPENAPI_SPEC is None:
        return Response(
            "OpenAPI specification is not available.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="text/plain",
        )
    return Response(
        OPENAPI_SPEC_PATH.read_text(encoding="utf-8"),
        media_type="application/yaml",
    )


@mcp.custom_route("/openapi.json", methods=["GET"])
async def openapi_json(request: Request) -> JSONResponse:
    if _OPENAPI_SPEC is None:
        return JSONResponse(
            {"error": "OpenAPI specification is not available."},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    spec = deepcopy(_OPENAPI_SPEC)
    base_url = str(request.base_url).rstrip("/")
    if not base_url:
        base_url = "/"
    spec["servers"] = [{"url": base_url}]

    # Stamp tool metadata so the OpenAPI document explicitly references the
    # underlying MCP tool without duplicating long docstrings (see
    # agent_instructions.md for full guidance).
    paths = spec.get("paths", {})
    for route, methods in paths.items():
        if not isinstance(methods, dict):
            continue

        for method, operation in methods.items():
            if not isinstance(operation, dict):
                continue

            key = (method.upper(), route)
            tool_name = TOOL_ROUTE_MAP.get(key)
            if not tool_name:
                continue

            # Surface the association for debugging/metadata consumers.
            operation.setdefault("x-tool-name", tool_name)

    return JSONResponse(spec)
