import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..const import CONFIG_KEY, SAMPLE_RAW_DICT_KEY, SUBSAMPLE_RAW_LIST_KEY


class ProjectDict(BaseModel):
    """
    Project dict (raw) model
    """

    config: dict = Field(alias=CONFIG_KEY)
    subsample_list: list | None = Field(alias=SUBSAMPLE_RAW_LIST_KEY)
    sample_list: list = Field(alias=SAMPLE_RAW_DICT_KEY)

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class ProjectUploadData(BaseModel):
    """
    Model used in post request to upload project
    """

    pep_dict: ProjectDict
    tag: str | None = "default"
    is_private: bool | None = False
    overwrite: bool | None = False

    @field_validator("tag")
    def tag_should_not_be_none(cls, v):
        return v or "default"


class ProjectAnnotationModel(BaseModel):
    namespace: str
    name: str
    tag: str
    is_private: bool
    number_of_samples: int
    description: str
    last_update_date: datetime.datetime
    submission_date: datetime.datetime
    digest: str
    pep_schema: str | int | None = None
    pop: bool = False
    stars_number: int | None = 0
    forked_from: str | None = None


class SearchReturnModel(BaseModel):
    count: int
    limit: int
    offset: int
    results: list[ProjectAnnotationModel]
