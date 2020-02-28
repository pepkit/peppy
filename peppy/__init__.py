"""Project configuration, particularly for logging.

Project-scope constants may reside here, but more importantly, some setup here
will provide a logging infrastructure for all of the project's modules.
Individual modules and classes may provide separate configuration on a more
local level, but this will at least provide a foundation.

"""

from ._version import __version__
from .const import *
from .exceptions import *
from .project import Project
from .sample import Sample
from .utils import fetch_samples

_EXPORT_FROM_UTILS = [fetch_samples.__name__]

__classes__ = ["Project", "Sample"]
__all__ = __classes__ + ["PeppyError"] + _EXPORT_FROM_UTILS

LOGGING_LEVEL = "INFO"
