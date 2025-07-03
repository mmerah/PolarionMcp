"""
MCP Streamable HTTP transport endpoint for FastAPI integration.
Provides Microsoft Copilot compatible MCP server functionality.
"""

import json
import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, Response, Header

from lib.polarion.polarion_driver import PolarionDriver
from ..config import settings
from ..types import (
    MCPMethod,
    MCPErrorCode,
    MCPError,
    MCPRequest,
    MCPResponse,
    MCPSession,
    InitializeResult,
    ToolSchema,
    ToolDefinition,
    ToolsListResult,
    ToolName,
    ToolContentItem,
    ToolResponse,
    WorkItemResult,
    TestRunResult,
    DocumentResult,
    HealthCheckResult,
    MCPException,
    ToolNotFoundException,
    InvalidParametersException,
    PolarionConnectionException,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["MCP"])


# Session storage for MCP sessions
mcp_sessions: Dict[str, MCPSession] = {}


class PolarionConnection:
    """Context manager for Polarion connections"""

    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id
        self.driver = None

    def __enter__(self):
        self.driver = PolarionDriver(settings.POLARION_URL)
        connection = self.driver.__enter__()
        if self.project_id:
            connection.select_project(self.project_id)
        return connection

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Optional[Any]) -> None:
        if self.driver:
            self.driver.__exit__(exc_type, exc_val, exc_tb)


def create_error_response(
    request_id: Optional[str], code: MCPErrorCode, message: str
) -> MCPResponse:
    """Create an MCP error response"""
    return MCPResponse(id=request_id, error=MCPError(code=code, message=message))

def create_success_response(
    request_id: Optional[str], result: Dict[str, Any]
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
                # Test if we can instantiate PolarionDriver (validates env vars)
                PolarionDriver(settings.POLARION_URL)
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
                    "title": getattr(workitem, "title", ""),
                    "description": getattr(workitem, "description", ""),
                    "type": getattr(workitem, "type", ""),
                    "status": getattr(workitem, "status", ""),
                    "author": getattr(workitem, "author", ""),
                    "created": str(getattr(workitem, "created", "")),
                    "updated": str(getattr(workitem, "updated", "")),
                }

            elif tool_name == "search_workitems":
                query = arguments.get("query")
                field_list = arguments.get("field_list")
                if not query:
                    raise ValueError("query is required")

                result = conn.search_workitems(query, field_list)

            elif tool_name == "get_test_runs":
                test_runs = conn.get_test_runs()
                result = []
                for tr in test_runs:
                    result.append(
                        {
                            "id": tr.id,
                            "title": getattr(tr, "title", ""),
                            "status": getattr(tr, "status", ""),
                            "created": str(getattr(tr, "created", "")),
                            "updated": str(getattr(tr, "updated", "")),
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
                    "title": getattr(test_run, "title", ""),
                    "status": getattr(test_run, "status", ""),
                    "created": str(getattr(test_run, "created", "")),
                    "updated": str(getattr(test_run, "updated", "")),
                    "description": getattr(test_run, "description", ""),
                }

            elif tool_name == "get_documents":
                documents = conn.get_documents()
                result = []
                for doc in documents:
                    result.append(
                        {
                            "id": doc.id,
                            "title": getattr(doc, "title", ""),
                            "type": getattr(doc, "type", {}).get("id", ""),
                            "created": str(getattr(doc, "created", "")),
                            "updated": str(getattr(doc, "updated", "")),
                        }
                    )
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
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON")

        # Create MCP request object
        mcp_request = MCPRequest(**request_data)

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
async def get_mcp_openapi_schema():
    """
    Get OpenAPI schema for Microsoft Copilot integration.
    Returns the schema in the format required by Microsoft Copilot Studio.
    """
    schema = {
        "swagger": "2.0",
        "info": {
            "title": "Polarion MCP Server",
            "description": "Model Context Protocol server for Polarion integration with Microsoft Copilot",
            "version": "1.0.0",
        },
        "host": "your-server-hostname.com",  # This should be configured
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
