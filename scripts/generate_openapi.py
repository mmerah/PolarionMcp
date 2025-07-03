#!/usr/bin/env python3
"""Generate OpenAPI specification for Microsoft Copilot Studio integration."""

import json
import sys
from pathlib import Path

# Add parent directory to path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.openapi.utils import get_openapi
from mcp_server.http_server import app


def generate_openapi_spec():
    """Generate OpenAPI specification with Microsoft Copilot Studio enhancements."""
    
    # Generate base OpenAPI spec
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add Microsoft Copilot Studio specific metadata
    for path, path_item in openapi_schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method == "post" and path.startswith("/tools/"):
                # Add Microsoft-specific metadata for MCP tools
                operation["x-ms-agentic-protocol"] = "mcp"
                operation["x-ms-visibility"] = "important"
    
    # Add additional metadata for Microsoft Copilot Studio
    openapi_schema["info"]["contact"] = {
        "name": "Polarion MCP Server",
        "url": "https://github.com/mmerah/PolarionMcp"
    }
    
    # Set servers to HTTPS for production use
    openapi_schema["servers"] = [
        {
            "url": "https://localhost:8000",
            "description": "Local HTTPS server (recommended for production)"
        },
        {
            "url": "http://localhost:8000", 
            "description": "Local HTTP server (development only)"
        }
    ]

    return openapi_schema


def main():
    """Main function to generate and save OpenAPI specification."""
    spec = generate_openapi_spec()
    
    # Save to file
    output_file = Path(__file__).parent.parent / "openapi.json"
    with open(output_file, "w") as f:
        json.dump(spec, f, indent=2)
    
    print(f"OpenAPI specification generated: {output_file}")
    print("Ready for Microsoft Copilot Studio import")
    print("Use this file to create a custom connector in Copilot Studio")


if __name__ == "__main__":
    main()