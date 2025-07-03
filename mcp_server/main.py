"""
Main entry point for the MCP Server for Polarion access.
Provides both FastAPI REST endpoints and MCP Streamable HTTP transport.
"""

from typing import Dict

from fastapi import FastAPI, HTTPException

from lib.polarion.polarion_driver import PolarionDriver

from .routers import polarion, mcp_endpoint

app = FastAPI(
    title="MCP Server for Polarion",
    description="Model Context Protocol (MCP) server with HTTPS and OpenAPI support for Polarion integration. Supports both REST API and MCP Streamable HTTP transport for Microsoft Copilot and other AI assistants.",
    version="1.0.0",
    openapi_tags=[
        {"name": "MCP", "description": "Model Context Protocol endpoints"},
        {"name": "Polarion", "description": "Direct Polarion API endpoints"},
        {"name": "Health", "description": "Health and status endpoints"},
    ]
)

app.include_router(polarion.router)
app.include_router(mcp_endpoint.router)


@app.get("/", tags=["Root"])
def read_root() -> Dict[str, str]:
    """
    Root endpoint to check if the server is running.
    """
    return {"message": "Welcome to the MCP Server for Polarion", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
def health_check() -> Dict[str, str]:
    """
    Health check endpoint to verify the server and Polarion connection.
    """
    try:
        # Test if we can instantiate the PolarionDriver (checks env vars)
        from .config import settings

        PolarionDriver(settings.POLARION_URL)
        return {"status": "healthy", "polarion_config": "valid"}
    except ValueError as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
