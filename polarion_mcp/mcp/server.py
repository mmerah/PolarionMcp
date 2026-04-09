"""
HTTP server factory for polarion_mcp.

A single HTTP mode works for all clients:
- Cline / Claude Code  — standard MCP HTTP clients
- Microsoft Copilot Studio — needs stateless requests, CORS, path normalisation
- GPT Actions — uses the /actions/* REST routes registered alongside /mcp

stateless_http=True:  each POST gets its own session, enabling parallel tool calls.
json_response=True:   JSON bodies instead of SSE streams (compatible with all clients).
CORS:                 required for browser/cloud-based clients (Copilot Studio, etc.)
"""

import logging
import sys

import uvicorn
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from polarion_mcp.core.settings import settings
from polarion_mcp.mcp.middleware import MCPPathFix
from polarion_mcp.mcp.tools import mcp


def create_app():
    """Build and return the ASGI application."""
    # Register GPT Actions REST routes (/actions/*)
    import polarion_mcp.gpt_actions.routes  # noqa: F401

    cors = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_headers=["*"],
            allow_methods=["*"],
            allow_credentials=False,
        )
    ]
    app = mcp.http_app(
        path="/mcp",
        transport="streamable-http",
        json_response=True,
        stateless_http=True,
        middleware=cors,
    )
    return MCPPathFix(app)  # type: ignore[return-value]


def run(
    host: str = "0.0.0.0",
    port: int = 8000,
    log_level: str = "INFO",
) -> None:
    """Configure logging, verify credentials, and start the HTTP server."""
    _configure_logging(log_level)
    logger = logging.getLogger(__name__)
    _verify_settings(logger)

    app = create_app()

    logger.info(f"Starting Polarion MCP Server on http://{host}:{port}")
    logger.info(f"MCP endpoint:          http://{host}:{port}/mcp")
    logger.info(f"GPT Actions endpoints: http://{host}:{port}/actions/")

    uvicorn.run(app, host=host, port=port, log_level=log_level.lower())


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
