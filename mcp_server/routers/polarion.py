"""
API router for Polarion-related endpoints.
"""

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from lib.polarion.polarion_driver import PolarionDriver

from .. import models
from ..auth import get_api_key
from ..config import settings

router = APIRouter(
    prefix="/polarion",
    tags=["Polarion"],
    dependencies=[Depends(get_api_key)],
    responses={401: {"description": "Unauthorized"}},
)


@router.get(
    "/projects/{project_id}/workitems/{workitem_id}",
    response_model=models.WorkItemResponse,
)
def get_workitem_by_id(
    project_id: Annotated[
        str, Path(example="DeviceTestBench", description="The Polarion Project ID.")
    ],
    workitem_id: Annotated[
        str, Path(example="DTB-1234", description="The Work Item ID.")
    ],
) -> models.WorkItemResponse:
    """
    Fetches a specific work item from a Polarion project by its ID.

    This endpoint demonstrates how to use the existing `PolarionDriver` to interact
    with the Polarion server. It requires `POLARION_USER` and `POLARION_TOKEN`
    to be set in the environment for the driver to connect.
    """
    try:
        with PolarionDriver(settings.POLARION_URL) as polarion:
            polarion.select_project(project_id)
            # The python-polarion library's getWorkitem can be slow if it has to search.
            # We assume the project is already selected.
            workitem = polarion.get_workitem(workitem_id)

            if not workitem:
                raise HTTPException(
                    status_code=404,
                    detail=f"Work Item '{workitem_id}' not found in project '{project_id}'.",
                )

            # The workitem object is complex; we map it to our Pydantic model for a clean API response.
            response = models.WorkItemResponse(
                id=workitem.id,
                title=workitem.title,
                type=workitem.type.id,
                status=workitem.status.id,
                description=(
                    workitem.description.content if workitem.description else None
                ),
                # A simplified representation of custom fields
                custom_fields={
                    field.key: (
                        field.value.id if hasattr(field.value, "id") else field.value
                    )
                    for field in workitem.customFields["Custom"]
                },
            )
            return response

    except ValueError as e:
        # Catches errors from PolarionDriver like missing env vars
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # Catches other errors, e.g., project not found from polarion library
        if "Project not found" in str(e):
            raise HTTPException(
                status_code=404, detail=f"Project '{project_id}' not found."
            )
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/projects/{project_id}/info", response_model=models.ProjectResponse)
def get_project_info(
    project_id: Annotated[
        str, Path(example="MyProject", description="The Polarion Project ID.")
    ]
) -> models.ProjectResponse:
    """
    Get information about a specific Polarion project.
    """
    try:
        with PolarionDriver(settings.POLARION_URL) as polarion:
            polarion.select_project(project_id)
            project_info = polarion.get_project_info()
            return models.ProjectResponse(**project_info)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        if "Project not found" in str(e):
            raise HTTPException(
                status_code=404, detail=f"Project '{project_id}' not found."
            )
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get(
    "/projects/{project_id}/workitems", response_model=models.WorkItemListResponse
)
def search_workitems(
    project_id: Annotated[
        str, Path(example="MyProject", description="The Polarion Project ID.")
    ],
    query: Annotated[
        str, Query(example="type:requirement", description="Polarion query string")
    ],
    fields: Annotated[
        Optional[List[str]],
        Query(
            example=["id", "title", "type"],
            description="Fields to include in response",
        ),
    ] = None,
) -> models.WorkItemListResponse:
    """
    Search for work items in a Polarion project using a query string.
    """
    try:
        with PolarionDriver(settings.POLARION_URL) as polarion:
            polarion.select_project(project_id)
            workitems = polarion.search_workitems(query, field_list=fields)

            items = []
            for wi in workitems:
                # Create a simplified workitem response
                item = models.WorkItemResponse(
                    id=wi.get("id", ""),
                    title=wi.get("title", ""),
                    type=(
                        wi.get("type", {}).get("id", "")
                        if isinstance(wi.get("type"), dict)
                        else wi.get("type", "")
                    ),
                    status=(
                        wi.get("status", {}).get("id", "")
                        if isinstance(wi.get("status"), dict)
                        else wi.get("status", "")
                    ),
                    description=(
                        wi.get("description", {}).get("content", "")
                        if isinstance(wi.get("description"), dict)
                        else wi.get("description", "")
                    ),
                    custom_fields={},
                )
                items.append(item)

            return models.WorkItemListResponse(items=items, total=len(items))
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        if "Project not found" in str(e):
            raise HTTPException(
                status_code=404, detail=f"Project '{project_id}' not found."
            )
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get(
    "/projects/{project_id}/testruns", response_model=List[models.TestRunResponse]
)
def get_test_runs(
    project_id: Annotated[
        str, Path(example="MyProject", description="The Polarion Project ID.")
    ]
) -> List[models.TestRunResponse]:
    """
    Get all test runs in a Polarion project.
    """
    try:
        with PolarionDriver(settings.POLARION_URL) as polarion:
            polarion.select_project(project_id)
            test_runs = polarion.get_test_runs()

            response = []
            for tr in test_runs:
                response.append(
                    models.TestRunResponse(
                        id=tr.id,
                        title=tr.title,
                        status=(
                            tr.status.id if hasattr(tr.status, "id") else str(tr.status)
                        ),
                        type=tr.type.id if hasattr(tr.type, "id") else str(tr.type),
                    )
                )

            return response
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        if "Project not found" in str(e):
            raise HTTPException(
                status_code=404, detail=f"Project '{project_id}' not found."
            )
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get(
    "/projects/{project_id}/testruns/{testrun_id}",
    response_model=models.TestRunResponse,
)
def get_test_run(
    project_id: Annotated[
        str, Path(example="MyProject", description="The Polarion Project ID.")
    ],
    testrun_id: Annotated[str, Path(example="TR-123", description="The Test Run ID.")],
) -> models.TestRunResponse:
    """
    Get a specific test run by ID.
    """
    try:
        with PolarionDriver(settings.POLARION_URL) as polarion:
            polarion.select_project(project_id)
            test_run = polarion.get_test_run(testrun_id)

            if not test_run:
                raise HTTPException(
                    status_code=404,
                    detail=f"Test Run '{testrun_id}' not found in project '{project_id}'.",
                )

            return models.TestRunResponse(
                id=test_run.id,
                title=test_run.title,
                status=(
                    test_run.status.id
                    if hasattr(test_run.status, "id")
                    else str(test_run.status)
                ),
                type=(
                    test_run.type.id
                    if hasattr(test_run.type, "id")
                    else str(test_run.type)
                ),
            )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        if "Project not found" in str(e):
            raise HTTPException(
                status_code=404, detail=f"Project '{project_id}' not found."
            )
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get(
    "/projects/{project_id}/documents", response_model=List[models.DocumentResponse]
)
def get_documents(
    project_id: Annotated[
        str, Path(example="MyProject", description="The Polarion Project ID.")
    ]
) -> List[models.DocumentResponse]:
    """
    Get all documents in a Polarion project.
    """
    try:
        with PolarionDriver(settings.POLARION_URL) as polarion:
            polarion.select_project(project_id)
            documents = polarion.get_documents()

            response = []
            for doc in documents:
                response.append(
                    models.DocumentResponse(
                        id=doc.id,
                        title=doc.title,
                        type=doc.type.id if hasattr(doc.type, "id") else str(doc.type),
                        status=(
                            doc.status.id
                            if hasattr(doc.status, "id")
                            else str(doc.status)
                        ),
                    )
                )

            return response
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        if "Project not found" in str(e):
            raise HTTPException(
                status_code=404, detail=f"Project '{project_id}' not found."
            )
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get(
    "/projects/{project_id}/documents/{document_id}",
    response_model=models.DocumentResponse,
)
def get_document(
    project_id: Annotated[
        str, Path(example="MyProject", description="The Polarion Project ID.")
    ],
    document_id: Annotated[
        str, Path(example="DOC-123", description="The Document ID.")
    ],
) -> models.DocumentResponse:
    """
    Get a specific document by ID.
    """
    try:
        with PolarionDriver(settings.POLARION_URL) as polarion:
            polarion.select_project(project_id)
            document = polarion.get_test_specs_doc(document_id)

            if not document:
                raise HTTPException(
                    status_code=404,
                    detail=f"Document '{document_id}' not found in project '{project_id}'.",
                )

            return models.DocumentResponse(
                id=document.id,
                title=document.title,
                type=(
                    document.type.id
                    if hasattr(document.type, "id")
                    else str(document.type)
                ),
                status=(
                    document.status.id
                    if hasattr(document.status, "id")
                    else str(document.status)
                ),
            )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        if "Project not found" in str(e):
            raise HTTPException(
                status_code=404, detail=f"Project '{project_id}' not found."
            )
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )
