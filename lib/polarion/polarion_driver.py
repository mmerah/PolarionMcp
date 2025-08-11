"""
Polarion driver class - A robust, read-only client for accessing Polarion data.
"""

# The atexit unregistering is a specific design choice to control session
# cleanup manually within the context manager.
import atexit
import logging
import re
from typing import Any, Dict, List, Optional, Set

from polarion.document import Document
from polarion.plan import Plan
from polarion.polarion import Polarion, Project
from polarion.testrun import Testrun
from polarion.user import User
from polarion.workitem import Workitem


class PolarionConnectionException(Exception):
    """Exception raised for issues related to the Polarion connection or API calls."""

    pass


class PolarionDriver:
    """
    A read-only driver for interacting with a Polarion server.

    This class provides a simplified, read-only interface to the `polarion` library,
    offering methods to fetch projects, documents, work items, test runs, and more.
    It is designed to be used as a context manager to ensure proper session handling.
    """

    def __init__(self, url: str, user: str, token: str) -> None:
        """
        Initializes the driver configuration. Connection is established in __enter__.

        Args:
            url: The base URL for the Polarion instance (e.g., "https://polarion.example.com").
            user: The username for authentication.
            token: The personal access token for authentication.

        Raises:
            ValueError: If user or token is not provided.
        """
        self.log = logging.getLogger(self.__class__.__name__)
        self._url = url
        self._user = user
        self._token = token
        self._polarion: Optional[Polarion] = None
        self._project: Optional[Project] = None

        if not self._user:
            raise ValueError("Polarion user name must be provided.")
        if not self._token:
            raise ValueError("Polarion token must be provided.")

    def __enter__(self) -> "PolarionDriver":
        """Establishes the connection to the Polarion server."""
        if self._polarion:
            raise PolarionConnectionException(
                "A Polarion connection is already active. This driver does not support nested connections."
            )

        try:
            self.log.info(
                f"Connecting to Polarion at {self._url} with user '{self._user}'."
            )
            self._polarion = Polarion(
                polarion_url=self._url, user=self._user, token=self._token
            )
            # Unregister the library's automatic exit handler.
            # We will manually control the session logout in __exit__.
            atexit.unregister(self._polarion._atexit_cleanup)
            self.log.info("Successfully connected to Polarion.")
        except Exception as err:
            # Intercept known error messages for more user-friendly exceptions.
            if "Cannot login because WSDL has no SessionWebService" in str(err):
                raise PolarionConnectionException(
                    f"Invalid Polarion URL or the server is unreachable: {self._url}"
                )
            elif f"Could not log in to Polarion for user {self._user}" in str(err):
                raise PolarionConnectionException(
                    f"Invalid credentials for user '{self._user}'. Please check your token."
                )
            else:
                raise PolarionConnectionException(
                    f"Failed to connect to Polarion: {err}"
                ) from err

        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Closes the connection to the Polarion server."""
        if self._polarion:
            self.log.info("Closing Polarion connection.")
            self._polarion._atexit_cleanup()
            self._polarion = None
            self._project = None

    def select_project(self, project_id: str) -> None:
        """
        Selects a Polarion project to work with.

        Args:
            project_id: The ID of the Polarion project.

        Raises:
            PolarionConnectionException: If the project is not found or if there is no active connection.
        """
        if not self._polarion:
            raise PolarionConnectionException(
                "No active connection to Polarion. Cannot select a project."
            )
        try:
            self.log.info(f"Selecting project '{project_id}'.")
            self._project = self._polarion.getProject(project_id)
            self.log.info(f"Successfully selected project '{self._project.name}'.")
        except Exception as e:
            raise PolarionConnectionException(
                f"Failed to select project '{project_id}': {e}"
            ) from e

    def get_project_info(self) -> Dict[str, str]:
        """
        Gets key information about the currently selected project.

        Returns:
            A dictionary containing project details like id, name, and description.
        """
        if not self._project:
            raise PolarionConnectionException(
                "No project selected. Use .select_project() first."
            )
        return {
            "id": self._project.id,
            "name": self._project.name,
            "description": getattr(self._project.polarion_data, "description", ""),
        }

    def get_document(self, doc_location: str) -> Optional[Document]:
        """
        Retrieves a document by its location.

        A document location is typically in the format "Space/DocumentID".

        Args:
            doc_location: The location of the document.

        Returns:
            The Document object if found, otherwise None.

        Raises:
            PolarionConnectionException: If no project is selected.
        """
        if not self._project:
            raise PolarionConnectionException(
                "No project selected. Use .select_project() first."
            )
        try:
            return self._project.getDocument(doc_location)
        except Exception:
            # The underlying library raises a generic exception if not found.
            self.log.warning(
                f"Document at location '{doc_location}' not found in project '{self._project.id}'."
            )
            return None

    def get_documents(self) -> List[Document]:
        """
        Retrieves all documents in the current project.

        Note: This can be a slow operation on projects with many document spaces.

        Returns:
            A list of all Document objects in the project.

        Raises:
            PolarionConnectionException: If no project is selected.
        """
        if not self._project:
            raise PolarionConnectionException(
                "No project selected. Use .select_project() first."
            )

        documents: List[Document] = []
        try:
            doc_spaces = self._project.getDocumentSpaces()
            for doc_space in doc_spaces:
                documents.extend(self._project.getDocumentsInSpace(doc_space))
        except Exception as e:
            raise PolarionConnectionException(
                f"Failed to retrieve documents: {e}"
            ) from e
        return documents

    def test_spec_ids_in_doc(self, test_specs_doc: Document) -> Set[str]:
        """
        Returns a set of test specification work item IDs from a given document.

        This method performs an efficient server-side query.

        Args:
            test_specs_doc: The Document object to search within.

        Returns:
            A set of work item IDs (e.g., {"PROJ-123", "PROJ-124"}).

        Raises:
            PolarionConnectionException: If the search query fails.
        """
        if not self._project:
            raise PolarionConnectionException(
                "No project selected. Use .select_project() first."
            )

        # Using a targeted query is much more efficient than client-side filtering.
        query = f'document.id:"{test_specs_doc.id}" AND type:testcase'
        try:
            workitems = self._project.searchWorkitem(query=query, field_list=["id"])
            return {wi["id"] for wi in workitems}
        except Exception as e:
            raise PolarionConnectionException(
                f"Failed to search for test specifications in document '{test_specs_doc.id}': {e}"
            ) from e

    def get_workitem(self, workitem_id: str) -> Workitem:
        """
        Retrieves a work item by its ID.

        Args:
            workitem_id: The ID of the work item (e.g., "PROJ-123").

        Returns:
            The Workitem object.

        Raises:
            PolarionConnectionException: If the work item is not found or the request fails.
        """
        if not self._project:
            raise PolarionConnectionException(
                "No project selected. Use .select_project() first."
            )
        try:
            return self._project.getWorkitem(workitem_id)
        except Exception as e:
            raise PolarionConnectionException(
                f"Failed to get work item '{workitem_id}': {e}"
            ) from e

    def get_workitem_by_uri(self, uri: str) -> Workitem:
        """
        Retrieves a work item by its full URI.

        Args:
            uri: The Subterra URI of the work item.

        Returns:
            The Workitem object.

        Raises:
            PolarionConnectionException: If the work item is not found or the request fails.
        """
        if not self._project:
            raise PolarionConnectionException(
                "No project selected. Use .select_project() first."
            )
        try:
            # The Workitem constructor can resolve from a URI directly.
            return Workitem(self._polarion, self._project, uri=uri)
        except Exception as e:
            raise PolarionConnectionException(
                f"Failed to get work item by URI '{uri}': {e}"
            ) from e

    def search_workitems(
        self, query: str, field_list: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Searches for work items using a Polarion Lucene query.

        Args:
            query: The Lucene query string.
            field_list: A list of fields to retrieve for each work item. Defaults to ["id"].

        Returns:
            A list of dictionaries, where each dictionary represents a work item.

        Raises:
            PolarionConnectionException: If the search query fails.
        """
        if not self._project:
            raise PolarionConnectionException(
                "No project selected. Use .select_project() first."
            )
        try:
            # Get results from Polarion (returns Zeep objects)
            results = self._project.searchWorkitem(query=query, field_list=field_list)

            # Convert Zeep objects to dictionaries
            from zeep.helpers import serialize_object

            serialized_results = []

            # If no field_list specified, use default
            actual_fields = field_list if field_list else ["id"]

            for item in results:
                # Serialize the full object
                full_dict = serialize_object(item)

                # Filter to only include requested fields
                filtered_dict = {}
                for field in actual_fields:
                    if field in full_dict:
                        filtered_dict[field] = full_dict[field]

                serialized_results.append(filtered_dict)

            return serialized_results
        except Exception as e:
            raise PolarionConnectionException(
                f"Failed to search work items with query '{query}': {e}"
            ) from e

    def get_test_run(self, test_run_id: str) -> Testrun:
        """
        Retrieves a test run by its ID.

        Args:
            test_run_id: The ID of the test run.

        Returns:
            The Testrun object.

        Raises:
            PolarionConnectionException: If the test run is not found or the request fails.
        """
        if not self._project:
            raise PolarionConnectionException(
                "No project selected. Use .select_project() first."
            )
        try:
            return self._project.getTestRun(test_run_id)
        except Exception as e:
            raise PolarionConnectionException(
                f"Failed to get test run '{test_run_id}': {e}"
            ) from e

    def get_test_runs(self, query: str = "") -> List[Testrun]:
        """
        Retrieves all test runs in the current project, optionally filtered by a query.

        Args:
            query: An optional Lucene query to filter the test runs.

        Returns:
            A list of Testrun objects.

        Raises:
            PolarionConnectionException: If the search fails.
        """
        if not self._project:
            raise PolarionConnectionException(
                "No project selected. Use .select_project() first."
            )
        try:
            result = self._project.searchTestRuns(query=query)
            return result if result else []
        except Exception as e:
            raise PolarionConnectionException(
                f"Failed to get test runs with query '{query}': {e}"
            ) from e

    def get_plan(self, plan_id: str) -> Plan:
        """
        Retrieves a plan by its ID.

        Args:
            plan_id: The ID of the plan.

        Returns:
            The Plan object.

        Raises:
            PolarionConnectionException: If the plan is not found or the request fails.
        """
        if not self._project:
            raise PolarionConnectionException(
                "No project selected. Use .select_project() first."
            )
        try:
            return self._project.getPlan(plan_id)
        except Exception as e:
            raise PolarionConnectionException(
                f"Failed to get plan '{plan_id}': {e}"
            ) from e

    def search_plans(self, query: str = "") -> List[Plan]:
        """
        Searches for plans using a Polarion Lucene query.

        Args:
            query: The Lucene query string. If empty, returns all plans.

        Returns:
            A list of Plan objects matching the query.

        Raises:
            PolarionConnectionException: If the search fails.
        """
        if not self._project:
            raise PolarionConnectionException(
                "No project selected. Use .select_project() first."
            )
        try:
            # The Polarion library's searchPlan method appends "AND project.id:{id}" to the query
            # and the service also adds "AND NOT HAS_VALUE:isTemplate"
            # So we need to ensure the query doesn't start empty which would create invalid syntax
            if not query or query.strip() == "":
                # Use "NOT HAS_VALUE:dummy" as a always-true condition to get all plans
                # This creates valid syntax when ANDed with other conditions
                query = "NOT HAS_VALUE:dummyFieldThatDoesNotExist"
            return self._project.searchPlanFullItem(query=query)
        except Exception as e:
            raise PolarionConnectionException(
                f"Failed to search for plans with query '{query}': {e}"
            ) from e

    def get_user(self, user_id_or_name: str) -> Optional[User]:
        """
        Finds a specific user in the project by their ID or full name.

        Args:
            user_id_or_name: The user's ID or name to search for.

        Returns:
            The User object if found, otherwise None.

        Raises:
            PolarionConnectionException: If the request fails.
        """
        if not self._project:
            raise PolarionConnectionException(
                "No project selected. Use .select_project() first."
            )
        try:
            return self._project.findUser(user_id_or_name)
        except Exception as e:
            raise PolarionConnectionException(
                f"Failed to find user '{user_id_or_name}': {e}"
            ) from e

    def get_users(self) -> List[User]:
        """
        Retrieves all users associated with the current project.

        Returns:
            A list of User objects.

        Raises:
            PolarionConnectionException: If the request fails.
        """
        if not self._project:
            raise PolarionConnectionException(
                "No project selected. Use .select_project() first."
            )
        try:
            return self._project.getUsers()
        except Exception as e:
            raise PolarionConnectionException(
                f"Failed to get users for project '{self._project.id}': {e}"
            ) from e

    @staticmethod
    def workitem_id_from_uri(uri: str) -> Optional[str]:
        """
        Parses a work item ID from its Subterra URI.

        Example:
            Extracts 'PROJ-123' from
            'subterra:data-service:objects:/default/MyProject${WorkItem}PROJ-123'

        Args:
            uri: The Subterra URI of the work item.

        Returns:
            The work item ID as a string, or None if the pattern is not found.
        """
        match = re.search(r"\${WorkItem}(.+)$", uri)
        return match.group(1) if match else None
