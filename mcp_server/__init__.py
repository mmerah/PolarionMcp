"""Polarion MCP Server package."""

import asyncio

from .server import serve


def main():
    """Main entry point for the Polarion MCP server."""
    asyncio.run(serve())


if __name__ == "__main__":
    main()
