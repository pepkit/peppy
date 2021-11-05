""" Helpers without an obvious logical home. """

import logging
import os
from urllib.error import HTTPError
from urllib.request import urlopen

import yaml
from ubiquerg import expandpath, is_url

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


def make_abs_via_cfg(maybe_relpath, cfg_path, check_exists=False):
    """ Ensure that a possibly relative path is absolute. """
    if not isinstance(maybe_relpath, str):
        raise TypeError(
            "Attempting to ensure non-text value is absolute path: {} ({})".format(
                maybe_relpath, type(maybe_relpath)
            )
        )
    if os.path.isabs(maybe_relpath) or is_url(maybe_relpath):
        _LOGGER.debug("Already absolute")
        return maybe_relpath
    # Maybe we have env vars that make the path absolute?
    expanded = expandpath(maybe_relpath)
    if os.path.isabs(expanded):
        _LOGGER.debug("Expanded: {}".format(expanded))
        return expanded
    # Set path to an absolute path, relative to project config.
    config_dirpath = os.path.dirname(cfg_path)
    _LOGGER.debug("config_dirpath: {}".format(config_dirpath))
    abs_path = os.path.join(config_dirpath, maybe_relpath)
    _LOGGER.debug("Expanded and/or made absolute: {}".format(abs_path))
    if check_exists and not os.path.exists(abs_path):
        raise OSError(f"Path made absolute does not exist: {abs_path}")
    return abs_path


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
        return prj[CONFIG_KEY].to_dict()
    except KeyError:
        raise KeyError("Project lacks section '{}'".format(CONFIG_KEY))
    return data


def make_list(arg, obj_class):
    """
    Convert an object of predefined class to a list of objects of that class or
    ensure a list is a list of objects of that class

    :param list[obj] | obj arg: string or a list of strings to listify
    :param str obj_class: name of the class of intrest
    :return list: list of objects of the predefined class
    :raise TypeError: if a faulty argument was provided
    """

    def _raise_faulty_arg():
        raise TypeError(
            "Provided argument has to be a list[{o}] or a {o}, "
            "got '{a}'".format(o=obj_class.__name__, a=arg.__class__.__name__)
        )

    if isinstance(arg, obj_class):
        return [arg]
    elif isinstance(arg, list):
        if not all(isinstance(i, obj_class) for i in arg):
            _raise_faulty_arg()
        else:
            return arg
    else:
        _raise_faulty_arg()


def load_yaml(filepath):
    """ Load a yaml file into a Python dict """

    def read_yaml_file(filepath):
        """
        Read a YAML file

        :param str filepath: path to the file to read
        :return dict: read data
        """
        filepath = os.path.abspath(filepath)
        with open(filepath, "r") as f:
            data = yaml.safe_load(f)
        return data

    if is_url(filepath):
        _LOGGER.debug(f"Got URL: {filepath}")
        try:
            response = urlopen(filepath)
        except HTTPError as e:
            raise e
        data = response.read()  # a `bytes` object
        text = data.decode("utf-8")
        return yaml.safe_load(text)
    else:
        return read_yaml_file(filepath)
