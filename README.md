# Polarion MCP Server

A Model Context Protocol (MCP) server that provides seamless integration between Polarion ALM and AI assistants like Microsoft Copilot Studio and Cline. Built with FastMCP 2.10.6, this server enables AI agents to interact with Polarion projects, work items, test runs, documents, and more.

## Features

- **Full MCP Protocol Support**: Implements tools, resources, and prompts
- **Microsoft Copilot Studio Compatible**: Includes middleware for JSON-RPC ID type compatibility
- **9 Powerful Tools**: Comprehensive access to Polarion data
- **Secure Authentication**: Token-based authentication with Polarion
- **Production Ready**: Robust error handling and logging
- **Modern Python**: Uses `pyproject.toml` and follows best practices

## Prerequisites

- Python 3.10+
- Git
- Access to a Polarion instance with:
  - Polarion URL
  - Username
  - Personal access token
- Microsoft Copilot Studio account (for AI agent integration)

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/mmerah/PolarionMcp.git
   cd PolarionMcp
   ```

2. **Configure Polarion Credentials**
   
   Create a `.env` file in the project root:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your credentials:
   ```env
   POLARION_URL=https://your-polarion-instance.com/polarion
   POLARION_USER=your-username
   POLARION_TOKEN=your-personal-access-token
   ```

3. **Run the Server**
   
   Using the convenience script (recommended):
   ```bash
   chmod +x run_server.sh
   ./run_server.sh
   ```
   
   Or manually:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e .
   python -m mcp_server.main
   ```

   The server starts on `http://0.0.0.0:8000` with the MCP endpoint at `/mcp/`

## Available Tools

### 1. `health_check`
Checks the connection to the Polarion server.
- **Returns**: Connection status message

### 2. `get_project_info`
Retrieves information about a Polarion project.
- **Parameters**: 
  - `project_id`: The ID of the Polarion project
- **Returns**: Project name and description

### 3. `get_workitem`
Gets detailed information about a specific work item.
- **Parameters**:
  - `project_id`: The ID of the Polarion project
  - `workitem_id`: The ID of the work item (e.g., "PROJ-123")
- **Returns**: Work item details including title, type, status, author, dates

### 4. `search_workitems`
Searches for work items using Lucene query syntax.
- **Parameters**:
  - `project_id`: The ID of the Polarion project
  - `query`: Lucene query string (e.g., "status:open AND type:requirement")
  - `field_list`: Optional comma-separated list of fields to return
- **Returns**: List of matching work items

### 5. `get_test_runs`
Retrieves all test runs in a project.
- **Parameters**:
  - `project_id`: The ID of the Polarion project
- **Returns**: List of test runs with ID, title, and status

### 6. `get_test_run`
Gets details of a specific test run.
- **Parameters**:
  - `project_id`: The ID of the Polarion project
  - `test_run_id`: The ID of the test run
- **Returns**: Test run details including status, dates, and test case count

### 7. `get_documents`
Lists all documents in a project.
- **Parameters**:
  - `project_id`: The ID of the Polarion project
- **Returns**: List of documents with ID, title, and location

### 8. `get_test_specs_from_document`
Extracts test specification IDs from a document.
- **Parameters**:
  - `project_id`: The ID of the Polarion project
  - `document_id`: The ID of the document
- **Returns**: List of test specification IDs found in the document

### 9. `discover_work_item_types`
Discovers available work item types in a project.
- **Parameters**:
  - `project_id`: The ID of the Polarion project
  - `limit`: Maximum number of work items to sample (default: 20)
- **Returns**: List of work item types with occurrence counts

## MCP Resources

- **`polarion://project/{project_id}`**: Access project information as a resource

## MCP Prompts

- **`analyze_project`**: Generate analysis prompt for a project
- **`workitem_analysis`**: Generate analysis prompt for a specific work item

## Microsoft Copilot Studio Integration

### Public URL Configuration

For the server to be accessible by Microsoft Copilot Studio, you need a public URL:

- **Development**: Use VSCode port forwarding with Public visibility
- **Production**: Deploy to a cloud service like Azure

The server endpoint will be at: `https://your-public-url/mcp/`

### Integration Steps

1. **Ensure Server is Running**
   The server must be accessible at the public URL above.

2. **OpenAPI Specification**
   The `openapi.yaml` file is pre-configured with:
   - Correct host URL
   - MCP protocol specification: `x-ms-agentic-protocol: mcp-streamable-1.0`
   - Proper endpoint configuration

3. **Add to Copilot Studio**
   For detailed instructions on adding MCP servers to Microsoft Copilot Studio, refer to the official Microsoft documentation:
   https://github.com/microsoft/mcsmcp/blob/main/README.md

4. **Test Your Integration**
   Example prompts for Copilot Studio:
   - "Check the health of the Polarion connection"
   - "Get information about the MyProject project"
   - "Search for open defects in the WebApp project"
   - "Show me test runs in the QA project"
   - "Find all requirements assigned to john.doe in the Development project"

## Using with Cline

This server can also be used with [Cline](https://github.com/cline/cline) (VSCode extension) by running it in SSE transport mode:

1. **Run the Cline-compatible server**
   ```bash
   ./run_server_cline.sh
   ```
   This starts the server with SSE transport on `http://localhost:8000/mcp`

2. **Configure Cline**
   - Open VSCode with Cline extension
   - Click Cline icon → Menu (⋮) → MCP Servers
   - Go to "Remote Servers" tab
   - Add server with:
     - Name: `polarion`
     - URL: `http://localhost:8000/mcp`
   
   Or edit `cline_mcp_settings.json`:
   ```json
   {
       "mcpServers": {
           "polarion": {
               "url": "http://localhost:8000/mcp",
               "disabled": false,
               "autoApprove": ["health_check", "get_project_info"]
           }
       }
   }
   ```

3. **Use with Cline**
   - Ask Cline to interact with Polarion:
     - "Check my Polarion connection"
     - "Search for open bugs in project XYZ"
     - "Get test run results from Polarion"
     - "Show me all requirements in project ABC"

## Project Structure

```
PolarionMcp/
├── mcp_server/          # MCP server implementation
│   ├── __init__.py
│   ├── main.py         # Server entry point
│   ├── tools.py        # MCP tool definitions
│   ├── middleware.py   # Copilot Studio compatibility layer
│   └── settings.py     # Configuration management
├── lib/                 # Core libraries
│   └── polarion/
│       └── polarion_driver.py  # Polarion API wrapper
├── openapi.yaml        # OpenAPI specification for Copilot Studio
├── run_server.sh       # Convenience startup script
├── pyproject.toml      # Python package configuration
├── .env.example        # Environment variables template
└── README.md           # This file
```

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black mcp_server lib
isort mcp_server lib
```

### Type Checking
```bash
mypy mcp_server lib
```

## Troubleshooting

### Connection Issues
- Verify your Polarion URL is correct and accessible (notably use '/mcp/' and not '/mcp')
- Ensure your personal access token has sufficient permissions
- Check that the `.env` file is properly configured

### Copilot Studio Integration
- Confirm your public URL is accessible
- Verify the server is running on port 8000
- Check server logs for any middleware-related errors
- Consult the official Microsoft MCP documentation: https://github.com/microsoft/mcsmcp

### Common Errors
- "Invalid credentials": Check your username and token
- "Project not found": Verify the project ID exists in Polarion
- "Work item not found": Ensure the work item ID includes the project prefix

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
