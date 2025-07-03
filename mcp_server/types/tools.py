"""Tool-specific types and models for Polarion MCP server."""

from enum import Enum
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class ToolName(str, Enum):
    """Available tool names."""
    GET_PROJECT_INFO = "get_project_info"
    GET_WORKITEM = "get_workitem"
    SEARCH_WORKITEMS = "search_workitems"
    GET_TEST_RUNS = "get_test_runs"
    GET_TEST_RUN = "get_test_run"
    GET_DOCUMENTS = "get_documents"
    HEALTH_CHECK = "health_check"


# Tool Parameter Models
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
    field_list: Optional[List[str]] = Field(None, description="Optional list of fields to return")


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


class HealthCheckParams(BaseModel):
    """Parameters for health_check tool."""
    pass


# Tool Response Models
class ToolContentItem(BaseModel):
    """Content item for tool responses."""
    type: Literal["text"] = "text"
    text: str


class ToolResponse(BaseModel):
    """Standard tool response model."""
    content: List[ToolContentItem]
    isError: bool = False


class WorkItemResult(BaseModel):
    """Result model for work item data."""
    id: str
    title: str
    description: str
    type: str
    status: str
    author: str
    created: str
    updated: str


class TestRunResult(BaseModel):
    """Result model for test run data."""
    id: str
    title: str
    status: str
    created: str
    updated: str
    description: Optional[str] = None


class DocumentResult(BaseModel):
    """Result model for document data."""
    id: str
    title: str
    type: str
    created: str
    updated: str


class HealthCheckResult(BaseModel):
    """Result model for health check."""
    status: Literal["healthy", "unhealthy"]
    polarion_url: Optional[str] = None
    polarion_user: Optional[str] = None
    message: str
    error: Optional[str] = None