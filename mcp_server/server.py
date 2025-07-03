"""Polarion MCP Server - stdio implementation."""

import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError
from mcp.types import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    ErrorData,
    TextContent,
    Tool,
)
from pydantic import BaseModel, Field

from lib.polarion.polarion_driver import PolarionDriver


class PolarionSettings:
    """Settings for Polarion connection."""

    def __init__(self, load_dotenv_file: bool = True):
        # Load .env file if it exists and not disabled (for testing)
        if load_dotenv_file:
            self._load_env_file()

        self.polarion_url = os.getenv("POLARION_URL")
        self.polarion_user = os.getenv("POLARION_USER")
        self.polarion_token = os.getenv("POLARION_TOKEN")

        if not self.polarion_url:
            raise ValueError("POLARION_URL environment variable is required")
        if not self.polarion_user:
            raise ValueError("POLARION_USER environment variable is required")
        if not self.polarion_token:
            raise ValueError("POLARION_TOKEN environment variable is required")

    def _load_env_file(self):
        """Load environment variables from .env file if it exists."""
        # Load .env file from current working directory
        load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)


# Tool parameter models
class ProjectInfoParams(BaseModel):
    """Parameters for get_project_info tool."""

    project_id: str = Field(..., description="The ID of the Polarion project")


class WorkItemParams(BaseModel):
    """Parameters for get_workitem tool."""

    project_id: str = Field(..., description="The ID of the Polarion project")
    workitem_id: str = Field(..., description="The ID of the work item to retrieve")


class SearchWorkItemsParams(BaseModel):
    """Parameters for search_workitems tool."""

    project_id: str = Field(..., description="The ID of the Polarion project")
    query: str = Field(..., description="Lucene query string for searching work items")
    field_list: Optional[List[str]] = Field(
        None, description="Optional list of fields to return"
    )


class TestRunParams(BaseModel):
    """Parameters for get_test_run tool."""

    project_id: str = Field(..., description="The ID of the Polarion project")
    test_run_id: str = Field(..., description="The ID of the test run to retrieve")


class TestRunsParams(BaseModel):
    """Parameters for get_test_runs tool."""

    project_id: str = Field(..., description="The ID of the Polarion project")


class DocumentsParams(BaseModel):
    """Parameters for get_documents tool."""

    project_id: str = Field(..., description="The ID of the Polarion project")


class TestSpecsFromDocumentParams(BaseModel):
    """Parameters for get_test_specs_from_document tool."""

    project_id: str = Field(..., description="The ID of the Polarion project")
    document_id: str = Field(
        ..., description="The ID of the document to get test specs from"
    )


class HealthCheckParams(BaseModel):
    """Parameters for health_check tool."""

    pass


class DiscoverTypesParams(BaseModel):
    """Parameters for discover_work_item_types tool."""

    project_id: str = Field(..., description="The ID of the Polarion project")
    limit: Optional[int] = Field(
        20, description="Maximum number of work items to sample"
    )


async def serve() -> None:
    """Run the Polarion MCP server."""
    settings = PolarionSettings()
    server = Server("mcp-polarion")

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return [
            Tool(
                name="get_project_info",
                description="Get information about a Polarion project",
                inputSchema=ProjectInfoParams.model_json_schema(),
            ),
            Tool(
                name="get_workitem",
                description="Get a specific work item from a Polarion project",
                inputSchema=WorkItemParams.model_json_schema(),
            ),
            Tool(
                name="search_workitems",
                description="Search for work items in a Polarion project using Lucene query syntax",
                inputSchema=SearchWorkItemsParams.model_json_schema(),
            ),
            Tool(
                name="get_test_runs",
                description="Get all test runs from a Polarion project",
                inputSchema=TestRunsParams.model_json_schema(),
            ),
            Tool(
                name="get_test_run",
                description="Get a specific test run from a Polarion project",
                inputSchema=TestRunParams.model_json_schema(),
            ),
            Tool(
                name="get_documents",
                description="Get all documents from a Polarion project",
                inputSchema=DocumentsParams.model_json_schema(),
            ),
            Tool(
                name="get_test_specs_from_document",
                description="Get test specifications from a specific document in a Polarion project",
                inputSchema=TestSpecsFromDocumentParams.model_json_schema(),
            ),
            Tool(
                name="health_check",
                description="Check the health of the Polarion connection",
                inputSchema=HealthCheckParams.model_json_schema(),
            ),
            Tool(
                name="discover_work_item_types",
                description="Discover what work item types exist in a Polarion project by sampling work items",
                inputSchema=DiscoverTypesParams.model_json_schema(),
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> List[TextContent]:
        """Handle tool calls."""
        try:
            if name == "health_check":
                return await _handle_health_check(arguments, settings)
            elif name == "get_project_info":
                return await _handle_get_project_info(arguments, settings)
            elif name == "get_workitem":
                return await _handle_get_workitem(arguments, settings)
            elif name == "search_workitems":
                return await _handle_search_workitems(arguments, settings)
            elif name == "get_test_runs":
                return await _handle_get_test_runs(arguments, settings)
            elif name == "get_test_run":
                return await _handle_get_test_run(arguments, settings)
            elif name == "get_documents":
                return await _handle_get_documents(arguments, settings)
            elif name == "get_test_specs_from_document":
                return await _handle_get_test_specs_from_document(arguments, settings)
            elif name == "discover_work_item_types":
                return await _handle_discover_work_item_types(arguments, settings)
            else:
                raise McpError(
                    ErrorData(code=INVALID_PARAMS, message=f"Unknown tool: {name}")
                )
        except McpError:
            raise
        except Exception as e:
            raise McpError(
                ErrorData(code=INTERNAL_ERROR, message=f"Internal error: {str(e)}")
            )

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)


async def _handle_health_check(
    arguments: dict, settings: PolarionSettings
) -> List[TextContent]:
    """Handle health check."""
    try:
        HealthCheckParams(**arguments)

        # Try to connect to Polarion
        with PolarionDriver(
            settings.polarion_url, settings.polarion_user, settings.polarion_token
        ):
            status = "healthy"
            message = "Successfully connected to Polarion server"

        result = {
            "status": status,
            "polarion_url": settings.polarion_url,
            "polarion_user": settings.polarion_user,
            "message": message,
        }

        return [TextContent(type="text", text=f"Health check result: {result}")]
    except Exception as e:
        result = {
            "status": "unhealthy",
            "polarion_url": settings.polarion_url,
            "polarion_user": settings.polarion_user,
            "message": "Failed to connect to Polarion server",
            "error": str(e),
        }
        return [TextContent(type="text", text=f"Health check result: {result}")]


async def _handle_get_project_info(
    arguments: dict, settings: PolarionSettings
) -> List[TextContent]:
    """Handle get project info."""
    try:
        params = ProjectInfoParams(**arguments)

        with PolarionDriver(
            settings.polarion_url, settings.polarion_user, settings.polarion_token
        ) as driver:
            driver.select_project(params.project_id)
            project_info = driver.get_project_info()

        return [TextContent(type="text", text=f"Project info: {project_info}")]
    except Exception as e:
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR, message=f"Failed to get project info: {str(e)}"
            )
        )


async def _handle_get_workitem(
    arguments: dict, settings: PolarionSettings
) -> List[TextContent]:
    """Handle get workitem."""
    try:
        params = WorkItemParams(**arguments)

        with PolarionDriver(
            settings.polarion_url, settings.polarion_user, settings.polarion_token
        ) as driver:
            driver.select_project(params.project_id)
            workitem = driver.get_workitem(params.workitem_id)

            # Convert workitem to dict representation
            workitem_dict = {
                "id": workitem.id,
                "title": getattr(workitem, "title", ""),
                "description": getattr(workitem, "description", ""),
                "type": getattr(workitem, "type", ""),
                "status": getattr(workitem, "status", ""),
                "author": getattr(workitem, "author", ""),
                "created": str(getattr(workitem, "created", "")),
                "updated": str(getattr(workitem, "updated", "")),
            }

        return [TextContent(type="text", text=f"Work item: {workitem_dict}")]
    except Exception as e:
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message=f"Failed to get work item: {str(e)}")
        )


async def _handle_search_workitems(
    arguments: dict, settings: PolarionSettings
) -> List[TextContent]:
    """Handle search workitems."""
    try:
        params = SearchWorkItemsParams(**arguments)

        with PolarionDriver(
            settings.polarion_url, settings.polarion_user, settings.polarion_token
        ) as driver:
            driver.select_project(params.project_id)
            results = driver.search_workitems(params.query, params.field_list)

        return [TextContent(type="text", text=f"Search results: {results}")]
    except Exception as e:
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR, message=f"Failed to search work items: {str(e)}"
            )
        )


async def _handle_get_test_runs(
    arguments: dict, settings: PolarionSettings
) -> List[TextContent]:
    """Handle get test runs."""
    try:
        params = TestRunsParams(**arguments)

        with PolarionDriver(
            settings.polarion_url, settings.polarion_user, settings.polarion_token
        ) as driver:
            driver.select_project(params.project_id)
            test_runs = driver.get_test_runs()

        return [TextContent(type="text", text=f"Test runs: {test_runs}")]
    except Exception as e:
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message=f"Failed to get test runs: {str(e)}")
        )


async def _handle_get_test_run(
    arguments: dict, settings: PolarionSettings
) -> List[TextContent]:
    """Handle get test run."""
    try:
        params = TestRunParams(**arguments)

        with PolarionDriver(
            settings.polarion_url, settings.polarion_user, settings.polarion_token
        ) as driver:
            driver.select_project(params.project_id)
            test_run = driver.get_test_run(params.test_run_id)

            if test_run is None:
                return [
                    TextContent(
                        type="text", text=f"Test run {params.test_run_id} not found"
                    )
                ]

            # Convert test run to dict representation
            test_run_dict = {
                "id": test_run.id,
                "title": getattr(test_run, "title", ""),
                "status": getattr(test_run, "status", ""),
                "created": str(getattr(test_run, "created", "")),
                "updated": str(getattr(test_run, "updated", "")),
                "description": getattr(test_run, "description", ""),
            }

        return [TextContent(type="text", text=f"Test run: {test_run_dict}")]
    except Exception as e:
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message=f"Failed to get test run: {str(e)}")
        )


async def _handle_get_documents(
    arguments: dict, settings: PolarionSettings
) -> List[TextContent]:
    """Handle get documents."""
    try:
        params = DocumentsParams(**arguments)

        with PolarionDriver(
            settings.polarion_url, settings.polarion_user, settings.polarion_token
        ) as driver:
            driver.select_project(params.project_id)
            documents = driver.get_documents()

            # Convert documents to dict representation
            documents_list = []
            for doc in documents:
                doc_dict = {
                    "id": doc.id,
                    "title": getattr(doc, "title", ""),
                    "type": getattr(doc, "type", ""),
                    "created": str(getattr(doc, "created", "")),
                    "updated": str(getattr(doc, "updated", "")),
                }
                documents_list.append(doc_dict)

        return [TextContent(type="text", text=f"Documents: {documents_list}")]
    except Exception as e:
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message=f"Failed to get documents: {str(e)}")
        )


async def _handle_get_test_specs_from_document(
    arguments: dict, settings: PolarionSettings
) -> List[TextContent]:
    """Handle get test specs from document."""
    try:
        params = TestSpecsFromDocumentParams(**arguments)

        with PolarionDriver(
            settings.polarion_url, settings.polarion_user, settings.polarion_token
        ) as driver:
            driver.select_project(params.project_id)
            test_specs_doc = driver.get_test_specs_doc(params.document_id)

            if test_specs_doc is None:
                return [
                    TextContent(
                        type="text", text=f"Document {params.document_id} not found"
                    )
                ]

            test_spec_ids = driver.test_spec_ids_in_doc(test_specs_doc)

        return [
            TextContent(
                type="text",
                text=f"Test specification IDs in document: {list(test_spec_ids)}",
            )
        ]
    except Exception as e:
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to get test specs from document: {str(e)}",
            )
        )


async def _handle_discover_work_item_types(
    arguments: dict, settings: PolarionSettings
) -> List[TextContent]:
    """Handle discover work item types."""
    try:
        params = DiscoverTypesParams(**arguments)

        with PolarionDriver(
            settings.polarion_url, settings.polarion_user, settings.polarion_token
        ) as driver:
            driver.select_project(params.project_id)

            # Search for work items using common types (since wildcards don't work)
            results = []
            found_types = set()
            common_types = [
                "requirement",
                "testcase",
                "defect",
                "task",
                "epic",
                "story",
                "testrun",
                "execution",
                "test",
                "issue",
                "bug",
            ]

            for work_type in common_types:
                try:
                    # Search without field_list to get full objects, then limit the results
                    type_results = driver.search_workitems(f"type:{work_type}")
                    if type_results:
                        found_types.add(work_type)
                        # Take a few examples from each type
                        results.extend(type_results[:3])
                        if len(results) >= params.limit:
                            break
                except Exception:
                    continue

            # Limit the results
            if len(results) > params.limit:
                results = results[: params.limit]

            if not results:
                return [
                    TextContent(
                        type="text",
                        text=f"❌ No work items found in project '{params.project_id}'. The project might be empty or you might not have access to it.",
                    )
                ]

            # Use the found types from our search instead of parsing individual items
            if found_types:
                result_text = (
                    f"✅ Work item types found in project '{params.project_id}':\n\n"
                )

                for work_type in sorted(found_types):
                    # Find an example of this type
                    example_item = None
                    for item in results:
                        if hasattr(item, "uri") and work_type in str(
                            getattr(item, "uri", "")
                        ):
                            example_item = item
                            break

                    result_text += f"• **{work_type}**\n"
                    if example_item:
                        item_id = getattr(example_item, "id", "unknown")
                        result_text += f"  Example: {item_id}\n\n"
                    else:
                        result_text += "  (Found items of this type)\n\n"

                result_text += f"\nTotal types found: {len(found_types)}\n"
                result_text += f"Sampled from {len(results)} work items\n\n"
                result_text += "💡 **Tip**: Use the type name you want in search_workitems with 'type:typename' query\n"
                result_text += "🔧 **For test runs**: Try using search_workitems with queries like:\n"
                result_text += "   - 'type:testcase'\n"
                result_text += "   - 'type:execution'\n"
                result_text += "   - 'type:testrun'\n"
                result_text += "   - Or use one of the types listed above"
            else:
                result_text = (
                    f"❌ No work item types found in project '{params.project_id}'"
                )

        return [TextContent(type="text", text=result_text)]
    except Exception as e:
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to discover work item types: {str(e)}",
            )
        )
