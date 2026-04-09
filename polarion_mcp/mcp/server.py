"""
HTTP server factory for polarion_mcp.

Supported modes
---------------
http     — Standard MCP HTTP server (Cline, Claude Code, and other MCP clients).
copilot  — Microsoft Copilot Studio compatibility mode (adds CORS + JSON-RPC ID fix).
gpt      — HTTP mode with the GPT Actions REST endpoints registered (/actions/*).
"""

import logging
import sys
from typing import Literal

import uvicorn
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from polarion_mcp.core.settings import settings
from polarion_mcp.mcp.middleware import CopilotStudioIDFix, WellKnownFilter
from polarion_mcp.mcp.tools import mcp

Mode = Literal["http", "copilot", "gpt"]
MODES = ("http", "copilot", "gpt")


def create_app(mode: Mode):
    """
    Build and return the ASGI application for the given server mode.

    Args:
        mode: One of 'http', 'copilot', or 'gpt'.

    Returns:
        An ASGI application wrapped with the appropriate middleware.
    """
    if mode == "copilot":
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
            middleware=cors,
        )
        return CopilotStudioIDFix(app)  # type: ignore[return-value]

    elif mode in ("http", "gpt"):
        if mode == "gpt":
            # Importing the routes module registers the @mcp.custom_route decorators
            import polarion_mcp.gpt_actions.routes  # noqa: F401

        app = mcp.http_app(path="/mcp", transport="streamable-http")
        return WellKnownFilter(app)  # type: ignore[return-value]

    else:
        raise ValueError(f"Unknown mode '{mode}'. Choose from: {', '.join(MODES)}")


def run(
    mode: Mode = "http",
    host: str = "0.0.0.0",
    port: int = 8000,
    log_level: str = "INFO",
) -> None:
    """Configure logging, verify credentials, and start the HTTP server."""
    _configure_logging(log_level)
    logger = logging.getLogger(__name__)
    _verify_settings(logger)

    app = create_app(mode)

    logger.info(
        f"Starting Polarion MCP Server in '{mode}' mode on http://{host}:{port}"
    )
    logger.info(f"MCP endpoint: http://{host}:{port}/mcp")
    if mode == "gpt":
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


def _verify_settings(logger: logging.Logger) -> None:
    try:
        logger.info(f"Polarion URL: {settings.polarion_url}")
    except Exception as e:
        logger.critical(f"FATAL: Could not load settings. {e}")
        logger.critical(
            "Please ensure a .env file exists or environment variables are set."
        )
        sys.exit(1)
