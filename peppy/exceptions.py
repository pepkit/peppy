""" Custom error types """

from abc import ABCMeta

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"

__all__ = ["IllegalStateException", "PeppyError"]


class PeppyError(Exception):
    """ Base error type for peppy custom errors. """

    __metaclass__ = ABCMeta

    def __init__(self, msg):
        super(PeppyError, self).__init__(msg)


class IllegalStateException(PeppyError):
    """ Occurrence of some illogical/prohibited state within an object. """
    pass
