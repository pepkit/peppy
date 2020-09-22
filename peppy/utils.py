""" Helpers without an obvious logical home. """

import logging
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
        raise TypeError("Provided argument has to be a list[{o}] or a {o}, "
                        "got '{a}'".format(o=obj_class.__name__,
                                           a=arg.__class__.__name__))

    if isinstance(arg, obj_class):
        return [arg]
    elif isinstance(arg, list):
        if not all(isinstance(i, obj_class) for i in arg):
            _raise_faulty_arg()
        else:
            return arg
    else:
        _raise_faulty_arg()