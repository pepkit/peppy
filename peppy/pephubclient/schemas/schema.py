import logging

from ..constants import ResponseStatusCodes
from ..exceptions import ResponseError
from ..helpers import RequestManager
from .constants import (
    LATEST_VERSION,
    PEPHUB_SCHEMA_NEW_SCHEMA_URL,
    PEPHUB_SCHEMA_NEW_VERSION_URL,
    PEPHUB_SCHEMA_RECORD_URL,
    PEPHUB_SCHEMA_VERSION_URL,
    PEPHUB_SCHEMA_VERSIONS_URL,
)
from .models import (
    NewSchemaRecordModel,
    NewSchemaVersionModel,
    SchemaVersionResult,
    UpdateSchemaRecordFields,
    UpdateSchemaVersionFields,
)

_LOGGER = logging.getLogger("pephubclient")


class PEPHubSchema(RequestManager):
    """
    Class for managing schemas in PEPhub.

    Provides methods for getting, creating, updating and removing schema records
    and schema versions.
    """

    def __init__(self, jwt_data: str = None):
        """
        Initialize PEPHubSchema.

        Args:
            jwt_data: jwt token for authorization
        """
        self.__jwt_data = jwt_data

    def get(
        self, namespace: str, schema_name: str, version: str = LATEST_VERSION
    ) -> dict:
        """
        Get schema value for specific schema version.

        Args:
            namespace: namespace of schema
            schema_name: name of schema
            version: version of schema

        Returns:
            Schema object as dictionary.
        """
        pephub_response = self.send_request(
            method="GET",
            url=PEPHUB_SCHEMA_VERSION_URL.format(
                namespace=namespace, schema_name=schema_name, version=version
            ),
            headers=self.parse_header(self.__jwt_data),
            cookies=None,
        )
        if pephub_response.status_code == ResponseStatusCodes.OK:
            decoded_response = self.decode_response(pephub_response, output_json=True)
            return decoded_response

        if pephub_response.status_code == ResponseStatusCodes.NOT_EXIST:
            raise ResponseError("Schema doesn't exist, or you are unauthorized.")
        if pephub_response.status_code == ResponseStatusCodes.INTERNAL_ERROR:
            raise ResponseError(
                f"Internal server error. Unexpected return value. Error: {pephub_response.status_code}"
            )
        else:
            raise ResponseError(
                f"Unexpected Status code return. Error: {pephub_response.status_code}"
            )

    def get_versions(self, namespace: str, schema_name: str) -> SchemaVersionResult:
        """
        Get list of versions.

        Args:
            namespace: Namespace of the schema record
            schema_name: Name of the schema record

        Returns:
            SchemaVersionResult with pagination and list of versions.
        """
        pephub_response = self.send_request(
            method="GET",
            url=PEPHUB_SCHEMA_VERSIONS_URL.format(
                namespace=namespace, schema_name=schema_name
            ),
            headers=self.parse_header(self.__jwt_data),
            cookies=None,
        )

        if pephub_response.status_code == ResponseStatusCodes.OK:
            decoded_response = self.decode_response(pephub_response, output_json=True)
            return SchemaVersionResult(**decoded_response)

        if pephub_response.status_code == ResponseStatusCodes.NOT_EXIST:
            raise ResponseError("Schema doesn't exist, or you are unauthorized.")
        if pephub_response.status_code == ResponseStatusCodes.INTERNAL_ERROR:
            raise ResponseError(
                f"Internal server error. Unexpected return value. Error: {pephub_response.status_code}"
            )
        else:
            raise ResponseError(
                f"Unexpected Status code return. Error: {pephub_response.status_code}"
            )

    def create_schema(
        self,
        namespace: str,
        schema_name: str,
        schema_value: dict,
        version: str = "1.0.0",
        description: str = None,
        maintainers: str = None,
        contributors: str = None,
        release_notes: str = None,
        tags: str | list[str] | dict | None = None,
        lifecycle_stage: str = None,
        private: bool = False,
    ) -> None:
        """
        Create a new schema record + version in the database.

        Args:
            namespace: Namespace of the schema
            schema_name: Name of the schema record
            schema_value: Schema value itself in dict format
            version: First version of the schema
            description: Schema description
            maintainers: Schema maintainers
            contributors: Schema contributors of current version
            release_notes: Release notes for current version
            tags: Tags of the current version. Can be str, list[str], or dict
            lifecycle_stage: Stage of the schema record
            private: Whether project should be public or private. Default: False (public)

        Raises:
            ResponseError: if status not 202.
        """
        url = PEPHUB_SCHEMA_NEW_SCHEMA_URL.format(namespace=namespace)
        request_body = NewSchemaRecordModel(
            schema_name=schema_name,
            description=description,
            maintainers=maintainers,
            lifecycle_stage=lifecycle_stage,
            private=private,
            contributors=contributors,
            release_notes=release_notes,
            tags=tags,
            version=version,
            schema_value=schema_value,
        ).model_dump(exclude_none=True)

        pephub_response = self.send_request(
            method="POST",
            url=url,
            headers=self.parse_header(self.__jwt_data),
            cookies=None,
            json=request_body,
        )

        if pephub_response.status_code == ResponseStatusCodes.ACCEPTED:
            _LOGGER.info(
                f"Schema '{namespace}/{schema_name}:{version}' successfully created in PEPhub"
            )
            return None

        elif pephub_response.status_code == ResponseStatusCodes.UNAUTHORIZED:
            raise ResponseError(
                "User not authorized or doesn't have permission to write to this namespace"
            )

        else:
            raise ResponseError(
                f"Unexpected error. Status code: {pephub_response.status_code}"
            )

    def add_version(
        self,
        namespace: str,
        schema_name: str,
        schema_value: dict,
        version: str = "1.0.0",
        contributors: str = None,
        release_notes: str = None,
        tags: str | list[str] | dict | None = None,
    ) -> None:
        """
        Add new version to the schema registry.

        Args:
            namespace: Namespace of the schema
            schema_name: Name of the schema record
            schema_value: Schema value itself in dict format
            version: First version of the schema
            contributors: Schema contributors of current version
            release_notes: Release notes for current version
            tags: Tags of the current version. Can be str, list[str], or dict

        Raises:
            ResponseError: if status not 202.
        """
        url = PEPHUB_SCHEMA_NEW_VERSION_URL.format(
            namespace=namespace, schema_name=schema_name
        )
        request_body = NewSchemaVersionModel(
            contributors=contributors,
            release_notes=release_notes,
            tags=tags,
            version=version,
            schema_value=schema_value,
        ).model_dump(exclude_none=True, exclude_unset=True)

        pephub_response = self.send_request(
            method="POST",
            url=url,
            headers=self.parse_header(self.__jwt_data),
            cookies=None,
            json=request_body,
        )

        if pephub_response.status_code == ResponseStatusCodes.ACCEPTED:
            _LOGGER.info(
                f"Schema version '{namespace}/{schema_name}:{version}' successfully created in PEPhub"
            )
            return None

        elif pephub_response.status_code == ResponseStatusCodes.UNAUTHORIZED:
            raise ResponseError(
                "User not authorized or doesn't have permission to write to this namespace"
            )

        else:
            raise ResponseError(
                f"Unexpected error. Status code: {pephub_response.status_code}"
            )

    def update_record(
        self,
        namespace: str,
        schema_name: str,
        update_fields: dict | UpdateSchemaRecordFields,
    ) -> None:
        """
        Update schema registry data.

        Args:
            namespace: Namespace of the schema
            schema_name: Name of the schema version
            update_fields: dict or pydantic model UpdateSchemaRecordFields with
                fields: maintainers, lifecycle_stage, private, name, description.

        Raises:
            ResponseError: if status not 202.
        """
        if isinstance(update_fields, dict):
            update_fields = UpdateSchemaRecordFields(**update_fields)

        update_fields = update_fields.model_dump(exclude_none=True, exclude_unset=True)

        url = PEPHUB_SCHEMA_RECORD_URL.format(
            namespace=namespace, schema_name=schema_name
        )

        pephub_response = self.send_request(
            method="PATCH",
            url=url,
            headers=self.parse_header(self.__jwt_data),
            cookies=None,
            json=update_fields,
        )

        if pephub_response.status_code == ResponseStatusCodes.ACCEPTED:
            _LOGGER.info(
                f"Schema record '{namespace}/{schema_name}' was updated successfully!"
            )
            return None

        elif pephub_response.status_code == ResponseStatusCodes.NOT_EXIST:
            raise ResponseError("Schema doesn't exist in PEPhub")

        elif pephub_response.status_code == ResponseStatusCodes.UNAUTHORIZED:
            raise ResponseError(
                "User not authorized or doesn't have permission to write to this namespace"
            )

        else:
            raise ResponseError(
                f"Unexpected error. Status code: {pephub_response.status_code}"
            )

    def update_version(
        self,
        namespace: str,
        schema_name: str,
        version: str,
        update_fields: dict | UpdateSchemaVersionFields,
    ) -> None:
        """
        Update released version of the schema.

        Args:
            namespace: Namespace of the schema
            schema_name: Name of the schema version
            version: Schema version
            update_fields: dict or pydantic model UpdateSchemaVersionFields with
                fields: contributors, schema_value, release_notes.

        Raises:
            ResponseError: if status not 202.
        """
        url = PEPHUB_SCHEMA_VERSION_URL.format(
            namespace=namespace, schema_name=schema_name, version=version
        )

        if isinstance(update_fields, dict):
            update_fields = UpdateSchemaVersionFields(**update_fields)

        update_fields = update_fields.model_dump(exclude_unset=True, exclude_none=True)

        pephub_response = self.send_request(
            method="PATCH",
            url=url,
            headers=self.parse_header(self.__jwt_data),
            cookies=None,
            json=update_fields,
        )

        if pephub_response.status_code == ResponseStatusCodes.ACCEPTED:
            _LOGGER.info(
                f"Schema version '{namespace}/{schema_name}:{version}' was updated successfully!"
            )
            return None

        elif pephub_response.status_code == ResponseStatusCodes.NOT_EXIST:
            raise ResponseError("Schema doesn't exist in PEPhub")

        elif pephub_response.status_code == ResponseStatusCodes.UNAUTHORIZED:
            raise ResponseError(
                "User not authorized or doesn't have permission to write to this namespace"
            )

        else:
            raise ResponseError(
                f"Unexpected error. Status code: {pephub_response.status_code}"
            )

    def delete_schema(self, namespace: str, schema_name: str) -> None:
        """
        Delete schema from the database.

        Args:
            namespace: Namespace of the schema
            schema_name: Name of the schema version
        """
        url = PEPHUB_SCHEMA_RECORD_URL.format(
            namespace=namespace, schema_name=schema_name
        )

        pephub_response = self.send_request(
            method="DELETE",
            url=url,
            headers=self.parse_header(self.__jwt_data),
            cookies=None,
        )

        if pephub_response.status_code == ResponseStatusCodes.ACCEPTED:
            _LOGGER.info(
                f"Schema record '{namespace}/{schema_name}' was updated successfully!"
            )
            return None

        elif pephub_response.status_code == ResponseStatusCodes.NOT_EXIST:
            raise ResponseError("Schema doesn't exist in PEPhub")

        elif pephub_response.status_code == ResponseStatusCodes.UNAUTHORIZED:
            raise ResponseError(
                "User not authorized or doesn't have permission to write to this namespace"
            )

        else:
            raise ResponseError(
                f"Unexpected error. Status code: {pephub_response.status_code}"
            )

    def delete_version(
        self,
        namespace: str,
        schema_name: str,
        version: str,
    ) -> None:
        """
        Delete schema version.

        Args:
            namespace: Namespace of the schema
            schema_name: Name of the schema
            version: Schema version

        Raises:
            ResponseError: if status not 202.
        """
        url = PEPHUB_SCHEMA_VERSION_URL.format(
            namespace=namespace, schema_name=schema_name, version=version
        )

        pephub_response = self.send_request(
            method="DELETE",
            url=url,
            headers=self.parse_header(self.__jwt_data),
            cookies=None,
        )

        if pephub_response.status_code == ResponseStatusCodes.ACCEPTED:
            _LOGGER.info(
                f"Schema version '{namespace}/{schema_name}:{version}' was deleted successfully!"
            )
            return None

        elif pephub_response.status_code == ResponseStatusCodes.NOT_EXIST:
            raise ResponseError("Schema doesn't exist in PEPhub")

        elif pephub_response.status_code == ResponseStatusCodes.UNAUTHORIZED:
            raise ResponseError(
                "User not authorized or doesn't have permission to write to this namespace"
            )

        else:
            raise ResponseError(
                f"Unexpected error. Status code: {pephub_response.status_code}"
            )
