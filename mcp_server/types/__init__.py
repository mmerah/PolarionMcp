"""Types package for MCP server."""

from .mcp_protocol import (
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
)

from .tools import (
    ToolName,
    ToolContentItem,
    ToolResponse,
    ProjectInfoParams,
    WorkItemParams,
    SearchWorkItemsParams,
    TestRunParams,
    TestRunsParams,
    DocumentsParams,
    HealthCheckParams,
    WorkItemResult,
    TestRunResult,
    DocumentResult,
    HealthCheckResult,
)

from .exceptions import (
    MCPException,
    ToolNotFoundException,
    InvalidParametersException,
    PolarionConnectionException,
)

__all__ = [
    # MCP Protocol
    "MCPMethod",
    "MCPErrorCode",
    "MCPError",
    "MCPRequest",
    "MCPResponse",
    "MCPSession",
    "InitializeResult",
    "ToolSchema",
    "ToolDefinition",
    "ToolsListResult",
    # Tools
    "ToolName",
    "ToolContentItem",
    "ToolResponse",
    "ProjectInfoParams",
    "WorkItemParams",
    "SearchWorkItemsParams",
    "TestRunParams",
    "TestRunsParams",
    "DocumentsParams",
    "HealthCheckParams",
    "WorkItemResult",
    "TestRunResult",
    "DocumentResult",
    "HealthCheckResult",
    # Exceptions
    "MCPException",
    "ToolNotFoundException",
    "InvalidParametersException",
    "PolarionConnectionException",
]