"""Project configuration, particularly for logging.

Project-scope constants may reside here, but more importantly, some setup here
will provide a logging infrastructure for all of the project's modules.
Individual modules and classes may provide separate configuration on a more
local level, but this will at least provide a foundation.

"""

from copy import copy
import logging
from sys import stderr


LOOPERENV_VARNAME = "LOOPERENV"

DEFAULT_LOGGING = {""}
LOGGING_LEVEL = logging.INFO
LOGGING_LOCATIONS = (stderr, )

# name
# Level
# Location
# Format
# Date format


def getLogger(name, **kwargs):
    pass
    # TODO: warn if requested level is less than the effective level.
