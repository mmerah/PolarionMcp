# MCP Server for Polarion

Model Context Protocol (MCP) server with HTTPS and OpenAPI support for Polarion integration. Provides both MCP Streamable HTTP transport and traditional REST API endpoints. Compatible with Microsoft Copilot, Claude Desktop, Cline, and other AI assistants.

## Features

- **MCP Streamable HTTP**: Microsoft Copilot compatible MCP transport
- **HTTPS Support**: Production-ready SSL/TLS with certificate management  
- **OpenAPI Schema**: Auto-generated OpenAPI/Swagger documentation
- **Dual Protocol Support**: Both MCP and traditional REST endpoints
- **Read-Only Access**: Secure, read-only operations on Polarion data
- **AI Assistant Integration**: Works with Microsoft Copilot, Claude Desktop, Cline, and more
- **Comprehensive Polarion Access**: Work items, test runs, documents, and more
- **Production Ready**: Comprehensive error handling and health checks

## Quick Start

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### 2. Configuration

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your Polarion credentials:

```env
POLARION_USER=your-username@company.com
POLARION_TOKEN=your-polarion-token-here
POLARION_URL=https://your-polarion-instance.com/polarion
```

### 3. SSL Certificates (for HTTPS)

Generate self-signed certificates for development:

```bash
bash scripts/bash/generate_certs.sh
```

### 4. Start the Server

```bash
# HTTPS (production) - Required for Microsoft Copilot
uvicorn mcp_server.main:app --host 0.0.0.0 --port 8443 --ssl-keyfile mcp_server/certs/key.pem --ssl-certfile mcp_server/certs/cert.pem

# HTTP (development only)
uvicorn mcp_server.main:app --host 0.0.0.0 --port 8000
```

### 5. Test the Server

```bash
# Test health endpoint
curl -k https://localhost:8443/health

# Get OpenAPI schema for Microsoft Copilot
curl -k https://localhost:8443/mcp/schema

# Test MCP endpoint
curl -k -X POST https://localhost:8443/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": "1", "method": "initialize", "params": {}}'

# View interactive docs
# Visit: https://localhost:8443/docs
```

## MCP Tools

The MCP server provides these tools for AI assistants:

### Project Operations
- `get_project_info(project_id)` - Get project information
- `health_check()` - Check Polarion connection health

### Work Items
- `get_workitem(project_id, workitem_id)` - Get specific work item
- `search_workitems(project_id, query, field_list?)` - Search work items with Lucene queries

### Test Management
- `get_test_runs(project_id)` - List all test runs
- `get_test_run(project_id, test_run_id)` - Get specific test run
- `get_test_specs_from_document(project_id, document_id)` - Get test specs from document

### Documents
- `get_documents(project_id)` - List all documents in project

### MCP Resources
- `polarion://project/{project_id}/info` - Project information
- `polarion://project/{project_id}/workitem/{workitem_id}` - Work item details

## API Endpoints

### Core Endpoints
- `GET /` - Server information
- `GET /health` - Health check and configuration validation
- `GET /docs` - Interactive API documentation

### MCP Endpoints
- `POST /mcp` - MCP Streamable HTTP transport endpoint
- `GET /mcp/schema` - OpenAPI schema for Microsoft Copilot integration

### Polarion Data Access
- `GET /polarion/projects/{project_id}/info` - Project information
- `GET /polarion/projects/{project_id}/workitems/{workitem_id}` - Get specific work item
- `GET /polarion/projects/{project_id}/workitems?query=...` - Search work items
- `GET /polarion/projects/{project_id}/testruns` - List test runs
- `GET /polarion/projects/{project_id}/testruns/{testrun_id}` - Get specific test run
- `GET /polarion/projects/{project_id}/documents` - List documents

## AI Assistant Integration

### Microsoft Copilot Studio

1. **Get the OpenAPI schema**:
   ```bash
   curl -k https://your-server.com:8443/mcp/schema > polarion-mcp-schema.json
   ```

2. **Configure in Copilot Studio**:
   - Use the schema file from step 1
   - Set endpoint URL: `https://your-server.com:8443/mcp`
   - Ensure HTTPS is enabled
   - Add authentication headers if needed

### Claude Desktop

For Claude Desktop, configure it to use the HTTP MCP endpoint:

```json
{
  "mcpServers": {
    "polarion": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch", "https://your-server.com:8443/mcp"]
    }
  }
}
```

### Other MCP Clients

For HTTP-based MCP clients, use:
- **Endpoint**: `https://your-server.com:8443/mcp`
- **Protocol**: MCP Streamable HTTP v1.0
- **Transport**: HTTPS with proper SSL certificates

## Usage Examples

Once configured, you can ask your AI assistant:

```
"Get project information for MyProject"
"Search for all requirements in MyProject"
"Find test runs with status 'passed' in MyProject"
"Get work item REQ-123 from MyProject"
"List all documents in MyProject"
```

## Query Examples

### Lucene Query Examples for Work Items

```
# Search by type
"type:requirement"
"type:testcase"

# Search by status  
"status:open"
"status:closed"

# Search by text
"title:authentication"
"description:*login*"

# Combined searches
"type:requirement AND status:open"
"type:testcase AND title:*integration*"
```

## Configuration Reference

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `POLARION_URL` | Polarion server URL | `https://polarion.company.com/polarion` |
| `POLARION_USER` | Polarion username | `user@company.com` |
| `POLARION_TOKEN` | Polarion access token | `eyJhbGciOiJ...` |

### Optional Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_SERVER_API_KEY` | API key for REST endpoints | None |
| `SERVER_HOST` | Server bind address | `0.0.0.0` |
| `SERVER_PORT` | Server port | `8443` |
| `SSL_KEYFILE` | SSL private key path | `mcp_server/certs/key.pem` |
| `SSL_CERTFILE` | SSL certificate path | `mcp_server/certs/cert.pem` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Health Check

Test your configuration:

```bash
# Test HTTPS health endpoint
curl -k https://localhost:8443/health

# Test MCP endpoint
curl -k -X POST https://localhost:8443/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": "1", "method": "initialize", "params": {}}'

# Expected output for healthy connection:
# {"jsonrpc": "2.0", "id": "1", "result": {"protocolVersion": "2024-11-05", ...}}
```

## Troubleshooting

### Connection Issues

1. **Check environment variables**:
   ```bash
   curl -k https://localhost:8443/health
   ```

2. **Verify Polarion access**:
   - Ensure your Polarion token is valid
   - Check network connectivity to Polarion instance
   - Verify your user has appropriate permissions

3. **Check server logs**:
   - Server outputs logs to stdout when running with uvicorn
   - Look for connection errors or authentication issues

### Common Error Messages

- `"POLARION_URL environment variable is required"` - Set your Polarion URL
- `"Invalid credentials"` - Check your username and token
- `"Invalid polarion URL"` - Verify the Polarion instance URL
- `"Work item not found"` - Check the work item ID exists in the project

## Project Structure

```
├── lib/polarion/           # Polarion driver (read-only methods)
├── mcp_server/            # FastAPI application with MCP support
│   ├── routers/           # API route handlers
│   │   ├── polarion.py    # Polarion REST endpoints
│   │   └── mcp_endpoint.py # MCP Streamable HTTP endpoint
│   ├── auth.py           # Authentication logic
│   ├── config.py         # Configuration management
│   ├── models.py         # Pydantic models
│   └── main.py           # Application entry point
├── scripts/              # Utility scripts
├── .env.example         # Environment template
├── pyproject.toml       # Project configuration
└── README.md            # This file
```

## Development

### Install Development Tools

```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Code Quality Tools

```bash
# Format code
black .
isort .

# Lint code
flake8 .

# Type checking
mypy .

# Run tests
pytest
```

### Adding New Tools

To add new MCP tools, edit `mcp_polarion.py`:

```python
@mcp.tool()
def your_new_tool(project_id: str, param: str) -> Dict[str, Any]:
    """
    Description of your tool.
    
    Args:
        project_id: The Polarion project ID
        param: Your parameter
        
    Returns:
        Result dictionary
    """
    try:
        with PolarionConnection(project_id) as conn:
            # Your implementation
            pass
    except Exception as e:
        logger.error(f"Error in your_new_tool: {e}")
        raise McpError(f"Failed to execute tool: {str(e)}")
```

## Contributing

1. Install pre-commit hooks to ensure code quality
2. Follow existing code style (enforced by black/isort)
3. Add type hints (checked by mypy)
4. Write tests for new functionality
5. Update documentation for new features

## License

Open source - suitable for enterprise use.

## Support

- Check `health_check()` function for configuration issues
- Review server logs for detailed error information
- Ensure Polarion credentials and URL are correct
- Verify network connectivity to Polarion instance