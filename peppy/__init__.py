"""Project configuration, particularly for logging.

Project-scope constants may reside here, but more importantly, some setup here
will provide a logging infrastructure for all of the project's modules.
Individual modules and classes may provide separate configuration on a more
local level, but this will at least provide a foundation.

"""

from ._version import __version__
from .const import *
from .exceptions import *
from .project import Project, ProjectContext
from .sample import Sample, Subsample
from .snake_project import *
from .utils import fetch_samples, grab_project_data, CommandChecker
#from logmuse import init_logger

_EXPORT_FROM_UTILS = [fetch_samples.__name__, grab_project_data.__name__,
                      CommandChecker.__name__]

__classes__ = ["Project", "Sample", "SnakeProject"]
__all__ = __classes__ + ["PeppyError"] + _EXPORT_FROM_UTILS

# TODO: remove
COMPUTE_SETTINGS_VARNAME = "DIVCFG"

LOGGING_LEVEL = "INFO"

# Ensure that we have a handler and don't get a logging exception.
#_LOGGER = logging.getLogger(__name__)
#if not logging.getLogger().handlers:
#    _LOGGER.addHandler(logging.NullHandler())
#_LOGGER = init_logger(name="peppy", level=LOGGING_LEVEL)
