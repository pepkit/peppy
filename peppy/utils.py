""" Helpers without an obvious logical home. """

from collections import Iterable
import logging
import os

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
