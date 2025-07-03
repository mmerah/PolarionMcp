"""
Pydantic models for the MCP Server API responses.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WorkItemResponse(BaseModel):  # type: ignore[misc]
    id: str = Field(..., example="DTB-1234")
    title: str = Field(..., example="Example Work Item Title")
    type: str = Field(..., example="requirement")
    status: str = Field(..., example="approved")
    description: Optional[str] = Field(
        None, example="This is a detailed description of the work item."
    )
    custom_fields: Optional[Dict[str, Any]] = Field(
        None, example={"priority": "high", "risk": "low"}
    )


class ProjectResponse(BaseModel):  # type: ignore[misc]
    id: str = Field(..., example="MyProject")
    name: str = Field(..., example="My Project Name")
    description: Optional[str] = Field(None, example="Project description")


class TestRunResponse(BaseModel):  # type: ignore[misc]
    id: str = Field(..., example="TR-123")
    title: str = Field(..., example="Test Run Title")
    status: str = Field(..., example="open")
    type: str = Field(..., example="testrun")


class DocumentResponse(BaseModel):  # type: ignore[misc]
    id: str = Field(..., example="DOC-123")
    title: str = Field(..., example="Document Title")
    type: str = Field(..., example="testSpecificationsDocument")
    status: str = Field(..., example="draft")


class WorkItemListResponse(BaseModel):  # type: ignore[misc]
    items: List[WorkItemResponse] = Field(..., example=[])
    total: int = Field(..., example=0)
