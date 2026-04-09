"""Stdio entry point for Claude Code and other MCP clients that use stdio transport."""

import sys
from pathlib import Path

# Add project root to path to allow imports from lib
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.tools import mcp  # noqa: E402

if __name__ == "__main__":
    mcp.run(transport="stdio")
