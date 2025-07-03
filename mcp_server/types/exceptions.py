"""Custom exceptions for MCP server."""

from .mcp_protocol import MCPErrorCode


class MCPException(Exception):
    """Base exception for MCP-related errors."""

    def __init__(self, message: str, code: MCPErrorCode = MCPErrorCode.INTERNAL_ERROR):
        super().__init__(message)
        self.code = code


class ToolNotFoundException(MCPException):
    """Exception raised when an unknown tool is requested."""

    def __init__(self, tool_name: str):
        super().__init__(f"Unknown tool: {tool_name}", MCPErrorCode.METHOD_NOT_FOUND)


class InvalidParametersException(MCPException):
    """Exception raised when invalid parameters are provided."""

    def __init__(self, message: str):
        super().__init__(message, MCPErrorCode.INVALID_PARAMS)


class PolarionConnectionException(MCPException):
    """Exception raised when there are issues with Polarion connection."""

    def __init__(self, message: str):
        super().__init__(message, MCPErrorCode.INTERNAL_ERROR)
