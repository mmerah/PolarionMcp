import logging
import re
from typing import Optional

from fastmcp import FastMCP

from lib.polarion.polarion_driver import PolarionConnectionException, PolarionDriver
from mcp_server.helpers import (
    extract_plan_details,
    extract_test_run_details,
    extract_work_item_types_from_results,
    extract_workitem_fields,
    format_configured_types,
    format_discovered_types,
    format_plan_details,
    format_plan_workitems,
    format_plans,
    format_search_results,
    format_test_run_details,
    format_test_runs,
    format_workitem_details,
)
from mcp_server.settings import config_manager, settings

logger = logging.getLogger(__name__)

# Initialize FastMCP server instance
mcp: FastMCP = FastMCP("polarion-mcp")

# --- Configuration Tools ---


@mcp.tool
async def list_projects() -> str:
    """
    List all configured project aliases.

    Returns: List of configured projects with aliases and descriptions
             or message if no projects configured
    """
    projects = config_manager.list_projects()

    if not projects:
        return "No projects configured. Create a polarion_config.yaml file to define project aliases."

    output = f"Configured Projects ({len(projects)}):\n\n"
    for proj in projects:
        output += f"- {proj['alias']} -> {proj['id']}"
        if proj.get("is_plan"):
            output += " [PLAN]"
        output += "\n"
        if proj["name"]:
            output += f"  Name: {proj['name']}\n"
        if proj["description"]:
            output += f"  Description: {proj['description']}\n"
        output += "\n"

    return output.strip()


@mcp.tool
async def get_project_types(project_alias_or_id: str) -> str:
    """
    Get configured work item types for a project.

    Args:
        project_alias_or_id: Project alias or ID

    Returns: List of work item types or message to use discover
    """
    config = config_manager.get_project_config(project_alias_or_id)

    if not config:
        return f"No configuration found for project '{project_alias_or_id}'. Use discover_work_item_types to explore."

    if not config.work_item_types:
        return f"No work item types configured for '{project_alias_or_id}'. Use discover_work_item_types to explore."

    output = f"Work Item Types for '{config.name or project_alias_or_id}':\n\n"
    for type_name in config.work_item_types:
        output += f"- {type_name}\n"
        # Show all fields that will be returned for this type
        all_fields = config_manager.get_combined_fields(project_alias_or_id, type_name)
        if all_fields:
            # Separate standard and custom fields for clarity
            standard_fields = [
                f for f in all_fields if not f.startswith("customFields.")
            ]
            custom_fields = [
                f.replace("customFields.", "")
                for f in all_fields
                if f.startswith("customFields.")
            ]

            output += f"  Standard fields: {', '.join(standard_fields)}\n"
            if custom_fields:
                output += f"  Additional custom fields: {', '.join(custom_fields)}\n"

    return output


@mcp.tool
async def get_named_queries(project_alias_or_id: str) -> str:
    """
    Get available named queries for a project.

    Args:
        project_alias_or_id: Project alias or ID

    Returns: List of named queries with their Lucene expansions
    """
    config = config_manager.get_project_config(project_alias_or_id)

    if not config:
        return f"No configuration found for project '{project_alias_or_id}'."

    output = f"Named Queries for '{config.name or project_alias_or_id}':\n\n"

    # Project-specific queries
    if config.default_queries:
        output += "Project Queries:\n"
        for name, query in config.default_queries.items():
            output += f"- query:{name}\n"
            output += f"  -> {query}\n"

    return output


# --- MCP Tools ---


@mcp.tool
async def health_check() -> str:
    """
    Verify Polarion connection and credentials.

    Returns: "✅ Polarion connection is healthy" or "❌ [error message]"
    Requires: POLARION_URL, POLARION_USER, POLARION_TOKEN env vars
    """
    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ):
            return "✅ Polarion connection is healthy."
    except PolarionConnectionException as e:
        logger.error(f"Health check failed: {e}")
        return f"❌ Polarion connection failed: {e}"
    except Exception as e:
        logger.error(f"An unexpected error occurred during health check: {e}")
        return f"❌ An unexpected error occurred: {e}"


@mcp.tool
async def get_project_info(project_alias: str) -> str:
    """
    Get project name and description.

    Args:
        project_alias: Project alias or ID (e.g., "webstore" or "MYPROJ")

    Returns: "Project Information for '{id}':" followed by name/description
             or "❌ [error message]" on failure

    Note: Also validates project exists and you have access.
    """
    # Resolve project alias to actual ID
    actual_project_id = config_manager.resolve_project_id(project_alias)

    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ) as driver:
            driver.select_project(actual_project_id)
            info = driver.get_project_info()

            # Add config info if available
            config = config_manager.get_project_config(project_alias)
            output = f"Project Information for '{actual_project_id}'"
            if config and project_alias != actual_project_id:
                output += f" (alias: {project_alias})"
            output += ":\n"
            output += f"- Name: {info.get('name', 'N/A')}\n"
            output += f"- Description: {info.get('description', 'N/A')}"

            # Add configured types if available
            if config and config.work_item_types:
                output += (
                    f"\n- Configured Types: {', '.join(config.work_item_types[:5])}"
                )
                if len(config.work_item_types) > 5:
                    output += f" (and {len(config.work_item_types) - 5} more)"

            return output
    except Exception as e:
        logger.error(f"Failed to get project info for '{project_alias}': {e}")
        return f"❌ Failed to get project info: {e}"


@mcp.tool
async def get_workitem(project_alias: str, workitem_id: str) -> str:
    """
    Get work item details (title, type, status, author, dates, description).

    Args:
        project_alias: Project alias or ID (e.g., "webstore" or "MYPROJ")
        workitem_id: Full ID with prefix (e.g., "MYPROJ-123")

    Returns: "Work Item Details for '{id}':" with formatted details
             or "❌ [error message]" on failure
    """
    # Resolve project alias to actual ID
    actual_project_id = config_manager.resolve_project_id(project_alias)

    # Check if this is a plan project
    if config_manager.is_plan_project(project_alias):
        return (
            f"❌ get_workitem is not currently supported for plan projects.\n"
            f"Please use:\n"
            f"  - get_plan_workitems('{project_alias}', 'PLAN-ID') to see items in a specific plan\n"
            f"  - get_plans('{project_alias}') to list available plans"
        )

    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ) as driver:
            driver.select_project(actual_project_id)
            item = driver.get_workitem(workitem_id)

            # Extract all fields with error handling
            details = extract_workitem_fields(item, project_alias, config_manager)

            # Format and return the details
            return format_workitem_details(details, workitem_id)
    except Exception as e:
        logger.error(f"Failed to get work item '{workitem_id}': {e}")
        return f"❌ Failed to get work item: {e}"


@mcp.tool
async def search_workitems(
    project_alias: str, query: str, field_list: Optional[str] = None
) -> str:
    """
    Search work items using Lucene query syntax or named queries.

    Args:
        project_alias: Project alias or ID (e.g., "webstore" or "MYPROJ")
        query: Lucene query or named query (e.g., "query:open_bugs")
        field_list: Optional CSV fields (e.g., "id,title,type,status")
                   NOTE: Custom fields CANNOT be retrieved via field_list due to Polarion API limitations

    Returns: "Found N work items..." with up to 20 results
             "...and X more" if >20 results
             or "❌ [error message]" on failure

    IMPORTANT - Custom Fields:
    - Searching BY custom fields: Use field name directly in queries (e.g., "severity:critical")
    - Retrieving custom field VALUES: NOT supported in search results due to Polarion API limitations
    - Workaround: Use search to find items, then call get_workitem() for full details including custom fields

    Lucene Query Syntax (based on Apache Lucene):
    - Operators must be UPPERCASE: AND, OR, NOT
    - White space acts as OR operator: "term1 term2" = "term1 OR term2"
    - Use parentheses for complex queries: "(type:defect AND priority:high) OR status:blocked"
    - Wildcards: "*" for multiple chars, "?" for single char (cannot start with *)
    - Special field: HAS_VALUE - check if field has value: "HAS_VALUE:resolution" or "NOT HAS_VALUE:assignee"
    - Date ranges: "created:[$today - 7d$ TO $today$]" or "updated:[2024-01-01 TO 2024-01-31]"
    - Field syntax: Use field IDs, not display names (e.g., "assignee.id" not "assignee")
    - Custom fields: Use direct field names (e.g., "severity:critical", "acceptanceCriteria:trigger*")

    Query examples:
    - "type:defect AND status:open" (basic field queries)
    - "type:defect AND severity:critical" (search by custom field value)
    - "acceptanceCriteria:trigger* AND type:systemRequirement" (custom field with wildcard)
    - "assignee.id:john.doe AND NOT status:closed" (user assignment)
    - "type:requirement AND title:OAuth*" (text search with wildcards, cannot start with *)
    - "(priority:high OR priority:critical) AND NOT status:resolved" (complex boolean)
    - "created:[$today - 7d$ TO $today$]" (date range - last 7 days)
    - "HAS_VALUE:dueDate AND dueDate:[* TO $today$]" (overdue items)
    - "NOT HAS_VALUE:assignee" (unassigned items)
    - "NOT HAS_VALUE:severity" (items without severity custom field)
    - "parent.id:PROJ-123" (hierarchical - find children)
    - "query:open_bugs" (uses configured named query)
    - "query:my_items" (expands to configured query with $current_user)
    """
    # Resolve project alias to actual ID
    actual_project_id = config_manager.resolve_project_id(project_alias)

    # Check if this is a plan project
    if config_manager.is_plan_project(project_alias):
        return (
            f"❌ search_workitems is not currently supported for plan projects.\n"
            f"Please use:\n"
            f"  - get_plan_workitems('{project_alias}', 'PLAN-ID') to see items in a specific plan\n"
            f"  - get_plans('{project_alias}') to list available plans\n"
            f"  - search_plans('{project_alias}', 'query') to search for specific plans"
        )

    # Resolve named queries
    resolved_query = config_manager.resolve_query(project_alias, query)

    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ) as driver:
            driver.select_project(actual_project_id)

            # Always use default fields unless explicitly specified
            # This avoids ClassCastException issues with custom fields on certain work item types
            if field_list:
                fields = [f.strip() for f in field_list.split(",")]
            else:
                # Always use default display fields
                # Users can explicitly provide field_list if they need custom fields
                fields = config_manager.get_display_fields()

            results = driver.search_workitems(resolved_query, fields)

            # Format and return the results
            return format_search_results(
                results, query, resolved_query, actual_project_id, fields
            )
    except Exception as e:
        logger.error(f"Failed to search work items with query '{query}': {e}")
        return f"❌ Failed to search work items: {e}"


@mcp.tool
async def get_test_runs(project_alias: str) -> str:
    """
    List test runs with ID, title, and status.

    Args:
        project_alias: Project alias or ID (e.g., "webstore" or "MYPROJ")

    Returns: "Found N test runs..." with up to 20 results
             or "❌ [error message]" on failure
    """
    # Resolve project alias to actual ID
    actual_project_id = config_manager.resolve_project_id(project_alias)

    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ) as driver:
            driver.select_project(actual_project_id)
            test_runs = driver.get_test_runs()

            # Format and return the test runs
            return format_test_runs(test_runs, actual_project_id)
    except Exception as e:
        logger.error(f"Failed to get test runs: {e}")
        return f"❌ Failed to get test runs: {e}"


@mcp.tool
async def get_test_run(project_alias: str, test_run_id: str) -> str:
    """
    Get test run details (status, dates, test case count).

    Args:
        project_alias: Project alias or ID (e.g., "webstore" or "MYPROJ")
        test_run_id: Test run ID

    Returns: "Test Run Details for '{id}':" with formatted details
             or "❌ [error message]" on failure
    """
    # Resolve project alias to actual ID
    actual_project_id = config_manager.resolve_project_id(project_alias)

    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ) as driver:
            driver.select_project(actual_project_id)
            test_run = driver.get_test_run(test_run_id)

            # Extract and format test run details
            details = extract_test_run_details(test_run)
            return format_test_run_details(details, test_run_id)
    except Exception as e:
        logger.error(f"Failed to get test run '{test_run_id}': {e}")
        return f"❌ Failed to get test run: {e}"


@mcp.tool
async def get_documents(project_alias: str) -> str:
    """
    List documents with ID, title, and location.

    Args:
        project_alias: Project alias or ID (e.g., "webstore" or "MYPROJ")

    Returns: "Found N documents..." with up to 20 results
             or "❌ [error message]" on failure

    Note: Use returned IDs with get_test_specs_from_document.
    """
    # Resolve project alias to actual ID
    actual_project_id = config_manager.resolve_project_id(project_alias)

    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ) as driver:
            driver.select_project(actual_project_id)
            documents = driver.get_documents()

            if not documents:
                return f"No documents found in project '{actual_project_id}'."

            output = f"Found {len(documents)} documents in project '{actual_project_id}':\n\n"
            for i, doc in enumerate(documents[:20], 1):
                output += f"{i}. ID: {doc.id}, Title: {getattr(doc, 'title', 'N/A')}, Location: {getattr(doc, 'moduleFolder', 'N/A')}\n"

            if len(documents) > 20:
                output += f"\n...and {len(documents) - 20} more."
            return output
    except Exception as e:
        logger.error(f"Failed to get documents: {e}")
        return f"❌ Failed to get documents: {e}"


@mcp.tool
async def get_test_specs_from_document(project_alias: str, document_id: str) -> str:
    """
    Extract test case IDs from a document.

    Args:
        project_alias: Project alias or ID (e.g., "webstore" or "MYPROJ")
        document_id: Document location (e.g., "QA/TestSpecs")

    Returns: "Found N test specifications..." with up to 50 IDs
             or "❌ [error message]" on failure

    Note: Searches for type:testcase items linked to document.
    """
    # Resolve project alias to actual ID
    actual_project_id = config_manager.resolve_project_id(project_alias)

    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ) as driver:
            driver.select_project(actual_project_id)

            # First get the document
            doc = driver.get_document(document_id)
            if not doc:
                return f"Document '{document_id}' not found in project '{actual_project_id}'."

            # Get test spec IDs from document
            test_spec_ids = driver.test_spec_ids_in_doc(doc)

            if not test_spec_ids:
                return f"No test specifications found in document '{document_id}'."

            output = f"Found {len(test_spec_ids)} test specifications in document '{document_id}':\n"
            for i, spec_id in enumerate(sorted(test_spec_ids)[:50], 1):
                output += f"{i}. {spec_id}\n"

            if len(test_spec_ids) > 50:
                output += f"\n...and {len(test_spec_ids) - 50} more."
            return output
    except Exception as e:
        logger.error(f"Failed to get test specs from document '{document_id}': {e}")
        return f"❌ Failed to get test specs: {e}"


@mcp.tool
async def discover_work_item_types(project_alias: str, limit: int = 1000) -> str:
    """
    Discover work item types by sampling project items.

    Args:
        project_alias: Project alias or ID (e.g., "webstore" or "MYPROJ")
        limit: Max items to sample (default: 1000)

    Returns: "Discovered work item types..." with type frequencies
             or "❌ [error message]" on failure

    Note: Uses configuration cache if available, otherwise discovers from Polarion.
    """
    # Resolve project alias to actual ID
    actual_project_id = config_manager.resolve_project_id(project_alias)

    # Check if types are configured
    configured_types = config_manager.get_work_item_types(project_alias)
    if configured_types:
        return format_configured_types(
            configured_types, project_alias, actual_project_id, config_manager
        )

    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ) as driver:
            driver.select_project(actual_project_id)

            # Search for work items with type field
            results = driver.search_workitems("NOT type:null", ["id", "type"])

            # Extract and count work item types
            types_count = extract_work_item_types_from_results(results, limit)

            # Format and return the discovered types
            sample_size = min(len(results), limit)
            return format_discovered_types(types_count, actual_project_id, sample_size)
    except Exception as e:
        logger.error(f"Failed to discover work item types: {e}")
        return f"❌ Failed to discover work item types: {e}"


# --- Plan-specific Tools ---


@mcp.tool
async def get_plans(project_alias: str) -> str:
    """
    List plans (releases, iterations) in a project.

    Args:
        project_alias: Project alias or ID (e.g., "releases" or "MYPROJ")

    Returns: "Found N plans..." with up to 20 results
             or "❌ [error message]" on failure

    Note: Only works for projects configured with is_plan: true
    """
    # Resolve project alias to actual ID
    actual_project_id = config_manager.resolve_project_id(project_alias)

    # Check if this is a plan project
    if not config_manager.is_plan_project(project_alias):
        return f"Project '{actual_project_id}' is not configured as a plan project. Set 'is_plan: true' in configuration if this project contains plans."

    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ) as driver:
            driver.select_project(actual_project_id)
            # Pass empty string explicitly to get all plans
            plans = driver.search_plans("")

            # Format and return the plans
            return format_plans(plans, actual_project_id)
    except Exception as e:
        logger.error(f"Failed to get plans: {e}")
        return f"❌ Failed to get plans: {e}"


@mcp.tool
async def get_plan(project_alias: str, plan_id: str) -> str:
    """
    Get plan details (name, dates, template, allowed types).

    Args:
        project_alias: Project alias or ID (e.g., "releases" or "MYPROJ")
        plan_id: Plan ID (e.g., "R2024.4" or "Sprint23")

    Returns: "Plan Details for '{id}':" with formatted details
             or "❌ [error message]" on failure

    Note: Only works for projects configured with is_plan: true
    """
    # Resolve project alias to actual ID
    actual_project_id = config_manager.resolve_project_id(project_alias)

    # Check if this is a plan project
    if not config_manager.is_plan_project(project_alias):
        return f"Project '{actual_project_id}' is not configured as a plan project. Set 'is_plan: true' in configuration if this project contains plans."

    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ) as driver:
            driver.select_project(actual_project_id)
            plan = driver.get_plan(plan_id)

            # Extract and format plan details
            details = extract_plan_details(plan)
            return format_plan_details(details, plan_id)
    except Exception as e:
        logger.error(f"Failed to get plan '{plan_id}': {e}")
        return f"❌ Failed to get plan: {e}"


@mcp.tool
async def get_plan_workitems(project_alias: str, plan_id: str) -> str:
    """
    Get work items in a specific plan.

    Args:
        project_alias: Project alias or ID (e.g., "releases" or "MYPROJ")
        plan_id: Plan ID (e.g., "R2024.4" or "Sprint23")

    Returns: "Found N work items in plan..." with up to 20 results
             or "❌ [error message]" on failure

    Note: Only works for projects configured with is_plan: true
    """
    # Resolve project alias to actual ID
    actual_project_id = config_manager.resolve_project_id(project_alias)

    # Check if this is a plan project
    if not config_manager.is_plan_project(project_alias):
        return f"Project '{actual_project_id}' is not configured as a plan project. Set 'is_plan: true' in configuration if this project contains plans."

    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ) as driver:
            driver.select_project(actual_project_id)
            plan = driver.get_plan(plan_id)

            # Get work items from the plan
            workitems = plan.getWorkitemsInPlan()

            # Format and return the work items
            return format_plan_workitems(workitems, plan_id)
    except Exception as e:
        logger.error(f"Failed to get work items for plan '{plan_id}': {e}")
        return f"❌ Failed to get plan work items: {e}"


@mcp.tool
async def search_plans(project_alias: str, query: str = "") -> str:
    """
    Search for plans using Lucene query syntax.

    Args:
        project_alias: Project alias or ID (e.g., "releases" or "MYPROJ")
        query: Lucene query (e.g., "templateId:release", "parent.id:R2024")

    Returns: "Found N plans..." with up to 20 results
             or "❌ [error message]" on failure

    Query examples:
    - "templateId:release" (find all release plans)
    - "templateId:iteration" (find all iteration plans)
    - "parent.id:R2024" (find child plans of R2024)
    - "name:Sprint*" (find plans with names starting with Sprint)
    - "dueDate:[$today$ TO $today + 30d$]" (plans due in next 30 days)

    Note: Only works for projects configured with is_plan: true
    """
    # Resolve project alias to actual ID
    actual_project_id = config_manager.resolve_project_id(project_alias)

    # Check if this is a plan project
    if not config_manager.is_plan_project(project_alias):
        return f"Project '{actual_project_id}' is not configured as a plan project. Set 'is_plan: true' in configuration if this project contains plans."

    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ) as driver:
            driver.select_project(actual_project_id)
            plans = driver.search_plans(query)

            # Format and return the plans
            if not plans:
                return f"No plans found in project '{actual_project_id}' for query: '{query}'"

            output = f"Found {len(plans)} plans for query '{query}':\n\n"
            for i, plan in enumerate(plans[:20], 1):
                output += f"{i}. ID: {plan.id}, Name: {getattr(plan, 'name', 'N/A')}, Template: {getattr(plan, 'templateId', 'N/A')}\n"
                if hasattr(plan, "startDate") and hasattr(plan, "dueDate"):
                    output += f"   Period: {getattr(plan, 'startDate', 'N/A')} to {getattr(plan, 'dueDate', 'N/A')}\n"

            if len(plans) > 20:
                output += f"\n...and {len(plans) - 20} more."

            return output
    except Exception as e:
        logger.error(f"Failed to search plans with query '{query}': {e}")
        return f"❌ Failed to search plans: {e}"


# --- MCP Resources ---


@mcp.resource("polarion://project/{project_id}")
async def get_project_resource(project_id: str) -> str:
    """
    MCP resource for project information.

    Args:
        project_id: Project alias or ID (e.g., "webstore" or "MYPROJ")

    Returns: Same as get_project_info()
    URI: polarion://project/{project_id}
    """
    # Call the actual function implementation, not the tool wrapper
    return await get_project_info.fn(project_id)


# --- MCP Prompts ---


@mcp.prompt
async def analyze_project(project_alias: str) -> str:
    """
    Generate analysis prompt for a project.

    Args:
        project_alias: Project alias or ID (e.g., "webstore" or "MYPROJ")

    Returns: Prompt with embedded project info for analysis.
    """
    # Call the actual function implementation, not the tool wrapper
    project_info = await get_project_info.fn(project_alias)
    return (
        f"Please analyze this Polarion project and provide insights:\n\n{project_info}"
    )


@mcp.prompt
async def workitem_analysis(project_alias: str, workitem_id: str) -> str:
    """
    Generate analysis prompt for a work item.

    Args:
        project_alias: Project alias or ID (e.g., "webstore" or "MYPROJ")
        workitem_id: Full ID with prefix (e.g., "MYPROJ-123")

    Returns: Prompt with embedded work item info for recommendations.
    """
    # Call the actual function implementation, not the tool wrapper
    workitem_info = await get_workitem.fn(project_alias, workitem_id)
    return f"Please analyze this Polarion work item and provide recommendations:\n\n{workitem_info}"
