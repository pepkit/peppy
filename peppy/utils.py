""" Helpers without an obvious logical home. """

import logging
from yacman import load_yaml as _load_yaml
from .const import CONFIG_KEY

_LOGGER = logging.getLogger(__name__)


def copy(obj):
    def copy(self):
        """
        Copy self to a new object.
        """
        from copy import deepcopy

        return deepcopy(self)
    obj.copy = copy
    return obj


def read_schema(schema):
    """
    Safely read schema from YAML-formatted file.

    :param str | Mapping schema: path to the schema file
        or schema in a dict form
    :return dict: read schema
    :raise TypeError: if the schema arg is neither a Mapping nor a file path
    """
    if isinstance(schema, str):
        return _load_yaml(schema)
    elif isinstance(schema, dict):
        return schema
    raise TypeError("schema has to be either a dict, URL to remote schema "
                    "or a path to an existing file")


def grab_project_data(prj):
    """
    From the given Project, grab Sample-independent data.

    There are some aspects of a Project of which it's beneficial for a Sample
    to be aware, particularly for post-hoc analysis. Since Sample objects
    within a Project are mutually independent, though, each doesn't need to
    know about any of the others. A Project manages its, Sample instances,
    so for each Sample knowledge of Project data is limited. This method
    facilitates adoption of that conceptual model.

    :param Project prj: Project from which to grab data
    :return Mapping: Sample-independent data sections from given Project
    """
    if not prj:
        return {}

    try:
        data = prj[CONFIG_KEY]
    except KeyError:
        _LOGGER.debug("Project lacks section {}, skipping".format(CONFIG_KEY))
    return data