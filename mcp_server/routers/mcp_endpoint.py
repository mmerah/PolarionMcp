"""
MCP Streamable HTTP transport endpoint for FastAPI integration.
Provides Microsoft Copilot compatible MCP server functionality.
"""

import json
import logging
import uuid
from typing import Any, Dict, Optional, Union

from fastapi import APIRouter, Header, HTTPException, Request, Response

from lib.polarion.polarion_driver import PolarionDriver

from ..config import settings
from ..types import (
    DocumentResult,
    HealthCheckResult,
    InitializeResult,
    InvalidParametersException,
    MCPError,
    MCPErrorCode,
    MCPException,
    MCPMethod,
    MCPRequest,
    MCPResponse,
    MCPSession,
    PolarionConnectionException,
    TestRunResult,
    ToolContentItem,
    ToolDefinition,
    ToolName,
    ToolNotFoundException,
    ToolResponse,
    ToolSchema,
    ToolsListResult,
    WorkItemResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["MCP"])


# Session storage for MCP sessions
mcp_sessions: Dict[str, MCPSession] = {}


def safe_get_value(obj: Any, attr: str, default: str = "") -> str:
    """Safely extract a value from a Polarion object, handling nested attributes."""
    try:
        value = getattr(obj, attr, default)
        if value is None:
            return default

        # If it's a complex object with 'id' attribute, get the id
        if hasattr(value, "id"):
            return str(value.id)

        # If it's a complex object with 'content' attribute (like description), get the content
        if hasattr(value, "content"):
            return str(value.content)

        # Otherwise, just convert to string
        return str(value)
    except Exception:
        return default


class PolarionConnection:
    """Context manager for Polarion connections"""

    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id
        self.driver = None

    def __enter__(self):
        self.driver = PolarionDriver(
            settings.POLARION_URL, settings.POLARION_USER, settings.POLARION_TOKEN
        )
        connection = self.driver.__enter__()
        if self.project_id:
            connection.select_project(self.project_id)
        return connection

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        if self.driver:
            self.driver.__exit__(exc_type, exc_val, exc_tb)


def create_error_response(
    request_id: Optional[Union[str, int]], code: MCPErrorCode, message: str
) -> MCPResponse:
    """Create an MCP error response"""
    return MCPResponse(id=request_id, error=MCPError(code=code, message=message))


def create_success_response(
    request_id: Optional[Union[str, int]], result: Dict[str, Any]
) -> MCPResponse:
    """Create an MCP success response"""
    return MCPResponse(id=request_id, result=result)


async def handle_initialize(params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Handle MCP initialize request"""
    result = InitializeResult(
        protocolVersion="2024-11-05",
        capabilities={"tools": {}, "resources": {}, "logging": {}},
        serverInfo={"name": "polarion-mcp-server", "version": "1.0.0"},
    )
    return result.model_dump()


async def handle_tools_list(params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Handle tools/list request"""
    tools = [
        ToolDefinition(
            name=ToolName.GET_PROJECT_INFO,
            description="Get information about a Polarion project",
            inputSchema=ToolSchema(
                type="object",
                properties={
                    "project_id": {
                        "type": "string",
                        "description": "The ID of the Polarion project",
                    }
                },
                required=["project_id"],
            ),
        ),
        ToolDefinition(
            name=ToolName.GET_WORKITEM,
            description="Get a specific work item from a Polarion project",
            inputSchema=ToolSchema(
                type="object",
                properties={
                    "project_id": {
                        "type": "string",
                        "description": "The ID of the Polarion project",
                    },
                    "workitem_id": {
                        "type": "string",
                        "description": "The ID of the work item to retrieve",
                    },
                },
                required=["project_id", "workitem_id"],
            ),
        ),
        ToolDefinition(
            name=ToolName.SEARCH_WORKITEMS,
            description="Search for work items in a Polarion project",
            inputSchema=ToolSchema(
                type="object",
                properties={
                    "project_id": {
                        "type": "string",
                        "description": "The ID of the Polarion project",
                    },
                    "query": {
                        "type": "string",
                        "description": "Lucene query string for searching work items",
                    },
                    "field_list": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of fields to return",
                    },
                },
                required=["project_id", "query"],
            ),
        ),
        ToolDefinition(
            name=ToolName.GET_TEST_RUNS,
            description="Get all test runs from a Polarion project",
            inputSchema=ToolSchema(
                type="object",
                properties={
                    "project_id": {
                        "type": "string",
                        "description": "The ID of the Polarion project",
                    }
                },
                required=["project_id"],
            ),
        ),
        ToolDefinition(
            name=ToolName.GET_TEST_RUN,
            description="Get a specific test run from a Polarion project",
            inputSchema=ToolSchema(
                type="object",
                properties={
                    "project_id": {
                        "type": "string",
                        "description": "The ID of the Polarion project",
                    },
                    "test_run_id": {
                        "type": "string",
                        "description": "The ID of the test run to retrieve",
                    },
                },
                required=["project_id", "test_run_id"],
            ),
        ),
        ToolDefinition(
            name=ToolName.GET_DOCUMENTS,
            description="Get all documents from a Polarion project",
            inputSchema=ToolSchema(
                type="object",
                properties={
                    "project_id": {
                        "type": "string",
                        "description": "The ID of the Polarion project",
                    }
                },
                required=["project_id"],
            ),
        ),
        ToolDefinition(
            name=ToolName.GET_TEST_SPECS_FROM_DOCUMENT,
            description="Get test specifications from a specific document in a Polarion project",
            inputSchema=ToolSchema(
                type="object",
                properties={
                    "project_id": {
                        "type": "string",
                        "description": "The ID of the Polarion project",
                    },
                    "document_id": {
                        "type": "string",
                        "description": "The ID of the document to get test specs from",
                    },
                },
                required=["project_id", "document_id"],
            ),
        ),
        ToolDefinition(
            name=ToolName.HEALTH_CHECK,
            description="Check the health of the Polarion connection",
            inputSchema=ToolSchema(
                type="object",
                properties={},
                required=[],
            ),
        ),
    ]

    result = ToolsListResult(tools=tools)
    return result.model_dump()


async def handle_tool_call(tool_name: str, arguments: Dict[str, Any]) -> ToolResponse:
    """Handle tool call requests"""
    try:
        if tool_name == ToolName.HEALTH_CHECK:
            try:
                # Test if we can instantiate PolarionDriver (validates parameters)
                PolarionDriver(
                    settings.POLARION_URL,
                    settings.POLARION_USER,
                    settings.POLARION_TOKEN,
                )
                health_result = HealthCheckResult(
                    status="healthy",
                    polarion_url=settings.POLARION_URL,
                    polarion_user=settings.POLARION_USER,
                    message="Connection parameters are valid",
                )
                return ToolResponse(
                    content=[
                        ToolContentItem(
                            type="text",
                            text=json.dumps(health_result.model_dump(), indent=2),
                        )
                    ]
                )
            except Exception as e:
                health_result = HealthCheckResult(
                    status="unhealthy",
                    error=str(e),
                    message="Check your Polarion connection parameters",
                )
                return ToolResponse(
                    content=[
                        ToolContentItem(
                            type="text",
                            text=json.dumps(health_result.model_dump(), indent=2),
                        )
                    ]
                )

        project_id = arguments.get("project_id")
        if not project_id:
            raise InvalidParametersException("project_id is required for this tool")

        with PolarionConnection(project_id) as conn:
            if tool_name == "get_project_info":
                result = conn.get_project_info()

            elif tool_name == "get_workitem":
                workitem_id = arguments.get("workitem_id")
                if not workitem_id:
                    raise ValueError("workitem_id is required")

                workitem = conn.get_workitem(workitem_id)
                if not workitem:
                    raise ValueError(f"Work item {workitem_id} not found")

                result = {
                    "id": workitem.id,
                    "title": safe_get_value(workitem, "title"),
                    "description": safe_get_value(workitem, "description"),
                    "type": safe_get_value(workitem, "type"),
                    "status": safe_get_value(workitem, "status"),
                    "author": safe_get_value(workitem, "author"),
                    "created": safe_get_value(workitem, "created"),
                    "updated": safe_get_value(workitem, "updated"),
                }

            elif tool_name == "search_workitems":
                query = arguments.get("query")
                field_list = arguments.get("field_list")
                if not query:
                    raise ValueError("query is required")

                workitems = conn.search_workitems(query, field_list)
                result = []

                for wi in workitems:
                    # Handle both dict-like results and WorkItem objects
                    if hasattr(wi, "__dict__"):  # It's a WorkItem object
                        item = {
                            "id": wi.id,
                            "title": safe_get_value(wi, "title"),
                            "type": safe_get_value(wi, "type"),
                            "status": safe_get_value(wi, "status"),
                            "description": safe_get_value(wi, "description"),
                            "author": safe_get_value(wi, "author"),
                            "created": safe_get_value(wi, "created"),
                            "updated": safe_get_value(wi, "updated"),
                        }
                    else:  # It's already a dict
                        item = {
                            "id": wi.get("id", ""),
                            "title": wi.get("title", ""),
                            "type": (
                                wi.get("type", {}).get("id", "")
                                if isinstance(wi.get("type"), dict)
                                else wi.get("type", "")
                            ),
                            "status": (
                                wi.get("status", {}).get("id", "")
                                if isinstance(wi.get("status"), dict)
                                else wi.get("status", "")
                            ),
                            "description": (
                                wi.get("description", {}).get("content", "")
                                if isinstance(wi.get("description"), dict)
                                else wi.get("description", "")
                            ),
                            "author": (
                                wi.get("author", {}).get("id", "")
                                if isinstance(wi.get("author"), dict)
                                else wi.get("author", "")
                            ),
                            "created": str(wi.get("created", "")),
                            "updated": str(wi.get("updated", "")),
                        }
                    result.append(item)

            elif tool_name == "get_test_runs":
                test_runs = conn.get_test_runs()
                result = []
                for tr in test_runs:
                    result.append(
                        {
                            "id": tr.id,
                            "title": safe_get_value(tr, "title"),
                            "status": safe_get_value(tr, "status"),
                            "created": safe_get_value(tr, "created"),
                            "updated": safe_get_value(tr, "updated"),
                        }
                    )

            elif tool_name == "get_test_run":
                test_run_id = arguments.get("test_run_id")
                if not test_run_id:
                    raise ValueError("test_run_id is required")

                test_run = conn.get_test_run(test_run_id)
                if not test_run:
                    raise ValueError(f"Test run {test_run_id} not found")

                result = {
                    "id": test_run.id,
                    "title": safe_get_value(test_run, "title"),
                    "status": safe_get_value(test_run, "status"),
                    "created": safe_get_value(test_run, "created"),
                    "updated": safe_get_value(test_run, "updated"),
                    "description": safe_get_value(test_run, "description"),
                }

            elif tool_name == "get_documents":
                documents = conn.get_documents()
                result = []
                for doc in documents:
                    result.append(
                        {
                            "id": doc.id,
                            "title": safe_get_value(doc, "title"),
                            "type": safe_get_value(doc, "type"),
                            "created": safe_get_value(doc, "created"),
                            "updated": safe_get_value(doc, "updated"),
                        }
                    )

            elif tool_name == "get_test_specs_from_document":
                document_id = arguments.get("document_id")
                if not document_id:
                    raise ValueError("document_id is required")

                # Get the document
                document = conn.get_test_specs_doc(document_id)
                if not document:
                    raise ValueError(f"Document {document_id} not found")

                # Get test spec IDs from the document
                test_spec_ids = conn.test_spec_ids_in_doc(document)

                result = {
                    "document_id": document_id,
                    "document_title": safe_get_value(document, "title"),
                    "test_spec_ids": list(test_spec_ids),
                    "total_test_specs": len(test_spec_ids),
                }

            else:
                raise ValueError(f"Unknown tool: {tool_name}")

        return ToolResponse(
            content=[
                ToolContentItem(
                    type="text",
                    text=json.dumps(result, indent=2),
                )
            ]
        )

    except MCPException as e:
        logger.error(f"MCP Error in tool {tool_name}: {e}")
        return ToolResponse(
            content=[
                ToolContentItem(
                    type="text",
                    text=f"Error: {str(e)}",
                )
            ],
            isError=True,
        )
    except Exception as e:
        logger.error(f"Unexpected error in tool {tool_name}: {e}")
        return ToolResponse(
            content=[
                ToolContentItem(
                    type="text",
                    text=f"Internal error: {str(e)}",
                )
            ],
            isError=True,
        )


async def handle_mcp_request(request: MCPRequest) -> MCPResponse:
    """Handle MCP request and return appropriate response"""
    try:
        if request.method == "initialize":
            result = await handle_initialize(request.params)
            return create_success_response(request.id, result)

        elif request.method == "notifications/initialized":
            # This is a notification from client that it's initialized
            # We just acknowledge it
            return create_success_response(request.id, {})

        elif request.method == "tools/list":
            result = await handle_tools_list(request.params)
            return create_success_response(request.id, result)

        elif request.method == "tools/call":
            if not request.params:
                return create_error_response(request.id, -32602, "Missing parameters")

            tool_name = request.params.get("name")
            arguments = request.params.get("arguments", {})

            if not tool_name:
                return create_error_response(request.id, -32602, "Missing tool name")

            tool_response = await handle_tool_call(tool_name, arguments)
            return create_success_response(request.id, tool_response.model_dump())

        elif request.method == "resources/list":
            # We don't implement resources yet, return empty list
            return create_success_response(request.id, {"resources": []})

        elif request.method == "resources/templates/list":
            # We don't implement resource templates yet, return empty list
            return create_success_response(request.id, {"resourceTemplates": []})

        elif request.method == "notifications/cancelled":
            # This is a notification that operation was cancelled
            # We just acknowledge it
            return create_success_response(request.id, {})

        else:
            return create_error_response(
                request.id, -32601, f"Method not found: {request.method}"
            )

    except Exception as e:
        logger.error(f"Error handling MCP request: {e}")
        return create_error_response(request.id, -32603, f"Internal error: {str(e)}")


@router.post("/")
async def mcp_streamable_endpoint(
    request: Request,
    mcp_session_id: Optional[str] = Header(None, alias="Mcp-Session-Id"),
):
    """
    MCP Streamable HTTP transport endpoint.
    Compatible with Microsoft Copilot and other MCP clients.
    """
    try:
        # Parse request body
        body = await request.body()
        if not body:
            raise HTTPException(status_code=400, detail="Empty request body")

        try:
            request_data = json.loads(body)
        except json.JSONDecodeError as e:
            # Return JSON-RPC error for invalid JSON
            error_response = create_error_response(
                None, -32700, f"Parse error: {str(e)}"
            )
            return Response(
                content=error_response.model_dump_json(),
                media_type="application/json",
            )

        # Create MCP request object with proper error handling
        try:
            mcp_request = MCPRequest(**request_data)
        except Exception as e:
            # Return JSON-RPC error for invalid request format
            error_response = create_error_response(
                request_data.get("id"), -32600, f"Invalid request: {str(e)}"
            )
            return Response(
                content=error_response.model_dump_json(),
                media_type="application/json",
            )

        # Generate session ID if this is an initialize request
        session_id = mcp_session_id
        if mcp_request.method == MCPMethod.INITIALIZE and not session_id:
            session_id = str(uuid.uuid4())
            mcp_sessions[session_id] = MCPSession(
                session_id=session_id,
                initialized=True,
            )

        # Handle the request
        mcp_response = await handle_mcp_request(mcp_request)

        # Prepare response
        response_data = mcp_response.model_dump(exclude_none=True)

        # Set headers for MCP
        headers = {"Content-Type": "application/json", "Cache-Control": "no-cache"}

        if session_id and mcp_request.method == MCPMethod.INITIALIZE:
            headers["Mcp-Session-Id"] = session_id

        return Response(
            content=json.dumps(response_data),
            media_type="application/json",
            headers=headers,
        )

    except Exception as e:
        logger.error(f"Error in MCP endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema")
async def get_mcp_openapi_schema(request: Request):
    """
    Get OpenAPI schema for Microsoft Copilot integration.
    Returns the schema in the format required by Microsoft Copilot Studio.
    """
    # Dynamically determine the host from the request
    host = request.headers.get("host", f"{settings.SERVER_HOST}:{settings.SERVER_PORT}")

    schema = {
        "swagger": "2.0",
        "info": {
            "title": "Polarion MCP Server",
            "description": "Model Context Protocol server for Polarion integration with Microsoft Copilot",
            "version": "1.0.0",
        },
        "host": host,
        "basePath": "/",
        "schemes": ["https"],
        "paths": {
            "/mcp": {
                "post": {
                    "summary": "Polarion MCP Server Streamable HTTP Endpoint",
                    "description": "MCP Streamable HTTP transport endpoint for Polarion tools",
                    "x-ms-agentic-protocol": "mcp-streamable-1.0",
                    "operationId": "InvokeMCP",
                    "consumes": ["application/json"],
                    "produces": ["application/json"],
                    "parameters": [
                        {
                            "name": "body",
                            "in": "body",
                            "required": True,
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "jsonrpc": {"type": "string", "enum": ["2.0"]},
                                    "id": {"type": "string"},
                                    "method": {"type": "string"},
                                    "params": {"type": "object"},
                                },
                                "required": ["jsonrpc", "method"],
                            },
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "jsonrpc": {"type": "string"},
                                    "id": {"type": "string"},
                                    "result": {"type": "object"},
                                    "error": {"type": "object"},
                                },
                            },
                        }
                    },
                }
            }
        },
    }

    return schema
