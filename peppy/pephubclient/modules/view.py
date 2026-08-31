import logging
from urllib.parse import quote

# import peppy
from ...project import Project
from ..constants import (
    PEPHUB_BASE_URL,
    PEPHUB_VIEW_PATH,
    PEPHUB_VIEW_SAMPLE_PATH,
    ResponseStatusCodes,
)
from ..exceptions import ResponseError
from ..helpers import RequestManager
from ..models import ProjectDict

_LOGGER = logging.getLogger("pephubclient")


class PEPHubView(RequestManager):
    """
    Class for managing views in PEPhub.

    Provides methods for getting, creating, updating and removing views.
    This class aims to wrap the Views API for easier maintenance and
    better user experience.
    """

    def __init__(self, jwt_data: str = None, base_url: str = None):
        """
        Initialize PEPHubView.

        Args:
            jwt_data: jwt token for authorization
            base_url: base URL of the PEPhub instance to talk to
        """

        self.__jwt_data = jwt_data
        self.__base_url = (base_url or PEPHUB_BASE_URL).rstrip("/") + "/"

    def get(
        self, namespace: str, name: str, tag: str, view_name: str, raw: bool = False
    ) -> Project | dict:
        """
        Get view from project in PEPhub.

        Args:
            namespace: namespace of project
            name: name of project
            tag: tag of project
            view_name: name of the view
            raw: if True, return raw response

        Returns:
            peppy.Project object or dictionary of the project (view).
        """
        url = self._build_view_request_url(
            namespace=namespace, name=name, view_name=view_name
        )

        url = url + self.parse_query_param(pep_variables={"tag": tag})

        response = self.send_request(
            method="GET", url=url, headers=self.parse_header(self.__jwt_data)
        )
        if response.status_code == ResponseStatusCodes.OK:
            output = self.decode_response(response, output_json=True)
            if raw:
                return output
            output = ProjectDict(**output).model_dump(by_alias=True)
            return Project.from_dict(output)
        elif response.status_code == ResponseStatusCodes.NOT_EXIST:
            raise ResponseError("View does not exist, or you are unauthorized.")
        else:
            raise ResponseError(
                f"Internal server error. Unexpected return value. Error: {response.status_code}"
            )

    def create(
        self,
        namespace: str,
        name: str,
        tag: str,
        view_name: str,
        description: str = None,
        sample_list: list = None,
        no_fail: bool = False,
    ):
        """
        Create view in project in PEPhub.

        Args:
            namespace: namespace of project
            name: name of project
            tag: tag of project
            description: description of the view
            view_name: name of the view
            sample_list: list of sample names
            no_fail: whether to raise an error if view was not added to the
                project
        """

        if not sample_list or not isinstance(sample_list, list):
            raise ValueError("Sample list must be a list of sample names.")

        url = self._build_view_request_url(
            namespace=namespace, name=name, view_name=view_name
        )

        url = url + self.parse_query_param(pep_variables={"tag": tag})

        response = self.send_request(
            method="POST",
            url=url,
            headers=self.parse_header(self.__jwt_data),
            params={"description": description, "no_fail": no_fail},
            json=sample_list,
        )
        if response.status_code == ResponseStatusCodes.ACCEPTED:
            _LOGGER.info(
                f"View '{view_name}' created in project '{namespace}/{name}:{tag}' successfully."
            )
            return None
        elif response.status_code == ResponseStatusCodes.NOT_EXIST:
            raise ResponseError(
                f"Project '{namespace}/{name}:{tag}' or one of the samples does not exist."
            )
        elif response.status_code == ResponseStatusCodes.CONFLICT:
            raise ResponseError(f"View '{view_name}' already exists in the project.")
        else:
            raise ResponseError(f"Unexpected return value.{response.status_code}")

    def delete(self, namespace: str, name: str, tag: str, view_name: str) -> None:
        """
        Delete view from project in PEPhub.

        Args:
            namespace: namespace of project
            name: name of project
            tag: tag of project
            view_name: name of the view
        """
        url = self._build_view_request_url(
            namespace=namespace, name=name, view_name=view_name
        )

        url = url + self.parse_query_param(pep_variables={"tag": tag})

        response = self.send_request(
            method="DELETE", url=url, headers=self.parse_header(self.__jwt_data)
        )

        if response.status_code == ResponseStatusCodes.ACCEPTED:
            _LOGGER.info(
                f"View '{view_name}' deleted from project '{namespace}/{name}:{tag}' successfully."
            )
            return None
        elif response.status_code == ResponseStatusCodes.NOT_EXIST:
            raise ResponseError("View does not exists, or you are unauthorized.")
        elif response.status_code == ResponseStatusCodes.UNAUTHORIZED:
            raise ResponseError("You are unauthorized to delete this view.")
        else:
            raise ResponseError("Unexpected return value. ")

    def add_sample(
        self,
        namespace: str,
        name: str,
        tag: str,
        view_name: str,
        sample_name: str,
    ):
        """
        Add sample to view in project in PEPhub.

        Args:
            namespace: namespace of project
            name: name of project
            tag: tag of project
            view_name: name of the view
            sample_name: name of the sample
        """
        url = self._build_view_request_url(
            namespace=namespace,
            name=name,
            view_name=view_name,
            sample_name=sample_name,
        )

        url = url + self.parse_query_param(pep_variables={"tag": tag})

        response = self.send_request(
            method="POST",
            url=url,
            headers=self.parse_header(self.__jwt_data),
        )
        if response.status_code == ResponseStatusCodes.ACCEPTED:
            _LOGGER.info(
                f"Sample '{sample_name}' added to view '{view_name}' in project '{namespace}/{name}:{tag}' successfully."
            )
            return None
        elif response.status_code == ResponseStatusCodes.NOT_EXIST:
            raise ResponseError(
                f"Sample '{sample_name}' or project {namespace}/{name}:{tag} does not exist."
            )
        elif response.status_code == ResponseStatusCodes.CONFLICT:
            raise ResponseError(f"Sample '{sample_name}' already exists in the view.")
        else:
            raise ResponseError(
                f"Unexpected return value. Error: {response.status_code}"
            )

    def remove_sample(
        self,
        namespace: str,
        name: str,
        tag: str,
        view_name: str,
        sample_name: str,
    ):
        """
        Remove sample from view in project in PEPhub.

        Args:
            namespace: namespace of project
            name: name of project
            tag: tag of project
            view_name: name of the view
            sample_name: name of the sample
        """
        url = self._build_view_request_url(
            namespace=namespace,
            name=name,
            view_name=view_name,
            sample_name=sample_name,
        )

        url = url + self.parse_query_param(pep_variables={"tag": tag})

        response = self.send_request(
            method="DELETE",
            url=url,
            headers=self.parse_header(self.__jwt_data),
        )
        if response.status_code == ResponseStatusCodes.ACCEPTED:
            _LOGGER.info(
                f"Sample '{sample_name}' removed from view '{view_name}' in project '{namespace}/{name}:{tag}' successfully."
            )
            return None
        elif response.status_code == ResponseStatusCodes.NOT_EXIST:
            raise ResponseError(
                f"Sample '{sample_name}' or project {namespace}/{name}:{tag} does not exist. "
            )
        elif response.status_code == ResponseStatusCodes.UNAUTHORIZED:
            raise ResponseError(
                "You are unauthorized to remove this sample from the view."
            )
        else:
            raise ResponseError(
                f"Unexpected return value. Error: {response.status_code}"
            )

    def _build_view_request_url(
        self, namespace: str, name: str, view_name: str, sample_name: str = None
    ):
        """
        Build URL for view request.

        Args:
            namespace: namespace of project
            name: name of project
            view_name: name of view

        Returns:
            URL.
        """
        if sample_name:
            return self.__base_url + PEPHUB_VIEW_SAMPLE_PATH.format(
                namespace=quote(str(namespace), safe=""),
                project=quote(str(name), safe=""),
                view_name=quote(str(view_name), safe=""),
                sample_name=quote(str(sample_name), safe=""),
            )
        return self.__base_url + PEPHUB_VIEW_PATH.format(
            namespace=quote(str(namespace), safe=""),
            project=quote(str(name), safe=""),
            view_name=quote(str(view_name), safe=""),
        )
