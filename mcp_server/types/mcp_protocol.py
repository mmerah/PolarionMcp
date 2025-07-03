"""MCP protocol types and models."""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel

from .tools import ToolName


class MCPMethod(str, Enum):
    """MCP protocol methods."""

    INITIALIZE = "initialize"
    NOTIFICATIONS_INITIALIZED = "notifications/initialized"
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"
    RESOURCES_LIST = "resources/list"
    RESOURCES_TEMPLATES_LIST = "resources/templates/list"
    NOTIFICATIONS_CANCELLED = "notifications/cancelled"


class MCPErrorCode(int, Enum):
    """JSON-RPC error codes used in MCP protocol."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


class MCPError(BaseModel):
    """MCP protocol error model."""

    code: MCPErrorCode
    message: str
    data: Optional[Dict[str, Any]] = None


class MCPRequest(BaseModel):
    """MCP protocol request model."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: Optional[Union[str, int]] = None
    method: MCPMethod
    params: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """MCP protocol response model."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[MCPError] = None


class MCPSession(BaseModel):
    """MCP session model."""

    session_id: str
    initialized: bool = False


class InitializeResult(BaseModel):
    """Result model for MCP initialize method."""

    protocolVersion: str
    capabilities: Dict[str, Dict[str, Any]]
    serverInfo: Dict[str, str]


class ToolSchema(BaseModel):
    """Tool input schema model."""

    type: str
    properties: Dict[str, Any]
    required: List[str]


class ToolDefinition(BaseModel):
    """Tool definition model."""

    name: ToolName
    description: str
    inputSchema: ToolSchema


class ToolsListResult(BaseModel):
    """Result model for tools/list method."""

    tools: List[ToolDefinition]
