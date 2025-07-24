import argparse
import logging
import os
import sys
from pathlib import Path

import uvicorn

# Add project root to path to allow imports from lib
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.middleware import CopilotStudioIDFix  # noqa: E402
from mcp_server.settings import settings  # noqa: E402
from mcp_server.tools import mcp  # noqa: E402

# --- App Setup ---

# Check if we're in Copilot Studio mode or standard MCP mode
COPILOT_STUDIO_MODE = os.getenv("COPILOT_STUDIO_MODE", "false").lower() == "true"

if COPILOT_STUDIO_MODE:
    # Copilot Studio specific configuration
    app = mcp.http_app(path="/mcp", transport="streamable-http", json_response=True)
    # Wrap the app with the crucial middleware for Copilot Studio compatibility
    app = CopilotStudioIDFix(app)  # type: ignore[assignment]
else:
    # Standard MCP configuration for Cline and other MCP clients
    # Cline uses SSE transport for remote servers
    app = mcp.http_app(path="/mcp", transport="sse")

# --- Main Execution ---


def main():
    """Sets up and runs the Polarion MCP server."""
    parser = argparse.ArgumentParser(
        description="Polarion MCP Server (Compatible with Cline and Copilot Studio)"
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to bind the server to."
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind the server to."
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level.",
    )
    args = parser.parse_args()

    # Configure logging
    log_level = getattr(logging, args.log_level.upper())
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
    # Suppress overly verbose logs from some libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)

    # Verify settings are loaded
    try:
        logger.info(
            f"Successfully loaded settings for Polarion URL: {settings.polarion_url}"
        )
    except Exception as e:
        logger.critical(f"FATAL: Could not load settings. {e}")
        logger.critical(
            "Please ensure a .env file exists or environment variables are set."
        )
        sys.exit(1)

    mode = "Copilot Studio" if COPILOT_STUDIO_MODE else "Standard MCP"
    logger.info(f"Starting Polarion MCP Server in {mode} mode")
    logger.info(f"Server running on http://{args.host}:{args.port}")
    logger.info(f"MCP endpoint available at http://{args.host}:{args.port}/mcp")

    if COPILOT_STUDIO_MODE:
        logger.info(
            f"Public tunnel URL: https://mbbgk00z-{args.port}.euw.devtunnels.ms/mcp"
        )

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level.lower(),
    )


if __name__ == "__main__":
    main()
