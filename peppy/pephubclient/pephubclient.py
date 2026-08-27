from typing import Literal

from pydantic import ValidationError
from typing_extensions import deprecated
from ubiquerg import parse_registry_path

from ..const import (
    CONFIG_KEY,
    NAME_KEY,
    SAMPLE_RAW_DICT_KEY,
    SUBSAMPLE_RAW_LIST_KEY,
)
from ..project import Project
from .constants import (
    PATH_TO_TOKEN_FILE,
    RegistryPath,
    ResponseStatusCodes,
)
from .exceptions import IncorrectQueryStringError, ResponseError
from .files_manager import FilesManager
from .helpers import MessageHandler, RequestManager, save_pep
from .models import (
    ProjectAnnotationModel,
    ProjectDict,
    ProjectUploadData,
    SearchReturnModel,
)
from .modules.sample import PEPHubSample
from .modules.view import PEPHubView
from .pephub_oauth.pephub_oauth import PEPHubAuth
from .schemas.schema import PEPHubSchema

class PEPHubClient(RequestManager):
    def __init__(self):
        cached = FilesManager.load_token_data(PATH_TO_TOKEN_FILE)
        self.__jwt_data = cached.token
        self.__base_url = cached.base_url.rstrip("/") + "/"

        self.__view = PEPHubView(self.__jwt_data)
        self.__sample = PEPHubSample(self.__jwt_data)
        self.__schema = PEPHubSchema(self.__jwt_data)

    @property
    def view(self) -> PEPHubView:
        return self.__view

    @property
    def sample(self) -> PEPHubSample:
        return self.__sample

    @property
    def schema(self) -> PEPHubSchema:
        return self.__schema

    def login(self, token: str | None = None, url: str | None = None) -> None:
        """
        Log in to PEPhub.

        Args:
            token: JWT token to register directly. If provided, the browser
                device-code flow is skipped.
            url: Base URL for PEPhub. If provided, overrides the cached/default URL.
        """
        cached = FilesManager.load_token_data(PATH_TO_TOKEN_FILE)
        if url:
            cached.base_url = url
        if token:
            MessageHandler.print_warning("Token provided. Registering...")
            cached.token = token
        else:
            cached.token = PEPHubAuth().login_to_pephub(base_url=cached.base_url)

        FilesManager.save_token_data(PATH_TO_TOKEN_FILE, cached)
        self.__jwt_data = cached.token
        self.__base_url = cached.base_url.rstrip("/") + "/"

    def logout(self) -> None:
        """Log out from PEPhub."""
        FilesManager.delete_file_if_exists(PATH_TO_TOKEN_FILE)
        self.__jwt_data = None

    def pull(
        self,
        project_registry_path: str,
        force: bool | None = False,
        zip: bool | None = False,
        output: str | None = None,
    ) -> None:
        """
        Download project locally.

        Args:
            project_registry_path: Project registry path in PEPhub
                (e.g. databio/base:default)
            force: if project exists, overwrite it.
            zip: if True, save project as zip file
            output: path where project will be saved
        """
        project_dict = self.load_raw_pep(
            registry_path=project_registry_path,
        )

        save_pep(
            project=project_dict,
            reg_path=project_registry_path,
            force=force,
            project_path=output,
            zip=zip,
        )

    def load_project(
        self,
        project_registry_path: str,
        query_param: dict | None = None,
    ) -> Project:
        """
        Load peppy project from PEPhub in Project object.

        Args:
            project_registry_path: registry path of the project
            query_param: query parameters used in get request

        Returns:
            peppy project.
        """
        raw_pep = self.load_raw_pep(project_registry_path, query_param)
        peppy_project = Project().from_dict(raw_pep)
        return peppy_project

    def push(
        self,
        cfg: str,
        namespace: str,
        name: str | None = None,
        tag: str | None = None,
        is_private: bool | None = False,
        force: bool | None = False,
    ) -> None:
        """
        Push (upload/update) project to Pephub using config/csv path.

        Args:
            cfg: Project config file (YAML) or sample table (CSV/TSV)
                with one row per sample to constitute project
            namespace: namespace
            name: project name
            tag: project tag
            is_private: Specifies whether project should be private [Default= False]
            force: Force push to the database. Use it to update, or upload
                project. [Default= False]
        """
        peppy_project = Project(cfg=cfg)
        self.upload(
            project=peppy_project,
            namespace=namespace,
            name=name,
            tag=tag,
            is_private=is_private,
            force=force,
        )

    def upload(
        self,
        project: Project,
        namespace: str,
        name: str = None,
        tag: str = None,
        is_private: bool = False,
        force: bool = True,
    ) -> None:
        """
        Upload peppy project to the PEPhub.

        Args:
            project: Project object that has to be uploaded to the DB
            namespace: namespace
            name: project name
            tag: project tag
            is_private: Make project private
            force: overwrite project if it exists, use it to update, or upload
                project.
        """
        pep_dict = project.to_dict(
            extended=True,
            orient="records",
        )
        if name:
            pep_dict[CONFIG_KEY][NAME_KEY] = name

        pep_dict["config"] = pep_dict.pop(CONFIG_KEY)
        pep_dict["samples"] = pep_dict.pop(SAMPLE_RAW_DICT_KEY)
        pep_dict["subsamples"] = pep_dict.pop(SUBSAMPLE_RAW_LIST_KEY)
        upload_data = ProjectUploadData(
            pep_dict=pep_dict,
            tag=tag,
            is_private=is_private,
            overwrite=force,
        )
        pephub_response = self.send_request(
            method="POST",
            url=self._build_push_request_url(namespace=namespace),
            headers=self.parse_header(self.__jwt_data),
            json=upload_data.model_dump(),
            cookies=None,
        )
        if pephub_response.status_code == ResponseStatusCodes.ACCEPTED:
            MessageHandler.print_success(
                f"Project '{namespace}/{name}:{upload_data.tag}' was successfully uploaded"
            )
        elif pephub_response.status_code == ResponseStatusCodes.CONFLICT:
            raise ResponseError(
                "Project already exists. Set force to overwrite project."
            )
        elif pephub_response.status_code == ResponseStatusCodes.UNAUTHORIZED:
            raise ResponseError("Unauthorized! Failure in uploading project.")
        elif pephub_response.status_code == ResponseStatusCodes.FORBIDDEN:
            raise ResponseError(
                "User does not have permission to write to this namespace!"
            )
        else:
            detail = ""
            try:
                detail = self.decode_response(pephub_response, output_json=True).get(
                    "detail", ""
                )
            except Exception:
                pass
            raise ResponseError(
                f"Unexpected Response Error. {pephub_response.status_code}: {detail}"
                if detail
                else f"Unexpected Response Error. {pephub_response.status_code}"
            )
        return None

    def find_project(
        self,
        namespace: str,
        query_string: str = "",
        tag: str = None,
        limit: int = 100,
        offset: int = 0,
        filter_by: Literal["submission_date", "last_update_date"] = None,
        start_date: str = None,
        end_date: str = None,
    ) -> SearchReturnModel:
        """
        Find project in specific namespace and return list of PEP annotation.

        Args:
            namespace: Namespace where to search for projects
            query_string: Search query
            tag: Project tag
            limit: Return limit
            offset: Return offset
            filter_by: Use filter date. Option: [submission_date, last_update_date]
            start_date: filter beginning date
            end_date: filter end date (if none today's date is used)
        """

        query_param = {
            "q": query_string,
            "limit": limit,
            "offset": offset,
            "tag": tag,
        }
        if filter_by in ["submission_date", "last_update_date"]:
            query_param["filter_by"] = filter_by
            query_param["filter_start_date"] = start_date
            if end_date:
                query_param["filter_end_date"] = end_date

        url = self._build_project_search_url(
            namespace=namespace,
            query_param=query_param,
        )

        pephub_response = self.send_request(
            method="GET",
            url=url,
            headers=self.parse_header(self.__jwt_data),
            json=None,
            cookies=None,
        )
        if pephub_response.status_code == ResponseStatusCodes.OK:
            decoded_response = self.decode_response(pephub_response, output_json=True)
            project_list = []
            for project_found in decoded_response["results"]:
                project_list.append(ProjectAnnotationModel(**project_found))
            return SearchReturnModel(**decoded_response)
        raise ResponseError(f"Unexpected response: {pephub_response.status_code}")

    @deprecated("This method is deprecated. Use load_raw_pep instead.")
    def _load_raw_pep(
        self,
        registry_path: str,
        jwt_data: str | None = None,
        query_param: dict | None = None,
    ) -> dict:
        """
        This method is deprecated. Use load_raw_pep instead.

        Request PEPhub and return the requested project as Project object.

        Args:
            registry_path: Project namespace, eg. "geo/GSE124224:tag"
            query_param: Optional variables to be passed to PEPhub

        Returns:
            Raw project in dict.
        """
        return self.load_raw_pep(registry_path, query_param)

    def load_raw_pep(
        self,
        registry_path: str,
        query_param: dict | None = None,
    ) -> dict:
        """
        Request PEPhub and return the requested project as Project object.

        Args:
            registry_path: Project namespace, eg. "geo/GSE124224:tag"
            query_param: Optional variables to be passed to PEPhub

        Returns:
            Raw project in dict.
        """
        query_param = query_param or {}
        query_param["raw"] = "true"

        self._set_registry_data(registry_path)
        pephub_response = self.send_request(
            method="GET",
            url=self._build_pull_request_url(query_param=query_param),
            headers=self.parse_header(self.__jwt_data),
            cookies=None,
        )
        if pephub_response.status_code == ResponseStatusCodes.OK:
            decoded_response = self.decode_response(pephub_response, output_json=True)
            correct_proj_dict = ProjectDict(**decoded_response)

            # This step is necessary because of this issue: https://github.com/pepkit/pephub/issues/124
            return correct_proj_dict.model_dump(by_alias=True)

        if pephub_response.status_code == ResponseStatusCodes.NOT_EXIST:
            raise ResponseError("File does not exist, or you are unauthorized.")
        if pephub_response.status_code == ResponseStatusCodes.INTERNAL_ERROR:
            raise ResponseError(
                f"Internal server error. Unexpected return value. Error: {pephub_response.status_code}"
            )
        raise ResponseError(f"Unexpected response: {pephub_response.status_code}")

    def _set_registry_data(self, query_string: str) -> None:
        """
        Parse provided query string to extract project name, sample name, etc.

        Args:
            query_string: Passed by user. Contain information needed to locate
                the project.
        """
        try:
            self.registry_path = RegistryPath(**parse_registry_path(query_string))
        except (ValidationError, TypeError):
            raise IncorrectQueryStringError(query_string=query_string)

    def _build_pull_request_url(self, query_param: dict = None) -> str:
        """
        Build request for getting projects from pephub.

        Args:
            query_param: dict of parameters used in query string

        Returns:
            url string.
        """
        query_param = query_param or {}
        query_param["tag"] = self.registry_path.tag

        endpoint = self.registry_path.namespace + "/" + self.registry_path.item

        variables_string = self.parse_query_param(query_param)
        endpoint += variables_string

        return f"{self.__base_url}api/v1/projects/" + endpoint

    def _build_project_search_url(
        self, namespace: str, query_param: dict = None
    ) -> str:
        """
        Build request for searching projects from pephub.

        Args:
            query_param: dict of parameters used in query string

        Returns:
            url string.
        """

        variables_string = RequestManager.parse_query_param(query_param)
        endpoint = variables_string

        return f"{self.__base_url}api/v1/namespaces/{namespace}/projects" + endpoint

    def _build_push_request_url(self, namespace: str) -> str:
        """
        Build project upload request used in pephub.

        Args:
            namespace: namespace where project will be uploaded

        Returns:
            url string.
        """
        return f"{self.__base_url}api/v1/namespaces/{namespace}/projects/json"
