"""
Helper functions for MCP tools to handle complex formatting and field extraction.
"""

from typing import Any, Dict, List, Optional

from mcp_server.config import ConfigManager


def extract_workitem_fields(
    item: Any, project_alias: str, config_manager: ConfigManager
) -> Dict[str, str]:
    """
    Extract all fields from a work item with robust error handling.

    Args:
        item: The work item object from Polarion
        project_alias: Project alias for custom field lookup
        config_manager: Configuration manager instance

    Returns:
        Dictionary of field names to values (as strings)
    """
    # Get the work item type to fetch appropriate fields
    work_item_type = getattr(item.type, "id", None) if hasattr(item, "type") else None

    # Start with basic details that should always work
    details = {
        "ID": item.id,
        "Title": getattr(item, "title", "N/A"),
        "Type": work_item_type or "N/A",
    }

    # Try to get standard fields with error handling
    try:
        details["Status"] = (
            getattr(item.status, "id", "N/A") if hasattr(item, "status") else "N/A"
        )
    except Exception:
        details["Status"] = "N/A"

    try:
        details["Author"] = (
            getattr(item.author, "id", "N/A") if hasattr(item, "author") else "N/A"
        )
    except Exception:
        details["Author"] = "N/A"

    try:
        details["Created"] = str(getattr(item, "created", "N/A"))
    except Exception:
        details["Created"] = "N/A"

    try:
        details["Description"] = (
            getattr(item.description, "content", "N/A")
            if hasattr(item, "description")
            else "N/A"
        )
    except Exception:
        details["Description"] = "N/A"

    # Try to get custom fields if work item type is known
    if work_item_type:
        custom_fields = config_manager.get_custom_fields(project_alias, work_item_type)
        if custom_fields:
            for field_name in custom_fields:
                try:
                    # Use getCustomField method if available (real Polarion objects)
                    if hasattr(item, "getCustomField"):
                        value = item.getCustomField(field_name)
                        if value is not None:
                            details[f"Custom.{field_name}"] = str(value)
                    # For mock objects in tests, try direct attribute access
                    elif hasattr(item, "customFields"):
                        value = getattr(item.customFields, field_name, None)
                        if value is not None:
                            details[f"Custom.{field_name}"] = str(value)
                except Exception:
                    # Skip individual custom fields that cause errors
                    pass

    return details


def format_workitem_details(details: Dict[str, str], workitem_id: str) -> str:
    """
    Format work item details into a readable string.

    Args:
        details: Dictionary of field names to values
        workitem_id: The work item ID for the header

    Returns:
        Formatted string with work item details
    """
    output = f"Work Item Details for '{workitem_id}':\n"
    for key, value in details.items():
        output += f"- {key}: {value}\n"
    return output


def format_search_result(item: Dict[str, Any], requested_fields: List[str]) -> str:
    """
    Format a single search result item into a readable string.

    Args:
        item: Dictionary representing a work item from search results
        requested_fields: List of fields that were requested (to filter display)

    Returns:
        Formatted string with item details
    """
    item_details = []

    # Only show the requested fields
    for key in requested_fields:
        value = item.get(key)
        if value is not None:
            # Handle nested objects (like type.id becomes {'id': 'defect'})
            if isinstance(value, dict) and "id" in value:
                item_details.append(f"{key}: {value['id']}")
            # Handle other dictionaries (like customFields)
            elif isinstance(value, dict):
                item_details.append(f"{key}: {value}")
            else:
                item_details.append(f"{key}: {value}")
    return ", ".join(item_details) if item_details else "No details"


def format_search_results(
    results: List[Dict[str, Any]],
    query: str,
    resolved_query: str,
    actual_project_id: str,
    requested_fields: List[str],
    max_items: int = 20,
) -> str:
    """
    Format search results into a readable string.

    Args:
        results: List of work items from search
        query: Original query string
        resolved_query: Resolved query (after named query expansion)
        actual_project_id: The actual project ID
        requested_fields: List of fields that were requested (to filter display)
        max_items: Maximum number of items to display

    Returns:
        Formatted string with search results
    """
    if not results:
        output = f"No work items found in project '{actual_project_id}'"
        if query != resolved_query:
            output += f" for named query '{query}' (expanded to: '{resolved_query}')"
        else:
            output += f" for query: '{query}'"
        return output

    output = f"Found {len(results)} work items"
    if query != resolved_query:
        output += f" for named query '{query}'"
    else:
        output += f" for query '{query}'"
    output += ":\n\n"

    for i, item in enumerate(results[:max_items], 1):
        output += f"{i}. "
        # Results from searchWorkitem are dictionaries
        if isinstance(item, dict):
            output += format_search_result(item, requested_fields)
        else:
            # Fallback for object format (shouldn't happen with searchWorkitem)
            item_details = {
                "ID": getattr(item, "id", "N/A"),
                "Title": getattr(item, "title", "N/A"),
            }
            details_str = ", ".join(
                f"{k}: {v}" for k, v in item_details.items() if v != "N/A"
            )
            output += details_str
        output += "\n"

    if len(results) > max_items:
        output += f"\n...and {len(results) - max_items} more."

    return output


def format_test_runs(
    test_runs: List[Any], actual_project_id: str, max_items: int = 20
) -> str:
    """
    Format test runs into a readable string.

    Args:
        test_runs: List of test run objects
        actual_project_id: The actual project ID
        max_items: Maximum number of items to display

    Returns:
        Formatted string with test runs
    """
    if not test_runs:
        return f"No test runs found in project '{actual_project_id}'."

    output = f"Found {len(test_runs)} test runs in project '{actual_project_id}':\n\n"
    for i, run in enumerate(test_runs[:max_items], 1):
        output += f"{i}. ID: {run.id}, Title: {getattr(run, 'title', 'N/A')}, Status: {getattr(run, 'status', 'N/A')}\n"

    if len(test_runs) > max_items:
        output += f"\n...and {len(test_runs) - max_items} more."

    return output


def extract_test_run_details(test_run: Any) -> Dict[str, str]:
    """
    Extract details from a test run object.

    Args:
        test_run: Test run object from Polarion

    Returns:
        Dictionary of field names to values
    """
    return {
        "ID": test_run.id,
        "Title": getattr(test_run, "title", "N/A"),
        "Status": getattr(test_run, "status", "N/A"),
        "Created": str(getattr(test_run, "created", "N/A")),
        "Finished": str(getattr(test_run, "finished", "N/A")),
        "Test Cases": str(len(test_run.records) if hasattr(test_run, "records") else 0),
    }


def format_test_run_details(details: Dict[str, str], test_run_id: str) -> str:
    """
    Format test run details into a readable string.

    Args:
        details: Dictionary of field names to values
        test_run_id: The test run ID for the header

    Returns:
        Formatted string with test run details
    """
    output = f"Test Run Details for '{test_run_id}':\n"
    for key, value in details.items():
        output += f"- {key}: {value}\n"
    return output


def extract_work_item_types_from_results(
    results: List[Dict[str, Any]], limit: int = 1000
) -> Dict[str, int]:
    """
    Extract work item types and their counts from search results.

    Args:
        results: List of work items from search
        limit: Maximum number of items to process

    Returns:
        Dictionary mapping type names to occurrence counts
    """
    types_count: Dict[str, int] = {}

    for item in results[:limit]:
        # Results from searchWorkitem are dictionaries
        if isinstance(item, dict):
            type_info = item.get("type")
            if isinstance(type_info, dict):
                type_value = type_info.get("id")
            else:
                type_value = type_info
        else:
            # Fallback for object format
            type_value = (
                getattr(item.type, "id", None) if hasattr(item, "type") else None
            )

        if type_value:
            types_count[type_value] = types_count.get(type_value, 0) + 1

    return types_count


def format_discovered_types(
    types_count: Dict[str, int], actual_project_id: str, sample_size: int
) -> str:
    """
    Format discovered work item types into a readable string.

    Args:
        types_count: Dictionary mapping type names to counts
        actual_project_id: The actual project ID
        sample_size: Number of items that were sampled

    Returns:
        Formatted string with discovered types
    """
    if not types_count:
        return f"Could not discover work item types in project '{actual_project_id}'."

    output = f"Discovered work item types in project '{actual_project_id}' (sampled {sample_size} items):\n\n"
    for type_name, count in sorted(
        types_count.items(), key=lambda x: x[1], reverse=True
    ):
        output += f"- {type_name}: {count} occurrences\n"

    output += f"\n💡 Tip: Add these types to polarion_config.yaml to avoid repeated discovery."

    return output


def format_configured_types(
    configured_types: List[str],
    project_alias: str,
    actual_project_id: str,
    config_manager: ConfigManager,
) -> str:
    """
    Format configured work item types with their fields.

    Args:
        configured_types: List of configured type names
        project_alias: Project alias for field lookup
        actual_project_id: The actual project ID
        config_manager: Configuration manager instance

    Returns:
        Formatted string with configured types and their fields
    """
    output = f"Work Item Types for '{actual_project_id}' (from configuration):\n\n"

    for type_name in configured_types:
        output += f"- {type_name}\n"
        # Show all fields that will be returned for this type
        all_fields = config_manager.get_combined_fields(project_alias, type_name)
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

    output += f"\nTotal: {len(configured_types)} configured types"
    return output


def format_plans(plans: List[Any], actual_project_id: str, max_items: int = 20) -> str:
    """
    Format plans into a readable string.

    Args:
        plans: List of plan objects
        actual_project_id: The actual project ID
        max_items: Maximum number of items to display

    Returns:
        Formatted string with plans
    """
    if not plans:
        return f"No plans found in project '{actual_project_id}'."

    output = f"Found {len(plans)} plans in project '{actual_project_id}':\n\n"
    for i, plan in enumerate(plans[:max_items], 1):
        output += f"{i}. ID: {plan.id}, Name: {getattr(plan, 'name', 'N/A')}, Template: {getattr(plan, 'templateId', 'N/A')}\n"
        if hasattr(plan, "startDate") and hasattr(plan, "dueDate"):
            output += f"   Period: {getattr(plan, 'startDate', 'N/A')} to {getattr(plan, 'dueDate', 'N/A')}\n"

    if len(plans) > max_items:
        output += f"\n...and {len(plans) - max_items} more."

    return output


def extract_plan_details(plan: Any) -> Dict[str, str]:
    """
    Extract details from a plan object.

    Args:
        plan: Plan object from Polarion

    Returns:
        Dictionary of field names to values
    """
    details = {
        "ID": plan.id,
        "Name": getattr(plan, "name", "N/A"),
        "Template": getattr(plan, "templateId", "N/A"),
        "Start Date": str(getattr(plan, "startDate", "N/A")),
        "Due Date": str(getattr(plan, "dueDate", "N/A")),
        "Started On": str(getattr(plan, "startedOn", "N/A")),
        "Finished On": str(getattr(plan, "finishedOn", "N/A")),
    }

    # Check if plan has parent
    if hasattr(plan, "parent") and plan.parent:
        details["Parent Plan"] = getattr(plan.parent, "id", "N/A")

    # Check for allowed types
    if hasattr(plan, "allowedTypes") and plan.allowedTypes:
        types = []
        if hasattr(plan.allowedTypes, "EnumOptionId"):
            for type_option in plan.allowedTypes.EnumOptionId:
                types.append(type_option.id)
        if types:
            details["Allowed Types"] = ", ".join(types)

    return details


def format_plan_details(details: Dict[str, str], plan_id: str) -> str:
    """
    Format plan details into a readable string.

    Args:
        details: Dictionary of field names to values
        plan_id: The plan ID for the header

    Returns:
        Formatted string with plan details
    """
    output = f"Plan Details for '{plan_id}':\n"
    for key, value in details.items():
        output += f"- {key}: {value}\n"
    return output


def format_plan_workitems(
    workitems: List[Any], plan_id: str, max_items: int = 20
) -> str:
    """
    Format work items in a plan into a readable string.

    Args:
        workitems: List of work item objects
        plan_id: The plan ID
        max_items: Maximum number of items to display

    Returns:
        Formatted string with work items
    """
    if not workitems:
        return f"No work items found in plan '{plan_id}'."

    output = f"Found {len(workitems)} work items in plan '{plan_id}':\n\n"
    for i, item in enumerate(workitems[:max_items], 1):
        output += f"{i}. ID: {item.id}, Title: {getattr(item, 'title', 'N/A')}, Type: {getattr(item.type, 'id', 'N/A') if hasattr(item, 'type') else 'N/A'}, Status: {getattr(item.status, 'id', 'N/A') if hasattr(item, 'status') else 'N/A'}\n"

    if len(workitems) > max_items:
        output += f"\n...and {len(workitems) - max_items} more."

    return output
