# Polarion MCP Server

A Model Context Protocol server for providing read-only access to Polarion ALM. This server enables LLMs to retrieve and analyze test data, work items, and project information from Polarion instances.

## Installation

### Using pip

```bash
pip install mcp-polarion
```


## Configuration

### Environment Variables

The MCP server requires three environment variables for Polarion authentication. You have two options:

#### Option 1: Using .env file (Recommended)
Create a `.env` file in your working directory:

```env
POLARION_URL=https://your-polarion-instance.com/polarion
POLARION_USER=your-username
POLARION_TOKEN=your-access-token
```

#### Option 2: System Environment Variables
Set environment variables directly:

```bash
export POLARION_URL=https://your-polarion-instance.com/polarion
export POLARION_USER=your-username
export POLARION_TOKEN=your-access-token
```

### Configure for Claude

<details>
<summary>Using pip installation</summary>

```json
{
  "mcpServers": {
    "polarion": {
      "command": "mcp-polarion",
      "env": {
        "POLARION_URL": "https://your-polarion-instance.com/polarion",
        "POLARION_USER": "your-username",
        "POLARION_TOKEN": "your-access-token"
      }
    }
  }
}
```

Or if using a `.env` file, specify the working directory:

```json
{
  "mcpServers": {
    "polarion": {
      "command": "mcp-polarion",
      "cwd": "/path/to/directory/with/env/file"
    }
  }
}
```
</details>


### Configure for VS Code

<details>
<summary>Using pip installation</summary>

```json
{
  "mcp": {
    "servers": {
      "polarion": {
        "command": "mcp-polarion",
        "env": {
          "POLARION_URL": "https://your-polarion-instance.com/polarion",
          "POLARION_USER": "your-username",
          "POLARION_TOKEN": "your-access-token"
        }
      }
    }
  }
}
```

Or if using a `.env` file, specify the working directory:

```json
{
  "mcp": {
    "servers": {
      "polarion": {
        "command": "mcp-polarion",
        "cwd": "/path/to/directory/with/env/file"
      }
    }
  }
}
```
</details>

### Configure for Cline (Development)

For development setup with local repository, you have two options:

#### Option 1: Using Python module (Recommended)
```json
{
  "mcpServers": {
    "polarion": {
      "command": "/path/to/your/PolarionMcp/.venv/bin/python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/your/PolarionMcp"
    }
  }
}
```

#### Option 2: Using installed command (after `pip install -e .`)
```json
{
  "mcpServers": {
    "polarion": {
      "command": "/path/to/your/PolarionMcp/.venv/bin/mcp-polarion",
      "cwd": "/path/to/your/PolarionMcp"
    }
  }
}
```

## Available Tools

- `get_project_info` - Get information about a Polarion project
  - `project_id` (string, required): The ID of the Polarion project

- `get_workitem` - Get a specific work item from a Polarion project  
  - `project_id` (string, required): The ID of the Polarion project
  - `workitem_id` (string, required): The ID of the work item to retrieve

- `search_workitems` - Search for work items in a Polarion project using Lucene query syntax
  - `project_id` (string, required): The ID of the Polarion project
  - `query` (string, required): Lucene query string for searching work items
  - `field_list` (array, optional): Optional list of fields to return

- `get_test_runs` - Get all test runs from a Polarion project
  - `project_id` (string, required): The ID of the Polarion project

- `get_test_run` - Get a specific test run from a Polarion project
  - `project_id` (string, required): The ID of the Polarion project
  - `test_run_id` (string, required): The ID of the test run to retrieve

- `get_documents` - Get all documents from a Polarion project
  - `project_id` (string, required): The ID of the Polarion project

- `get_test_specs_from_document` - Get test specifications from a specific document in a Polarion project
  - `project_id` (string, required): The ID of the Polarion project
  - `document_id` (string, required): The ID of the document to get test specs from

- `health_check` - Check the health of the Polarion connection

- `discover_work_item_types` - Discover what work item types exist in a Polarion project by sampling work items
  - `project_id` (string, required): The ID of the Polarion project
  - `limit` (integer, optional): Maximum number of work items to sample (default: 20)

## Usage Examples

```
"Get project information for MyProject"
"Search for all requirements in MyProject"
"Find test runs with status 'passed' in MyProject"
"Get work item REQ-123 from MyProject"
```

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

## Microsoft Copilot Studio Integration

This MCP server can be integrated with Microsoft Copilot Studio through a FastAPI HTTP wrapper, enabling your Copilot agents to access Polarion data via HTTP REST endpoints.

### Quick Setup

1. **Install HTTP server dependencies**:
   ```bash
   # Option 1: Install specific dependencies
   pip install fastapi uvicorn[standard]
   
   # Option 2: Install with HTTP extras
   pip install -e ".[http]"
   ```

2. **Start HTTP Server**:
   ```bash
   # Development (HTTP)
   python -m mcp_server.http_server
   
   # Or using the installed command
   mcp-polarion-http
   ```

3. **HTTPS setup for development**:
   ```bash
   # Generate SSL certificates
   ./scripts/generate_certs.sh
   
   # Start with HTTPS
   python -m mcp_server.http_server --https --cert certs/cert.pem --key certs/key.pem
   ```

4. **Generate OpenAPI specification**:
   ```bash
   python scripts/generate_openapi.py
   ```

### Available REST Endpoints

- `POST /tools/health_check` - Check Polarion connection health
- `POST /tools/get_project_info` - Get project information
- `POST /tools/search_workitems` - Search work items
- `POST /tools/get_test_runs` - Get test runs
- `POST /tools/discover_work_item_types` - Discover work item types
- `GET /openapi.json` - OpenAPI specification for Copilot Studio

### Microsoft Copilot Studio Configuration

1. **Import OpenAPI Specification**:
   - Generate specification: `python scripts/generate_openapi.py`
   - Use the generated `openapi.json` file
   - Import as custom connector in Copilot Studio
   - Set base URL to your HTTPS server endpoint

2. **Required Settings**:
   - **Authentication**: Configure as needed for your environment
   - **HTTPS**: Microsoft Copilot Studio requires HTTPS endpoints
   - **CORS**: Enabled by default in the HTTP server

3. **Example Agent Prompts**:
   ```
   "Get project information for MyProject"
   "Search for open requirements in MyProject"  
   "Find all test runs with status failed"
   "Discover what work item types exist in MyProject"
   "Get work item REQ-123 details"
   "List all documents in MyProject"
   ```

## Development

### Running Tests

Install development dependencies and run tests:

```bash
pip install -e ".[dev]"
pytest
```

## Security Notes

- This server provides read-only access to Polarion data
- Ensure your Polarion access token has minimal required permissions
- Deploy in secure environments and networks
- Review data exposure before deploying to production
- Consider using environment-specific configuration

## Troubleshooting

### Connection Issues

1. Verify your `POLARION_URL` is correct and accessible
2. Check that your `POLARION_USER` and `POLARION_TOKEN` are valid
3. Ensure your Polarion instance supports the required API endpoints
4. Test connectivity using the `health_check` tool

### Test Run Queries

The `get_test_runs` tool searches for work items with type `verificationTest`, which is the standard type for test cases/test runs in many Polarion instances. If your Polarion instance uses a different type name for test runs, you can:

1. Use the `discover_work_item_types` tool to find all available types in your project
2. Use the `search_workitems` tool with a custom query like `type:your-test-type`
3. Contact your Polarion administrator for the appropriate type name

## License

This project is licensed under the MIT License. See the LICENSE file for details.