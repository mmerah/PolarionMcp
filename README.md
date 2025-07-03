# Polarion MCP Server

MCP (Model Context Protocol) server for Polarion integration. Provides AI assistants with read-only access to Polarion ALM data via both MCP and REST APIs.

## Features

- **MCP Streamable HTTP**: Microsoft Copilot compatible transport
- **HTTPS Support**: SSL/TLS with certificate management  
- **Dual Protocol**: Both MCP and traditional REST endpoints
- **Read-Only Security**: Secure, read-only operations on Polarion data
- **AI Assistant Ready**: Works with Microsoft Copilot, Claude Desktop, Cline, and more
- **Production Grade**: Comprehensive error handling and health checks

## Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
```

### 2. Configure Polarion Access

Edit `.env` with your Polarion credentials:

```env
POLARION_USER=your-username@company.com
POLARION_TOKEN=your-polarion-token-here
POLARION_URL=https://your-polarion-instance.com/polarion
```

### 3. Generate SSL Certificates

```bash
bash scripts/bash/generate_certs.sh
```

### 4. Start Server

```bash
# HTTPS (production) - Required for Microsoft Copilot
uvicorn mcp_server.main:app --host 0.0.0.0 --port 8443 --ssl-keyfile mcp_server/certs/key.pem --ssl-certfile mcp_server/certs/cert.pem

# HTTP (development only)
uvicorn mcp_server.main:app --host 0.0.0.0 --port 8000
```

### 5. Test Installation

```bash
# Test health endpoint
curl -k https://localhost:8443/health

# Test MCP endpoint
curl -k -X POST https://localhost:8443/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": "1", "method": "initialize", "params": {}}'
```

## MCP Tools

The server provides 8 MCP tools for AI assistants:

- **`get_project_info(project_id)`** - Get project information
- **`get_workitem(project_id, workitem_id)`** - Get specific work item
- **`search_workitems(project_id, query, field_list?)`** - Search work items with Lucene queries
- **`get_test_runs(project_id)`** - List all test runs
- **`get_test_run(project_id, test_run_id)`** - Get specific test run
- **`get_documents(project_id)`** - List all documents in project
- **`get_test_specs_from_document(project_id, document_id)`** - Get test specs from document
- **`health_check()`** - Check Polarion connection health

## AI Assistant Integration

### Microsoft Copilot Studio

1. **Get OpenAPI schema**: `curl -k https://your-server.com:8443/mcp/schema > polarion-mcp-schema.json`
2. **Configure in Copilot Studio**:
   - Use the schema file from step 1
   - Set endpoint URL: `https://your-server.com:8443/mcp`
   - Ensure HTTPS is enabled

### Claude Desktop / Cline

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "polarion": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "node",
      "args": [
        "/path/to/mcp-http-client.js",
        "https://localhost:8443/mcp/"
      ],
      "env": {
        "NODE_TLS_REJECT_UNAUTHORIZED": "0"
      }
    }
  }
}
```

### Other MCP Clients

- **Endpoint**: `https://your-server.com:8443/mcp`
- **Protocol**: MCP Streamable HTTP v1.0
- **Transport**: HTTPS with proper SSL certificates

## Usage Examples

Ask your AI assistant:

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

## Configuration

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

## Development

### Install Development Tools

```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

### Code Quality Tools

```bash
# Format code
black . && isort .

# Lint code
flake8 .

# Type checking
mypy .

# Run tests
pytest
```

## Troubleshooting

### Connection Issues

1. **Check environment variables**: `curl -k https://localhost:8443/health`
2. **Verify Polarion access**: Ensure your Polarion token is valid
3. **Check server logs**: Server outputs logs to stdout when running with uvicorn

### Common Error Messages

- `"POLARION_URL environment variable is required"` - Set your Polarion URL
- `"Invalid credentials"` - Check your username and token
- `"Invalid polarion URL"` - Verify the Polarion instance URL
- `"Work item not found"` - Check the work item ID exists in the project

## Project Structure

```
├── lib/polarion/              # Polarion driver (read-only methods)
├── mcp_server/               # FastAPI application with MCP support
│   ├── routers/              # API route handlers
│   │   ├── polarion.py       # Polarion REST endpoints
│   │   └── mcp_endpoint.py   # MCP Streamable HTTP endpoint
│   ├── auth.py              # Authentication logic
│   ├── config.py            # Configuration management
│   ├── models.py            # Pydantic models
│   └── main.py              # Application entry point
├── mcp-http-client.js        # Demo MCP HTTP client
├── scripts/                  # Utility scripts
├── .env.example             # Environment template
├── pyproject.toml           # Project configuration
└── README.md               # This file
```
