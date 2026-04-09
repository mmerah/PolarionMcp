# mcp-polarion

A CLI-first Polarion ALM client with MCP server support for AI assistants (Cline, Claude Code, Copilot Studio) and OpenAI GPT Actions.

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
mcp-polarion projects                               # list all configured aliases
mcp-polarion project           -p myproject         # name & description
mcp-polarion project-types     -p myproject         # configured work item types + fields
mcp-polarion named-queries     -p myproject         # named queries defined in config
mcp-polarion discover-types    -p myproject         # sample the project to find types
mcp-polarion discover-types    -p myproject --limit 500

# Work items
mcp-polarion get ADC-1234                           # project inferred from ID prefix
mcp-polarion get ADC-1234       -p myproject
mcp-polarion search "type:defect AND status:open"  -p myproject
mcp-polarion search "query:open_bugs"              -p myproject   # named query
mcp-polarion search "type:defect"  -p myproject --fields "id,title,status,customFields.severity"

# Tests & documents
mcp-polarion test-runs          -p myproject
mcp-polarion test-run  TR-42    -p myproject
mcp-polarion documents          -p myproject
mcp-polarion test-specs QA/TestSpecs  -p myproject

# Plans (plan projects only)
mcp-polarion plans              -p releases
mcp-polarion plan      R2024.4  -p releases
mcp-polarion plan-workitems R2024.4  -p releases
mcp-polarion search-plans "templateId:release"  -p releases

# Servers
mcp-polarion serve                          # HTTP — works for all clients
mcp-polarion serve --mode stdio             # stdio transport (.mcp.json)
mcp-polarion serve --port 9000 --log-level DEBUG

# Utilities
mcp-polarion docgen                         # regenerate agent_instructions.md
mcp-polarion generate-openapi               # regenerate openapi.yaml
```

The convenience script `run_server.sh` handles first-time venv setup and `.env` checks before calling `mcp-polarion serve`.

## Configuration

The optional `polarion_config.yaml` unlocks project aliases, named queries, custom field mappings, and plan project support. Copy the example to get started:

```bash
cp polarion_config.example.yaml polarion_config.yaml
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

After editing the config, regenerate the agent instructions:
```bash
mcp-polarion docgen
```

See [XML_PARSER.md](XML_PARSER.md) for importing custom field definitions from Polarion XML exports.

## Available Tools

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
| `get_workitem` | Full details for a single work item, including custom fields |
| `search_workitems` | Lucene query search; accepts named queries (`query:open_bugs`) and optional `field_list` |

### Test & Documents
| Tool | Description |
|------|-------------|
| `get_test_runs` | List all test runs |
| `get_test_run` | Details of one test run |
| `get_documents` | List documents in a project |
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

A single `mcp-polarion serve` command serves all HTTP clients. The server uses stateless requests (one session per POST) and JSON responses, which enables parallel tool calls and works equally well with Cline, Claude Code, Copilot Studio, and GPT Actions.

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

### GPT Actions (OpenAI)

```bash
mcp-polarion serve
```

REST endpoints are available at `/actions/` alongside the MCP endpoint. The OpenAPI spec at `/openapi.json` (or regenerate with `mcp-polarion generate-openapi`) describes all routes.

```bash
curl http://localhost:8000/actions/projects
curl http://localhost:8000/openapi.json | jq '.paths | keys'
```

Use `agent_instructions.md` as a knowledge file and `agent_instructions_simple.md` as the system prompt for your custom GPT.

## Project Structure

```
polarion_mcp/
  core/           Polarion domain logic — client, config, settings, formatters
  mcp/            MCP layer — tool definitions, middleware, server factory, stdio
  gpt_actions/    GPT Actions REST routes and OpenAPI spec generation
  docgen/         Agent instruction doc generator
  cli/            CLI entry point (mcp-polarion)
tests/
scripts/
  parse_custom_fields.py   Import custom fields from Polarion XML exports
run_server.sh              First-time bootstrapper (venv + deps + serve)
polarion_config.example.yaml
```

## Development

```bash
pytest                      # run tests
black polarion_mcp tests
isort polarion_mcp tests
mypy polarion_mcp
```

## License

MIT — see [LICENSE](LICENSE).