# mcp-polarion

A CLI-first Polarion ALM client with MCP server support for AI assistants (Cline, Claude Code, Copilot Studio) and a REST API for OpenAI GPT Actions and other HTTP consumers.

## Installation

```bash
git clone https://github.com/mmerah/PolarionMcp.git
cd PolarionMcp
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

Create a `.env` file:
```env
POLARION_URL=https://your-polarion-instance.com/polarion
POLARION_USER=your-username
POLARION_TOKEN=your-personal-access-token
```

## CLI Usage

```bash
# Connection
mcp-polarion health

# Projects
mcp-polarion projects                       # list all configured aliases
mcp-polarion project -p myproject           # name & description
mcp-polarion project-types -p myproject     # configured work item types + fields
mcp-polarion named-queries -p myproject     # named queries defined in config
mcp-polarion discover-types -p myproject    # sample the project to find types
mcp-polarion discover-types -p myproject --limit 500

# Work items
mcp-polarion get ADC-1234                   # project inferred from ID prefix
mcp-polarion get ADC-1234 -p myproject
mcp-polarion search "type:defect AND status:open" -p myproject
mcp-polarion search "query:open_bugs" -p myproject  # named query
mcp-polarion search "type:defect" -p myproject --fields "id,title,status,customFields.severity"

# Tests & documents
mcp-polarion test-runs -p myproject
mcp-polarion test-run TR-42 -p myproject
mcp-polarion documents -p myproject
mcp-polarion test-specs QA/TestSpecs -p myproject

# Plans (plan projects only)
mcp-polarion plans -p releases
mcp-polarion plan R2024.4 -p releases
mcp-polarion plan-workitems R2024.4 -p releases
mcp-polarion search-plans "templateId:release" -p releases

# Servers
mcp-polarion serve                          # HTTP works for all clients
mcp-polarion serve --mode stdio             # stdio transport for local .mcp.json
mcp-polarion serve --port 9000 --log-level DEBUG

# Utilities. Output goes to generated/
mcp-polarion docgen                         # generated/agent_instructions*.md
mcp-polarion generate-openapi               # generated/openapi.yaml
mcp-polarion import-custom-fields --path local/custom-fields/myproject
```

The convenience script `run_server.sh` handles first-time venv setup and `.env` checks before calling `mcp-polarion serve`.

## Configuration

The optional local config unlocks project aliases, named queries, custom field mappings, and plan project support. The tracked example lives in `local/`. Copy it to get started:

```bash
cp local/polarion_config.example.yaml local/polarion_config.yaml
```

```yaml
projects:
  myproject:                          # alias (use this everywhere)
    id: ACTUAL_PROJECT_ID             # real Polarion project ID
    work_item_types:
      - systemRequirement
      - defect
    custom_fields:
      defect: [severity, foundIn]
      systemRequirement: [acceptanceCriteria, riskRelevance]
    default_queries:
      open_bugs: "type:defect AND status:open"
      my_items: "assignee.id:$current_user"

  releases:
    id: RELEASES_PROJECT
    is_plan: true                     # enables plan-specific tools

display_fields: [id, title, type, status, assignee]
```

After editing the config, regenerate the agent instructions and OpenAPI spec:
```bash
mcp-polarion docgen                         # generated/agent_instructions*.md
mcp-polarion generate-openapi               # generated/openapi.yaml
```

For custom field imports, keep downloaded XML exports local and untracked:

```text
local/custom-fields/<project-alias>/
  requirement-custom-fields.xml
  defect-custom-fields.xml
```

Usually, those custom-fields.yml are located in a Polarion project administration content. They can be downloaded from there. Then import them with:

```bash
mcp-polarion import-custom-fields --path local/custom-fields/myproject
```

See [docs/XML_PARSER.md](docs/XML_PARSER.md) for the full import workflow.

## Available Tools

See [docs/WORKFLOW_EXAMPLES.md](docs/WORKFLOW_EXAMPLES.md) for tool usage patterns.

### General
| Tool | Description |
|------|-------------|
| `health_check` | Check Polarion connectivity |
| `get_project_info` | Project name and description |
| `list_projects` | All configured project aliases |
| `get_project_types` | Configured work item types for a project |
| `get_named_queries` | Named queries defined for a project |
| `discover_work_item_types` | Sample a project to find its work item types |

### Work Items *(regular projects)*
| Tool | Description |
|------|-------------|
| `get_workitem` | Full details for one or more work items, including custom fields and test steps |
| `search_workitems` | Lucene query search; accepts named queries (`query:open_bugs`), optional `field_list`, and optional `limit` |

### Test & Documents
| Tool | Description |
|------|-------------|
| `get_test_runs` | List all test runs |
| `get_test_run` | Details of one test run |
| `get_documents` | List documents in a project, with optional `limit` and document paths |
| `get_document` | Export a document PDF to `/tmp` and return local path plus artifact download info |
| `get_test_specs_from_document` | Extract test spec IDs from a document |

### Plans *(plan projects only)*
| Tool | Description |
|------|-------------|
| `get_plans` | List all plans (releases, iterations) |
| `get_plan` | Details of one plan |
| `get_plan_workitems` | Work items in a plan |
| `search_plans` | Lucene search across plans |

**Inputs**: `project_alias` accepts both aliases (`myproject`) and real IDs (`ACTUAL_PROJECT_ID`).  
**Outputs**: Human-readable strings. Errors start with `❌`.

## MCP Server Integration

A single `mcp-polarion serve` command serves all HTTP clients. The server uses stateless requests (one session per POST) and JSON responses, which enables parallel tool calls and works equally well with Cline, Claude Code, Copilot Studio, and GPT Actions (via the REST API).

### Cline / Claude Code (HTTP)

```bash
mcp-polarion serve          # http://0.0.0.0:8000/mcp
```

Add to Cline's MCP settings:
```json
{
  "mcpServers": {
    "polarion": { "url": "http://localhost:8000/mcp" }
  }
}
```

### Claude Code / `.mcp.json` (stdio)

```json
{
  "mcpServers": {
    "polarion": {
      "command": "mcp-polarion",
      "args": ["serve", "--mode", "stdio"]
    }
  }
}
```

### Microsoft Copilot Studio

```bash
mcp-polarion serve
```

Expose over HTTPS (e.g. Azure Dev Tunnel), then follow the [MCP onboarding wizard](https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-add-existing-server-to-agent): **Add a tool → New tool → Model Context Protocol**. Use `https://<your-host>/mcp` as the server URL.

### REST API / GPT Actions (OpenAI)

```bash
mcp-polarion serve
```

REST endpoints are available at `/actions/` alongside the MCP endpoint. Generate the OpenAPI spec and agent instructions first:

```bash
mcp-polarion generate-openapi               # generated/openapi.yaml
mcp-polarion docgen                         # generated/agent_instructions*.md
```

The running server also serves the spec at `/openapi.json` and `/openapi.yaml`.

```bash
curl http://localhost:8000/actions/projects
curl http://localhost:8000/openapi.json | jq '.paths | keys'
```

Use `generated/agent_instructions.md` as a knowledge file and `generated/agent_instructions_simple.md` as the system prompt for your custom GPT.

## Project Structure

```
polarion_mcp/
  core/           Polarion domain logic: client, config, settings, formatters
  config/         Config discovery and XML import utilities
  mcp/            MCP layer: tool definitions, middleware, server, stdio
  rest_api/       REST API routes and OpenAPI spec generation
  docgen/         Agent instruction doc generator
  cli/            CLI entry point (mcp-polarion)
docs/             Supporting guides and workflow references
local/            Workspace-local config and XML exports
generated/        Generated files (openapi.yaml, agent_instructions)
tests/
run_server.sh              First-time bootstrapper (venv + deps + serve)
```

## Shell Completion

Basic tab completion for subcommands and flags is available via `argcomplete`. After reinstalling the package, enable it in your shell:

```bash
pip install -e .
eval "$(register-python-argcomplete mcp-polarion)"
```

For bash, add that line to `~/.bashrc`. For zsh, enable bash completion compatibility first, then register the same command.

## Development

```bash
pytest
black polarion_mcp tests
isort polarion_mcp tests
mypy polarion_mcp
```

## License

MIT. See [LICENSE](LICENSE).
