# Polarion MCP Tool Workflows

## Tool Selection Matrix

| Query Type | First Tool | Follow-up Tools |
|------------|------------|-----------------|
| "What projects?" | `list_projects` | `get_project_info` |
| "Find bugs/requirements" | `list_projects` → `search_workitems` | `get_workitem` for details |
| "Specific item PROJ-123" | `get_workitem` | - |
| "Unknown project" | `list_projects` or ask user | - |
| "Test results" | `get_test_runs` | `get_test_run` |
| "Release/Sprint items" | Check `is_plan` → `get_plan_workitems` | - |
| "What queries available?" | `get_named_queries` | `search_workitems` with query:name |

## Core Workflow: General Queries

```
START → Parse query for project hints
↓
Has project ID/alias? 
  YES → list_projects (verify exists)
  NO → list_projects → ask user to select
↓
Is configured project?
  YES → get_project_types (get types + custom fields)
  NO → discover_work_item_types (sample 1000 items)
↓
Identify relevant work item type from query
↓
search_workitems with type filter
↓
Need details? → get_workitem on best matches
```

## Core Workflow: Plan Projects

```
Is plan project? (check is_plan flag)
  NO → Use standard workflow
  YES ↓
      What's needed?
        - List plans → get_plans
        - Specific plan → get_plan("plan-id")
        - Items in plan → get_plan_workitems("plan-id")
        - Search plans → search_plans("query")
```

## Search Patterns

**IMPORTANT**: Be precise - the more specific your query, the better the results. Combine multiple conditions to narrow scope.

### Query Construction
```yaml
# Basic patterns (combine for precision)
type:defect AND status:open AND priority:high  # Specific > broad
type:requirement AND title:OAuth* AND NOT status:done
assignee.id:john.doe AND status:in_progress AND dueDate:[* TO $today + 7d$]

# Custom fields (search BY, not retrieve)
severity:critical AND status:open  # More precise than just severity:critical
type:defect AND HAS_VALUE:severity AND NOT status:closed
NOT HAS_VALUE:description AND type:requirement

# Date ranges (combine with other filters)
created:[$today - 7d$ TO $today$] AND type:defect
dueDate:[* TO $today$] AND assignee.id:$current_user  # My overdue items

# Hierarchical
parent.id:PROJ-100 AND status:open  # Open children only
NOT HAS_VALUE:parent AND type:feature  # Top-level features
```

### Named Queries
```yaml
get_named_queries("proj")  # List available named queries
search_workitems("proj", "query:open_bugs")
# Expands to configured: "type:defect AND status:open"
```

## Critical Limitations

### Custom Fields in Search
```yaml
❌ CANNOT retrieve custom field values in search:
search_workitems("proj", "type:defect", "id,title,severity")
# severity will NOT be returned

✅ Workaround - Two-step process:
1. search_workitems("proj", "severity:critical", "id,title")
2. get_workitem("proj", "PROJ-123")  # Gets ALL fields
```

### Plan vs Regular Projects
```yaml
Plan projects (is_plan: true):
  ❌ search_workitems - Not supported
  ❌ get_workitem - Not supported  
  ✅ get_plan_workitems - Use this instead
  ✅ search_plans - Search plans themselves

Regular projects:
  ✅ search_workitems - Full Lucene queries
  ✅ get_workitem - Individual item details
  ❌ get_plans - Not applicable
```

## Quick Recipes

### Morning Status Check
```yaml
health_check()
list_projects()  # See what's available
search_workitems("dev", "query:my_items")
search_workitems("dev", "created:[$today$ TO $today$]")
```

### Bug Triage
```yaml
search_workitems("web", "type:defect AND priority:critical AND status:open", "id,title,status")
# For each critical bug:
get_workitem("web", "WEB-123")  # Full details with custom fields
```

### Sprint Planning (Plan Project)
```yaml
get_plans("releases")  # List all plans
search_plans("releases", "templateId:iteration")  # Find sprints
get_plan_workitems("releases", "Sprint23")  # Items in sprint
```

### Test Management
```yaml
get_test_runs("qa")  # Recent runs
get_test_run("qa", "QA-RUN-2024")  # Specific run details
get_documents("qa")  # Find test docs
get_test_specs_from_document("qa", "Testing/Regression")
```

## Decision Trees

### Project Unknown
```
Query has project hint? → extract it
↓ NO
list_projects() → show aliases
↓
Multiple matches? → ask user
Single match? → use it
No matches? → ask for project ID
```

### Type Discovery
```
Project configured? → get_project_types()
↓ NO
discover_work_item_types(limit=1000)
↓
Match query terms to types:
  "bugs" → defect, bug
  "requirements" → requirement, specification
  "tests" → testcase, testspec
```

### Field Resolution
```
Need custom fields?
↓ YES
Can't get in search → use get_workitem
↓
search_workitems (filter by custom field)
↓
get_workitem (retrieve custom field values)
```

## Lucene Rules
- Operators: UPPERCASE (AND, OR, NOT)
- Whitespace = OR: "term1 term2" → "term1 OR term2"
- No leading wildcards: ❌ "*auth" ✅ "auth*"
- Field IDs not names: "assignee.id" not "assignee"
- Parentheses for complex: "(A OR B) AND C"

## Performance Tips
```yaml
DO:
- Be specific: "type:defect AND status:open AND priority:high"
- Use configured queries: "query:open_bugs"
- Limit fields: "id,title,status"
- Filter at source: combine multiple conditions
- Add type filter: always include type: to narrow results

DON'T:
- Use broad queries: just "status:open" (too many results)
- Fetch all: "NOT type:null"
- Expect custom fields in search results
- Repeatedly discover types (use config)
```

## Error Patterns
| Error | Cause | Fix |
|-------|-------|-----|
| "Project not found" | Wrong ID/alias | Use list_projects() |
| "Work item not found" | Missing prefix | Include project: "PROJ-123" |
| "ClassCastException" | Custom field issue | Don't request custom fields in search |
| "❌" prefix | Permission/syntax | Check access rights, query syntax |

## Configuration Benefits
| Without Config | With Config |
|----------------|-------------|
| discover_work_item_types() every time | Instant type list |
| Complex Lucene queries | query:open_bugs |
| Unknown custom fields | Pre-defined per type |
| Raw project IDs | Friendly aliases |

## Tool Response Formats
- Success: Human-readable with data
- Error: "❌ [error message]"
- Lists: First 20-50 items + "...and X more"
- Empty: "No items found..."