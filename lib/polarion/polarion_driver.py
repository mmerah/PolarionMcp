"""
Polarion driver class - Read-only access to Polarion data
"""

import atexit
import logging
import os
from typing import Any, Dict, List, Optional

from polarion.document import Document
from polarion.polarion import Polarion


class PolarionDriver:
    """Polarion driver class - Read-only access to Polarion data"""

    def __init__(self, url: str) -> None:
        """Connect to Polarion server."""
        self.log = logging.getLogger(self.__class__.__name__)
        self._url = url
        self._polarion: Optional[Any] = None
        self._project: Optional[Any] = None
        self._user = os.environ.get("POLARION_USER")
        if not self._user:
            raise ValueError(
                "Polarion user name should not be None!\n"
                "Set the POLARION_USER environment variable."
            )
        self._token = os.environ.get("POLARION_TOKEN")
        if not self._token:
            raise ValueError(
                "Polarion token should not be None!\n"
                "Set the POLARION_TOKEN environment variable."
            )

    def __enter__(self) -> "PolarionDriver":
        """Setup Polarion connection and unregister Polarion cleanup."""
        assert (
            not self._polarion
        ), "Only one connection to Polarion server is supported!"
        try:
            self._polarion = Polarion(
                polarion_url=self._url, user=self._user, token=self._token
            )
        except Exception as err:
            if err.args[0] == "Cannot login because WSDL has no SessionWebService":
                raise Exception("Invalid polarion URL!")
            elif err.args[0] == f"Could not log in to Polarion for user {self._user}":
                raise Exception(
                    f"Invalid credentials for user '{self._user}'. Please check your token."
                )
            else:
                raise

        atexit.unregister(self._polarion._atexit_cleanup)
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Call Polarion cleanup to synchronize with main app."""
        assert self._polarion, "Expect a valid connection!"
        self._polarion._atexit_cleanup()

    def select_project(self, project_name: str) -> None:
        """Select Polarion project by name."""
        assert self._polarion, "There is no active connection to the Polarion server."
        self._project = self._polarion.getProject(project_name)

    def get_test_specs_doc(self, test_specs_doc_id: str) -> Optional[Document]:
        """
        Return test specifications document if exists

        @param test_specs_doc_id Polarion test specifications document id
        @return test spec document or None if not found
        """
        return self.__get_document_by_id(test_specs_doc_id)

    def test_spec_ids_in_doc(self, test_specs_doc: Document) -> set[str]:
        """
        Return set with test specification workitem IDs from a given test specification document

        1. Retrieve set with all test specifications in project
        2. Retrieve set with all woritem IDs in test specification document
        3. Return sets intersection

        @param test_specs_doc Polarion test specifications document object
        @return set with test specification IDs present in document
        """
        query = "type:verificationTest"
        test_specs_in_proj = self._project.searchWorkitem(  # type: ignore
            query=query, field_list=["id"]
        )
        test_spec_ids_in_proj = {wi["id"] for wi in test_specs_in_proj}
        wids_in_doc = {
            PolarionDriver.__workitem_id_from_uri(wi_uri)
            for wi_uri in test_specs_doc.getWorkitemUris()
        }
        test_spec_ids_in_doc = test_spec_ids_in_proj & wids_in_doc
        return test_spec_ids_in_doc

    def get_workitem(self, workitem_id: str) -> Any:
        """Get a workitem by ID."""
        assert (
            self._project
        ), "No active project! Please first select your desired project. Use `.select_project()`."
        return self._project.getWorkitem(workitem_id)

    def search_workitems(
        self, query: str, field_list: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search workitems with a query."""
        assert (
            self._project
        ), "No active project! Please first select your desired project. Use `.select_project()`."
        return self._project.searchWorkitem(query=query, field_list=field_list)  # type: ignore[no-any-return]

    def get_project_info(self) -> Dict[str, str]:
        """Get current project information."""
        assert (
            self._project
        ), "No active project! Please first select your desired project. Use `.select_project()`."
        return {
            "id": self._project.id,
            "name": self._project.name,
            "description": getattr(self._project, "description", ""),
        }

    def get_test_runs(self) -> List[Any]:
        """Get all test runs in the current project."""
        assert (
            self._project
        ), "No active project! Please first select your desired project. Use `.select_project()`."
        return self._project.getTestRuns()  # type: ignore[no-any-return]

    def get_documents(self) -> List[Any]:
        """Get all documents in the current project."""
        assert (
            self._project
        ), "No active project! Please first select your desired project. Use `.select_project()`."
        doc_spaces = self._project.getDocumentSpaces()
        documents = []
        for doc_space in doc_spaces:
            docs = self._project.getDocumentsInSpace(doc_space)
            documents.extend(docs)
        return documents

    def get_test_run(self, test_run_id: str) -> Any:
        """Get a test run by ID."""
        assert (
            self._project
        ), "No active project! Please first select your desired project. Use `.select_project()`."
        return self._project.getTestRun(test_run_id)

    def __get_document_by_id(self, doc_id: str) -> Optional[Document]:
        assert self._project, "No active project!"
        doc_spaces = self._project.getDocumentSpaces()
        for doc_space in doc_spaces:
            docs = self._project.getDocumentsInSpace(doc_space)
            for doc in docs:
                if doc.type["id"] == "testSpecificationsDocument" and doc.id == doc_id:
                    return doc
        return None

    @staticmethod
    def __workitem_id_from_uri(uri: str) -> Optional[str]:
        """
        Parse workitem id from URI.

        Extracts 'SNBL-3025' or similar from
        `subterra:data-service:objects:/default/SeNeBLESystem${WorkItem}SNBL-3025`

        @param uri URI of the workitem
        @return workitem id as string
        """
        from re import search

        match = search(r"\${WorkItem}(.+)$", uri)
        return match.group(1) if match else None
