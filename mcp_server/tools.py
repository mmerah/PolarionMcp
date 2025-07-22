import logging
from typing import Optional

from fastmcp import FastMCP

from lib.polarion.polarion_driver import PolarionConnectionException, PolarionDriver
from mcp_server.settings import settings

logger = logging.getLogger(__name__)

# Initialize FastMCP server instance
mcp: FastMCP = FastMCP("polarion-mcp")

# --- MCP Tools ---


@mcp.tool
async def health_check() -> str:
    """Checks the Polarion connection and returns a status message."""
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
async def get_project_info(project_id: str) -> str:
    """Retrieves and formats information for a given Polarion project."""
    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ) as driver:
            driver.select_project(project_id)
            info = driver.get_project_info()
            return (
                f"Project Information for '{project_id}':\n"
                f"- Name: {info.get('name', 'N/A')}\n"
                f"- Description: {info.get('description', 'N/A')}"
            )
    except Exception as e:
        logger.error(f"Failed to get project info for '{project_id}': {e}")
        return f"❌ Failed to get project info: {e}"


@mcp.tool
async def get_workitem(project_id: str, workitem_id: str) -> str:
    """Retrieves and formats details for a specific work item."""
    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ) as driver:
            driver.select_project(project_id)
            item = driver.get_workitem(workitem_id)

            details = {
                "ID": item.id,
                "Title": getattr(item, "title", "N/A"),
                "Type": getattr(item.type, "id", "N/A"),
                "Status": getattr(item.status, "id", "N/A"),
                "Author": getattr(item.author, "id", "N/A"),
                "Created": str(getattr(item, "created", "N/A")),
                "Description": getattr(item.description, "content", "N/A"),
            }

            output = f"Work Item Details for '{workitem_id}':\n"
            for key, value in details.items():
                output += f"- {key}: {value}\n"
            return output
    except Exception as e:
        logger.error(f"Failed to get work item '{workitem_id}': {e}")
        return f"❌ Failed to get work item: {e}"


@mcp.tool
async def search_workitems(
    project_id: str, query: str, field_list: Optional[str] = None
) -> str:
    """Searches for work items and returns a formatted list of results."""
    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ) as driver:
            driver.select_project(project_id)

            fields = None
            if field_list:
                fields = [f.strip() for f in field_list.split(",")]

            results = driver.search_workitems(query, fields)

            if not results:
                return f"No work items found in project '{project_id}' for query: '{query}'"

            output = f"Found {len(results)} work items for query '{query}':\n\n"
            for i, item in enumerate(results[:20], 1):  # Limit to 20 results for chat
                output += f"{i}. "
                if isinstance(item, dict):
                    details = ", ".join([f"{k}: {v}" for k, v in item.items()])
                    output += f"{details}\n"
                else:  # It's a Workitem object
                    output += (
                        f"ID: {getattr(item, 'id', 'N/A')}, "
                        f"Title: {getattr(item, 'title', 'N/A')}, "
                        f"Status: {getattr(item.status, 'id', 'N/A')}\n"
                    )
            if len(results) > 20:
                output += f"\n...and {len(results) - 20} more."
            return output
    except Exception as e:
        logger.error(f"Failed to search work items with query '{query}': {e}")
        return f"❌ Failed to search work items: {e}"


@mcp.tool
async def get_test_runs(project_id: str) -> str:
    """Retrieves all test runs in the specified project."""
    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ) as driver:
            driver.select_project(project_id)
            test_runs = driver.get_test_runs()

            if not test_runs:
                return f"No test runs found in project '{project_id}'."

            output = f"Found {len(test_runs)} test runs in project '{project_id}':\n\n"
            for i, run in enumerate(test_runs[:20], 1):
                output += f"{i}. ID: {run.id}, Title: {getattr(run, 'title', 'N/A')}, Status: {getattr(run, 'status', 'N/A')}\n"

            if len(test_runs) > 20:
                output += f"\n...and {len(test_runs) - 20} more."
            return output
    except Exception as e:
        logger.error(f"Failed to get test runs: {e}")
        return f"❌ Failed to get test runs: {e}"


@mcp.tool
async def get_test_run(project_id: str, test_run_id: str) -> str:
    """Retrieves details of a specific test run."""
    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ) as driver:
            driver.select_project(project_id)
            test_run = driver.get_test_run(test_run_id)

            details = {
                "ID": test_run.id,
                "Title": getattr(test_run, "title", "N/A"),
                "Status": getattr(test_run, "status", "N/A"),
                "Created": str(getattr(test_run, "created", "N/A")),
                "Finished": str(getattr(test_run, "finished", "N/A")),
                "Test Cases": (
                    len(test_run.records) if hasattr(test_run, "records") else 0
                ),
            }

            output = f"Test Run Details for '{test_run_id}':\n"
            for key, value in details.items():
                output += f"- {key}: {value}\n"
            return output
    except Exception as e:
        logger.error(f"Failed to get test run '{test_run_id}': {e}")
        return f"❌ Failed to get test run: {e}"


@mcp.tool
async def get_documents(project_id: str) -> str:
    """Retrieves all documents in the specified project."""
    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ) as driver:
            driver.select_project(project_id)
            documents = driver.get_documents()

            if not documents:
                return f"No documents found in project '{project_id}'."

            output = f"Found {len(documents)} documents in project '{project_id}':\n\n"
            for i, doc in enumerate(documents[:20], 1):
                output += f"{i}. ID: {doc.id}, Title: {getattr(doc, 'title', 'N/A')}, Location: {getattr(doc, 'moduleFolder', 'N/A')}\n"

            if len(documents) > 20:
                output += f"\n...and {len(documents) - 20} more."
            return output
    except Exception as e:
        logger.error(f"Failed to get documents: {e}")
        return f"❌ Failed to get documents: {e}"


@mcp.tool
async def get_test_specs_from_document(project_id: str, document_id: str) -> str:
    """Extracts test specification IDs from a document."""
    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ) as driver:
            driver.select_project(project_id)

            # First get the document
            doc = driver.get_document(document_id)
            if not doc:
                return f"Document '{document_id}' not found in project '{project_id}'."

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
async def discover_work_item_types(project_id: str, limit: int = 20) -> str:
    """Samples work items to discover available types in the project."""
    try:
        with PolarionDriver(
            url=settings.polarion_url,
            user=settings.polarion_user,
            token=settings.polarion_token,
        ) as driver:
            driver.select_project(project_id)

            # Search for work items with type field
            results = driver.search_workitems("NOT type:null", ["id", "type"])

            # Collect unique types
            types_count: dict[str, int] = {}
            for item in results[:limit]:
                if isinstance(item, dict) and "type" in item:
                    type_value = item["type"]
                    types_count[type_value] = types_count.get(type_value, 0) + 1

            if not types_count:
                return f"Could not discover work item types in project '{project_id}'."

            output = f"Discovered work item types in project '{project_id}' (sampled {min(len(results), limit)} items):\n\n"
            for type_name, count in sorted(
                types_count.items(), key=lambda x: x[1], reverse=True
            ):
                output += f"- {type_name}: {count} occurrences\n"

            return output
    except Exception as e:
        logger.error(f"Failed to discover work item types: {e}")
        return f"❌ Failed to discover work item types: {e}"


# --- MCP Resources ---


@mcp.resource("polarion://project/{project_id}")
async def get_project_resource(project_id: str) -> str:
    """
    Access Polarion project as a resource.

    Args:
        project_id: The ID of the Polarion project

    Returns:
        Project information as a resource
    """
    return await get_project_info(project_id)  # type: ignore[operator]


# --- MCP Prompts ---


@mcp.prompt
async def analyze_project(project_id: str) -> str:
    """
    Generate a prompt to analyze a Polarion project.

    Args:
        project_id: The ID of the Polarion project

    Returns:
        A prompt asking to analyze the project
    """
    project_info = await get_project_info(project_id)  # type: ignore[operator]
    return (
        f"Please analyze this Polarion project and provide insights:\n\n{project_info}"
    )


@mcp.prompt
async def workitem_analysis(project_id: str, workitem_id: str) -> str:
    """
    Generate a prompt to analyze a specific work item.

    Args:
        project_id: The ID of the Polarion project
        workitem_id: The ID of the work item

    Returns:
        A prompt asking to analyze the work item
    """
    workitem_info = await get_workitem(project_id, workitem_id)  # type: ignore[operator]
    return f"Please analyze this Polarion work item and provide recommendations:\n\n{workitem_info}"
