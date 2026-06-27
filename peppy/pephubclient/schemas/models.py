import datetime

from pydantic import BaseModel, ConfigDict


class PaginationResult(BaseModel):
    page: int = 0
    page_size: int = 10
    total: int


class SchemaVersionAnnotation(BaseModel):
    """
    Schema version annotation model
    """

    namespace: str
    schema_name: str
    version: str
    contributors: str | None = ""
    release_notes: str | None = ""
    tags: dict[str, str | None] = {}
    release_date: datetime.datetime
    last_update_date: datetime.datetime


class SchemaVersionResult(BaseModel):
    pagination: PaginationResult
    results: list[SchemaVersionAnnotation]


class NewSchemaVersionModel(BaseModel):
    """
    Model for creating a new schema version from json
    """

    contributors: str | None = None
    release_notes: str | None = None
    tags: list[str] | str | dict[str, str] | list[dict[str, str]] | None = None
    version: str
    schema_value: dict

    model_config = ConfigDict(extra="forbid")


class NewSchemaRecordModel(NewSchemaVersionModel):
    """
    Model for creating a new schema record from json
    """

    schema_name: str
    description: str | None = None
    maintainers: str | None = None
    lifecycle_stage: str | None = None
    private: bool = False

    model_config = ConfigDict(extra="forbid")


class UpdateSchemaRecordFields(BaseModel):
    maintainers: str | None = None
    lifecycle_stage: str | None = None
    private: bool | None = None
    name: str | None = None
    description: str | None = None

    model_config = ConfigDict(extra="forbid")


class UpdateSchemaVersionFields(BaseModel):
    contributors: str | None = None
    schema_value: str | None = None
    release_notes: str | None = None

    model_config = ConfigDict(extra="forbid")
