"""FastAPI HTTP server wrapper for Polarion MCP server.

This module provides a REST API wrapper around the existing MCP server handlers,
enabling integration with Microsoft Copilot Studio and other HTTP clients.
"""

import argparse
import ssl
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mcp_server.server import (
    DiscoverTypesParams,
    DocumentsParams,
    HealthCheckParams,
    PolarionSettings,
    ProjectInfoParams,
    SearchWorkItemsParams,
    TestRunParams,
    TestRunsParams,
    TestSpecsFromDocumentParams,
    WorkItemParams,
    _handle_discover_work_item_types,
    _handle_get_documents,
    _handle_get_project_info,
    _handle_get_test_run,
    _handle_get_test_runs,
    _handle_get_test_specs_from_document,
    _handle_get_workitem,
    _handle_health_check,
    _handle_search_workitems,
)

# Create FastAPI app
app = FastAPI(
    title="Polarion MCP HTTP API",
    description="REST API for accessing Polarion ALM data through MCP server handlers",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize settings
try:
    settings = PolarionSettings()
except ValueError as e:
    print(f"Configuration error: {e}")
    print("Please ensure environment variables are set correctly.")
    exit(1)


@app.post("/tools/health_check")
async def health_check(params: Optional[HealthCheckParams] = None):
    """Check the health of the Polarion connection."""
    try:
        arguments = params.model_dump() if params else {}
        result = await _handle_health_check(arguments, settings)
        return {"content": [{"type": item.type, "text": item.text} for item in result]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/get_project_info")
async def get_project_info(params: ProjectInfoParams):
    """Get information about a Polarion project."""
    try:
        result = await _handle_get_project_info(params.model_dump(), settings)
        return {"content": [{"type": item.type, "text": item.text} for item in result]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/get_workitem")
async def get_workitem(params: WorkItemParams):
    """Get a specific work item from a Polarion project."""
    try:
        result = await _handle_get_workitem(params.model_dump(), settings)
        return {"content": [{"type": item.type, "text": item.text} for item in result]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/search_workitems")
async def search_workitems(params: SearchWorkItemsParams):
    """Search for work items in a Polarion project using Lucene query syntax."""
    try:
        result = await _handle_search_workitems(params.model_dump(), settings)
        return {"content": [{"type": item.type, "text": item.text} for item in result]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/get_test_runs")
async def get_test_runs(params: TestRunsParams):
    """Get all test runs from a Polarion project."""
    try:
        result = await _handle_get_test_runs(params.model_dump(), settings)
        return {"content": [{"type": item.type, "text": item.text} for item in result]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/get_test_run")
async def get_test_run(params: TestRunParams):
    """Get a specific test run from a Polarion project."""
    try:
        result = await _handle_get_test_run(params.model_dump(), settings)
        return {"content": [{"type": item.type, "text": item.text} for item in result]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/get_documents")
async def get_documents(params: DocumentsParams):
    """Get all documents from a Polarion project."""
    try:
        result = await _handle_get_documents(params.model_dump(), settings)
        return {"content": [{"type": item.type, "text": item.text} for item in result]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/get_test_specs_from_document")
async def get_test_specs_from_document(params: TestSpecsFromDocumentParams):
    """Get test specifications from a specific document in a Polarion project."""
    try:
        result = await _handle_get_test_specs_from_document(params.model_dump(), settings)
        return {"content": [{"type": item.type, "text": item.text} for item in result]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/discover_work_item_types")
async def discover_work_item_types(params: DiscoverTypesParams):
    """Discover what work item types exist in a Polarion project by sampling work items."""
    try:
        result = await _handle_discover_work_item_types(params.model_dump(), settings)
        return {"content": [{"type": item.type, "text": item.text} for item in result]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def server_health():
    """Server health check endpoint."""
    return {"status": "healthy", "service": "Polarion MCP HTTP API"}


@app.get("/tools")
async def list_tools():
    """List all available tools."""
    return {
        "tools": [
            {
                "name": "health_check",
                "description": "Check the health of the Polarion connection",
                "endpoint": "/tools/health_check",
            },
            {
                "name": "get_project_info",
                "description": "Get information about a Polarion project",
                "endpoint": "/tools/get_project_info",
            },
            {
                "name": "get_workitem",
                "description": "Get a specific work item from a Polarion project",
                "endpoint": "/tools/get_workitem",
            },
            {
                "name": "search_workitems",
                "description": "Search for work items in a Polarion project using Lucene query syntax",
                "endpoint": "/tools/search_workitems",
            },
            {
                "name": "get_test_runs",
                "description": "Get all test runs from a Polarion project",
                "endpoint": "/tools/get_test_runs",
            },
            {
                "name": "get_test_run",
                "description": "Get a specific test run from a Polarion project",
                "endpoint": "/tools/get_test_run",
            },
            {
                "name": "get_documents",
                "description": "Get all documents from a Polarion project",
                "endpoint": "/tools/get_documents",
            },
            {
                "name": "get_test_specs_from_document",
                "description": "Get test specifications from a specific document in a Polarion project",
                "endpoint": "/tools/get_test_specs_from_document",
            },
            {
                "name": "discover_work_item_types",
                "description": "Discover what work item types exist in a Polarion project by sampling work items",
                "endpoint": "/tools/discover_work_item_types",
            },
        ]
    }


def main():
    """Main entry point for the HTTP server."""
    parser = argparse.ArgumentParser(description="Polarion MCP HTTP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--https", action="store_true", help="Enable HTTPS")
    parser.add_argument("--cert", help="SSL certificate file (for HTTPS)")
    parser.add_argument("--key", help="SSL private key file (for HTTPS)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    # SSL configuration
    ssl_config = None
    if args.https:
        if not args.cert or not args.key:
            print("HTTPS requires both --cert and --key arguments")
            exit(1)
        
        ssl_config = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_config.load_cert_chain(args.cert, args.key)

    protocol = "https" if args.https else "http"
    print(f"Starting Polarion MCP HTTP Server on {protocol}://{args.host}:{args.port}")
    print(f"API documentation available at {protocol}://{args.host}:{args.port}/docs")
    print(f"OpenAPI specification available at {protocol}://{args.host}:{args.port}/openapi.json")

    # Run the server
    uvicorn.run(
        "mcp_server.http_server:app",
        host=args.host,
        port=args.port,
        ssl_certfile=args.cert if args.https else None,
        ssl_keyfile=args.key if args.https else None,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()