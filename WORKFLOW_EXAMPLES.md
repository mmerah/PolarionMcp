# Polarion MCP Workflow Examples

This guide shows how natural language requests translate into efficient tool usage patterns.

## Configuration Benefits

The configuration system dramatically simplifies workflows:

| Task | Without Config | With Config |
|------|---------------|------------|
| Find requirements | `discover_work_item_types()` → `search_workitems(..., "type:systemRequirement OR type:specification")` | `search_workitems("webstore", "query:requirements")` |
| Get open bugs | `search_workitems("WEBSTORE_V3", "type:defect AND status:open")` | `search_workitems("webstore", "query:open_bugs")` |
| List projects | Need to know all project IDs | `list_projects()` shows all aliases |

## Quick Command Reference

| User Intent | Tool(s) | Example |
|------------|---------|---------|
| "What projects exist?" | `list_projects` | Returns: `webstore → WEBSTORE_V3` |
| "Is Polarion working?" | `health_check` | Returns: `✅ Connection healthy` |
| "Show me project X" | `get_project_info("x")` | Uses alias automatically |
| "Find open bugs" | `search_workitems("x", "query:open_bugs")` | Uses named query |
| "What queries exist?" | `get_named_queries("x")` | Lists all configured queries |
| "Test run status" | `get_test_run("x", "run-id")` | Returns run details |
| "Test cases in doc" | `get_test_specs_from_document("x", "doc-id")` | Extracts test IDs |
| "What types exist?" | `get_project_types("x")` or `discover_work_item_types("x")` | Lists work item types |

## Plan Projects Support

### What are Plan Projects?
Some Polarion projects are organized around Plans (releases, iterations, sprints) rather than just work items. These projects need special handling to access plan-specific data.

### Configuring a Plan Project
```yaml
# In polarion_config.yaml
releases:
  id: RELEASES_PROJECT
  is_plan: true  # Mark as plan project
  work_item_types:
    - feature
    - userStory
    - defect
```

### Plan-Specific Tools
| Tool | Purpose | Example |
|------|---------|---------|
| `get_plans(project)` | List all plans | `get_plans("releases")` |
| `get_plan(project, id)` | Get plan details | `get_plan("releases", "R2024.4")` |
| `get_plan_workitems(project, id)` | Get items directly in plan | `get_plan_workitems("releases", "Sprint23")` |
| `search_plans(project, query)` | Search plans | `search_plans("releases", "templateId:release")` |

### Working with Plan Projects
For plan projects, use the plan-specific tools:

| Tool | Status | Alternative |
|------|--------|-------------|
| `search_workitems(project, query)` | ❌ Not supported | Use `get_plan_workitems()` |
| `get_workitem(project, id)` | ❌ Not supported | Use `get_plan_workitems()` |

### Plan Workflows
```yaml
# Workflow for plan projects
# 1. List all plans in the project
get_plans("releases")

# 2. Search for specific plans (e.g., releases, iterations)
search_plans("releases", "templateId:release")
search_plans("releases", "templateId:iteration")

# 3. Get details of a specific plan
get_plan("releases", "R2024.4")

# 4. Get items in a specific plan
get_plan_workitems("releases", "Sprint23")

# 5. Find child plans
search_plans("releases", "parent.id:R2024")
```


## Common Workflows

### 1. Project Discovery
```yaml
# Check connection and list all projects
health_check() → list_projects() → get_project_info("webstore")

# With configuration, shows:
# • webstore → WEBSTORE_V3 (configured types: defect, requirement, task)
# • releases → RELEASES_PROJECT [PLAN] (plan-based project)
```

### 2. Bug Analysis
```yaml
# Using named queries (recommended)
get_named_queries("webstore")  # See available: open_bugs, critical_bugs, my_items
search_workitems("webstore", "query:critical_bugs")
get_workitem("webstore", "WEBSTORE_V3-123")  # Details for specific bug

# Or custom query
search_workitems("webstore", 
  "type:defect AND severity:critical AND assignee.id:john.doe",
  "id,title,severity,status")  # Only needed fields
```

### 3. Test Management
```yaml
# Test runs
get_test_runs("qa") → get_test_run("qa", "QA-RUN-2024-01")

# Test specifications
get_documents("qa") → get_test_specs_from_document("qa", "Testing/AuthTests")
```

### 4. Sprint Planning
```yaml
# Sprint items not started
search_workitems("myproj", "plannedFor.id:Sprint23 AND status:(new OR open)")

# Requirements tracking
search_workitems("myproj", "type:requirement AND title:OAuth* AND NOT status:done")
```

## Query Patterns

### Named Queries (Configured)
- `query:open_bugs` - Expands to configured query
- `query:my_items` - Uses $current_user placeholder
- `query:sprint_items` - Current sprint work

### Lucene Query Syntax Rules
- **Operators**: Must be UPPERCASE: AND, OR, NOT
- **Whitespace**: Acts as OR operator: "term1 term2" = "term1 OR term2"
- **Parentheses**: Required for complex queries: "(type:defect AND priority:high) OR status:blocked"
- **Wildcards**: "*" multiple chars, "?" single char (cannot start with *)
- **Special Fields**: HAS_VALUE - check if field has value
- **Field Names**: Use field IDs, not display names (e.g., "assignee.id" not "assignee")
- **Date Ranges**: Use `$today$` constant with modifiers: `$today - 7d$`, `$today + 1w$`, `$today - 2m$`, `$today + 1y$`

### Lucene Query Examples
| Pattern | Query |
|---------|-------|
| Multiple conditions | `type:defect AND (priority:high OR priority:critical) AND status:open` |
| Date ranges | `created:[$today - 7d$ TO $today$]` or `updated:[2024-01-01 TO 2024-01-31]` |
| Text search | `title:authentication* AND description:SAML*` |
| Hierarchical | `parent.id:MYPROJ-100` (finds all children) |
| Missing fields | `NOT HAS_VALUE:description` or `NOT HAS_VALUE:assignee` |
| Has value check | `HAS_VALUE:dueDate AND dueDate:[* TO $today$]` (overdue items) |
| User assignment | `assignee.id:john.doe AND NOT status:closed` |
| Complex boolean | `(type:requirement OR type:specification) AND status:(open new)` |
| Wildcard searches | `title:OAuth* AND NOT title:deprecated*` |

## Working with Custom Fields

### Important Limitation
**Custom fields CANNOT be retrieved in search results** due to Polarion API limitations. However, you CAN search/filter by custom field values in queries.

### Searching by Custom Field Values
Custom fields use their direct names in queries (no prefix needed):

```yaml
# Find defects with critical severity (custom field)
search_workitems("webstore", "type:defect AND severity:critical")

# Find requirements with specific acceptance criteria
# Note: Wildcards cannot start a term (Lucene limitation)
search_workitems("webstore", "type:systemRequirement AND acceptanceCriteria:trigger*")

# Complex query with custom fields
search_workitems("webstore", 
  "type:defect AND severity:(critical OR major) AND foundInVersion:v2.1*")

# Check if custom field has value
search_workitems("webstore", "type:defect AND HAS_VALUE:severity")

# Find items missing custom field
search_workitems("webstore", "type:defect AND NOT HAS_VALUE:foundInVersion")
```

### Getting Custom Field Values (Workaround)
Since search results cannot include custom fields, use this two-step process:

```yaml
# Step 1: Search to find relevant items (returns IDs only)
search_workitems("webstore", "type:defect AND severity:critical", "id,title,status")
# Returns: WEBSTORE-123, WEBSTORE-456, etc.

# Step 2: Get full details for specific items (includes custom fields)
get_workitem("webstore", "WEBSTORE-123")
# Returns: All fields including custom fields like severity, foundInVersion, etc.
```

### Why This Limitation Exists
- The Polarion Search API (`searchWorkitem`) only supports standard fields in its field_list parameter
- Custom fields can only be retrieved through the WorkItem API (`getWorkitem`) which fetches individual items
- This is a fundamental Polarion API constraint, not a limitation of this MCP server

## Natural Language → Lucene

| You Say | Query |
|---------|-------|
| "my items" | `assignee.id:$current_user` |
| "high priority bugs" | `type:defect AND priority:high` |
| "critical severity bugs" | `type:defect AND severity:critical` (custom field) |
| "recently updated" | `updated:[$today - 7d$ TO $today$]` |
| "blocked items" | `status:blocked OR HAS_VALUE:blockedBy` |
| "overdue" | `HAS_VALUE:dueDate AND dueDate:[* TO $today$] AND NOT status:closed` |
| "needs testing" | `status:resolved AND verification:pending` |
| "unassigned items" | `NOT HAS_VALUE:assignee` |
| "items with no description" | `NOT HAS_VALUE:description` |
| "missing severity" | `type:defect AND NOT HAS_VALUE:severity` (custom field) |
| "critical bugs open today" | `type:defect AND priority:critical AND created:[$today$ TO $today$]` |
| "requirements with OAuth" | `type:requirement AND title:OAuth*` |
| "specific acceptance criteria" | `acceptanceCriteria:performance*` (custom field, no leading wildcard) |

## Performance Best Practices

### ✅ DO
```yaml
# Use default display fields for simple searches
search_workitems("proj", "type:defect AND status:open")  # Returns standard fields only

# Explicitly request custom fields when needed
search_workitems("proj", "type:defect AND status:open", "id,title,status,customFields.severity")

# Use configured queries
search_workitems("webstore", "query:critical_bugs")

# Check connection once per session
health_check() → [multiple operations...]
```

### ❌ DON'T
```yaml
# Fetch everything then filter
search_workitems("proj", "NOT type:null")  # Gets all items

# Expect custom fields without requesting them
search_workitems("proj", "type:defect")  # Won't get custom fields unless explicitly requested

# Repeatedly discover types
discover_work_item_types() for every search  # Use configuration instead
```

## Role-Specific Workflows

### QA Engineer Morning Routine
```yaml
health_check()
get_test_runs("qa")  # Overnight test results
search_workitems("qa", "type:defect AND created:[$today - 1d$ TO $today$]")  # New bugs
search_workitems("qa", "status:resolved AND verification:required")  # To verify
```

### Product Manager Sprint Planning
```yaml
list_projects()  # See all projects
get_project_types("webstore")  # Understand taxonomy
search_workitems("webstore", "query:backlog")  # Review backlog
search_workitems("webstore", "query:critical_bugs")  # Must-fix items
```

### Developer Task Management
```yaml
search_workitems("dev", "query:my_items")  # My assignments
get_workitem("dev", "DEV-123")  # Current task details
search_workitems("dev", "parent.id:DEV-123")  # Related subtasks
```

## Example Conversations

### "Something's wrong with login"
```yaml
search_workitems("web", 
  "type:defect AND (title:login* OR description:auth*) AND status:open")
→ For each critical bug: get_workitem("web", bug_id)
```

### "How did tests go?"
```yaml
get_test_runs("qa") 
→ get_test_run("qa", most_recent_id)
→ If failures: search_workitems("qa", "type:defect AND created:[$today - 1d$ TO $today$]")
```

### "Sprint progress?"
```yaml
search_workitems("proj", "plannedFor.id:Sprint23 AND status:done")  # Completed
search_workitems("proj", "plannedFor.id:Sprint23 AND NOT status:done")  # Remaining
→ Calculate percentage
```

## Error Handling

- **Connection fails**: Check credentials and URL format (`/polarion` not `/polarion/`)
- **Project not found**: Try `list_projects()` to see available aliases
- **Work item not found**: Verify ID format includes project prefix (e.g., PROJ-123)
- **Query returns nothing**: Simplify query or check field names
- **"❌" prefix**: Indicates error - check access rights or query syntax

## Tips for AI Agents

1. **Start with `health_check()`** for new sessions
2. **Use `list_projects()`** to discover available projects
3. **Prefer named queries** (`query:open_bugs`) over complex Lucene
4. **Specify field lists** to reduce data transfer
5. **Batch similar operations** instead of making many small calls
6. **Use project aliases** for cleaner, more maintainable code
7. **Chain tools logically**: List → Filter → Detail