"""Project configuration, particularly for logging.

Project-scope constants may reside here, but more importantly, some setup here
will provide a logging infrastructure for all of the project's modules.
Individual modules and classes may provide separate configuration on a more
local level, but this will at least provide a foundation.

"""

from importlib.metadata import version

from .const import *
from .exceptions import *
from .project import Project
from .sample import Sample

__version__ = version("peppy")

__classes__ = ["Project", "Sample"]
__all__ = __classes__ + ["PeppyError", "__version__"]

LOGGING_LEVEL = "INFO"
