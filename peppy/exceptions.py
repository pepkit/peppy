""" Custom error types """

from abc import ABCMeta


class PeppyError(Exception):
    """ Base error type for peppy custom errors. """

    __metaclass__ = ABCMeta

    def __init__(self, msg):
        super(PeppyError, self).__init__(msg)
