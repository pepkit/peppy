""" Custom error types """

from abc import ABCMeta
from collections import Iterable

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"

__all__ = ["IllegalStateException", "InvalidSampleTableFileException", "PeppyError", "MissingSubprojectError"]


class PeppyError(Exception):
    """ Base error type for peppy custom errors. """

    __metaclass__ = ABCMeta

    def __init__(self, msg):
        super(PeppyError, self).__init__(msg)


class IllegalStateException(PeppyError):
    """ Occurrence of some illogical/prohibited state within an object. """
    pass


class InvalidSampleTableFileException(PeppyError):
    """ Error type for invalid sample annotations file. """
    pass


class MissingSubprojectError(PeppyError):
    """ Error when project config lacks a requested subproject. """

    def __init__(self, sp, defined=None):
        """
        Create exception with missing subproj request.

        :param str sp: the requested (and missing) subproject
        :param Iterable[str] defined: collection of names of defined subprojects
        """
        msg = "Subproject '{}' not found".format(sp)
        if isinstance(defined, Iterable):
            ctx = "defined subproject(s): {}".format(", ".join(map(str, defined)))
            msg = "{}; {}".format(msg, ctx)
        super(MissingSubprojectError, self).__init__(msg)