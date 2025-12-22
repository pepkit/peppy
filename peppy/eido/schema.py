import os
from logging import getLogger
from typing import Dict, List, Union

from ubiquerg import is_url

from ..utils import load_yaml
from .const import PROP_KEY, SAMPLES_KEY

_LOGGER = getLogger(__name__)


def preprocess_schema(schema_dict: Dict) -> Dict:
    """Preprocess schema before validation for user's convenience.

    Preprocessing includes:
    - renaming 'samples' to '_samples' since in the peppy.Project object
        _samples attribute holds the list of peppy.Samples objects.
    - adding array of strings entry for every string specified to accommodate
        subsamples in peppy.Project

    Args:
        schema_dict: Schema dictionary to preprocess

    Returns:
        Preprocessed schema
    """
    _LOGGER.debug(f"schema ori: {schema_dict}")
    if "project" not in schema_dict[PROP_KEY]:
        _LOGGER.debug("No project section found in schema")

    if SAMPLES_KEY in schema_dict[PROP_KEY]:
        if (
            "items" in schema_dict[PROP_KEY][SAMPLES_KEY]
            and PROP_KEY in schema_dict[PROP_KEY][SAMPLES_KEY]["items"]
        ):
            s_props = schema_dict[PROP_KEY][SAMPLES_KEY]["items"][PROP_KEY]
            for prop, val in s_props.items():
                if "type" in val and val["type"] in ["string", "number", "boolean"]:
                    s_props[prop] = {}
                    s_props[prop]["anyOf"] = [val, {"type": "array", "items": val}]
    else:
        _LOGGER.debug("No samples section found in schema")
    _LOGGER.debug(f"schema processed: {schema_dict}")
    return schema_dict


def read_schema(schema: Union[str, Dict]) -> List[Dict]:
    """Safely read schema from YAML-formatted file.

    If the schema imports any other schemas, they will be read recursively.

    Args:
        schema: Path to the schema file or schema in a dict form

    Returns:
        Read schemas

    Raises:
        TypeError: If the schema arg is neither a Mapping nor a file path or
            if the 'imports' sections in any of the schemas is not a list
    """

    def _recursively_read_schemas(
        x: Dict, lst: List[Dict], parent_folder: Union[str, None]
    ) -> List[Dict]:
        if "imports" in x:
            if isinstance(x["imports"], list):
                for sch in x["imports"]:
                    if (not is_url(sch)) and (not os.path.isabs(sch)):
                        # resolve relative path
                        if parent_folder is not None:
                            sch = os.path.normpath(os.path.join(parent_folder, sch))
                        else:
                            _LOGGER.warning(
                                f"The schema contains relative path without known parent folder: {sch}"
                            )
                    lst.extend(read_schema(sch))
            else:
                raise TypeError("In schema the 'imports' section has to be a list")
        lst.append(x)
        return lst

    schema_list = []
    schema_folder = None
    if isinstance(schema, str):
        _LOGGER.debug(f"Reading schema: {schema}")
        schema_folder = os.path.split(schema)[0]
        schema = load_yaml(schema)
    if not isinstance(schema, dict):
        raise TypeError(
            f"schema has to be a dict, path to an existing file or URL to a remote one. "
            f"Got: {type(schema)}"
        )
    return _recursively_read_schemas(schema, schema_list, schema_folder)
