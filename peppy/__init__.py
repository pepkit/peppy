"""
Project configuration, particularly for logging.

Project-scope constants may reside here, but more importantly, some setup here
will provide a logging infrastructure for all of the project's modules.
Individual modules and classes may provide separate configuration on a more
local level, but this will at least provide a foundation.

"""

from importlib.metadata import PackageNotFoundError, version

from .const import *
from .exceptions import *
from .project import Project
from .sample import Sample

try:
    __version__ = version("peppy")
except PackageNotFoundError:
    # package is not installed (e.g. running from a source checkout)
    __version__ = "0.0.0"

__all__ = ["Project", "Sample", "PeppyError", "__version__"]

LOGGING_LEVEL = "INFO"
