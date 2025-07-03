"""Types package for MCP server."""

from .exceptions import (
    InvalidParametersException,
    MCPException,
    PolarionConnectionException,
    ToolNotFoundException,
)
from .mcp_protocol import (
    InitializeResult,
    MCPError,
    MCPErrorCode,
    MCPMethod,
    MCPRequest,
    MCPResponse,
    MCPSession,
    ToolDefinition,
    ToolSchema,
    ToolsListResult,
)
from .tools import (
    DocumentResult,
    DocumentsParams,
    HealthCheckParams,
    HealthCheckResult,
    ProjectInfoParams,
    SearchWorkItemsParams,
    TestRunParams,
    TestRunResult,
    TestRunsParams,
    TestSpecsFromDocumentParams,
    ToolContentItem,
    ToolName,
    ToolResponse,
    WorkItemParams,
    WorkItemResult,
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
    "TestSpecsFromDocumentParams",
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
