"""Custom error types"""

from abc import ABCMeta
from collections.abc import Iterable
from typing import Optional

__all__ = [
    "IllegalStateException",
    "InvalidSampleTableFileException",
    "PeppyError",
    "MissingAmendmentError",
    "InvalidConfigFileException",
    "SampleTableFileException",
    "RemoteYAMLError",
]


class PeppyError(Exception):
    """Base error type for peppy custom errors."""

    __metaclass__ = ABCMeta

    def __init__(self, msg: str) -> None:
        super(PeppyError, self).__init__(msg)


class IllegalStateException(PeppyError):
    """Occurrence of some illogical/prohibited state within an object."""

    pass


class SampleTableFileException(PeppyError):
    """Error type for invalid sample annotations file."""

    pass


class InvalidSampleTableFileException(SampleTableFileException):
    """Error type for invalid sample annotations file."""

    pass


class RemoteYAMLError(PeppyError):
    """Remote YAML file cannot be accessed"""

    pass


class MissingAmendmentError(PeppyError):
    """Error when project config lacks a requested subproject."""

    def __init__(self, amendment: str, defined: Optional[Iterable[str]] = None) -> None:
        """Create exception with missing amendment request.

        Args:
            amendment: The requested (and missing) amendment
            defined: Collection of names of defined amendments
        """
        msg = "Amendment '{}' not found".format(amendment)
        if isinstance(defined, Iterable):
            ctx = "defined amendments(s): {}".format(", ".join(map(str, defined)))
            msg = "{}; {}".format(msg, ctx)
        super(MissingAmendmentError, self).__init__(msg)


class InvalidConfigFileException(PeppyError):
    """Error type for invalid project config file"""

    pass
