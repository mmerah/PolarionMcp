"""Stdio transport entry point for MCP clients that use stdio (e.g. .mcp.json configs)."""

from polarion_mcp.mcp.tools import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
