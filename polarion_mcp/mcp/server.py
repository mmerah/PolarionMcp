"""
HTTP server for polarion_mcp.

Uses FastMCP's built-in HTTP transport with two additional layers:

- CORS middleware — required for browser/cloud-based clients (Copilot Studio, etc.)
- MCPPathFix middleware — works around two client quirks:
  1. Starlette redirects POST /mcp → /mcp/ with 307; POST clients don't follow
     307 redirects, so we normalise the path before it reaches the router.
  2. Starlette's Mount("/mcp") catches /.well-known/* requests and the MCP
     handler returns 406, making clients think OAuth is misconfigured.
     We return 404 immediately instead.

The REST API routes (/actions/*) are registered via @mcp.custom_route()
decorators in polarion_mcp.rest_api.routes; FastMCP automatically includes
them alongside the /mcp endpoint.
"""

import logging
import sys

import fastmcp
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from polarion_mcp.core.settings import settings
from polarion_mcp.mcp.middleware import MCPPathFix
from polarion_mcp.mcp.tools import mcp


def run(
    host: str = "0.0.0.0",
    port: int = 8000,
    log_level: str = "INFO",
) -> None:
    """Configure logging, verify credentials, and start the HTTP server."""
    _configure_logging(log_level)
    logger = logging.getLogger(__name__)
    _verify_settings(logger)

    # Side-effect import: registers @mcp.custom_route() REST endpoints
    import polarion_mcp.rest_api.routes  # noqa: F401

    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_headers=["*"],
            allow_methods=["*"],
            allow_credentials=False,
        ),
        Middleware(MCPPathFix),
    ]

    # json_response=True: JSON bodies instead of SSE streams (all clients)
    fastmcp.settings.json_response = True

    logger.info(f"Starting Polarion MCP Server on http://{host}:{port}")
    logger.info(f"MCP endpoint:      http://{host}:{port}/mcp")
    logger.info(f"REST API endpoints: http://{host}:{port}/actions/")

    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
        log_level=log_level,
        path="/mcp",
        stateless_http=True,
        middleware=middleware,
        show_banner=False,
    )


def _configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    # stateless_http=True tears down each session immediately after the response
    # is sent; the mcp library's background message_router then hits
    # ClosedResourceError on the now-closed write stream. The response has
    # already been delivered — this is cleanup noise, not a real error.
    logging.getLogger("mcp.server.streamable_http").setLevel(logging.CRITICAL)


def _verify_settings(logger: logging.Logger) -> None:
    try:
        logger.info(f"Polarion URL: {settings.polarion_url}")
    except Exception as e:
        logger.critical(f"FATAL: Could not load settings. {e}")
        logger.critical(
            "Please ensure a .env file exists or environment variables are set."
        )
        sys.exit(1)
