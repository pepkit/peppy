"""Project configuration, particularly for logging.

Project-scope constants may reside here, but more importantly, some setup here
will provide a logging infrastructure for all of the project's modules.
Individual modules and classes may provide separate configuration on a more
local level, but this will at least provide a foundation.

"""

import logging
import os
from sys import stderr


LOOPERENV_VARNAME = "LOOPERENV"

DEFAULT_LOGGING = {""}
LOGGING_LEVEL = logging.INFO
LOGGING_LOCATIONS = (stderr, )

# TODO: establish these.
DEFAULT_LOGGING_FMT = ""
DEFAULT_DATEFMT = ""

# name
# Level
# Location
# Format
# Date format

LOOPER_LOGGER = None


def setup_looper_logger(level=LOGGING_LEVEL,
                        additional_locations=(),
                        fmt=None, datefmt=None):

    global LOOPER_LOGGER
    LOOPER_LOGGER = logging.getLogger(__name__.split(".")[0])
    LOOPER_LOGGER.setLevel(level)

    locations_exception = None
    where = LOGGING_LOCATIONS

    if isinstance(additional_locations, str):
        additional_locations = [additional_locations]
    try:
        where += LOGGING_LOCATIONS + (type(LOGGING_LOCATIONS))(additional_locations)
    except TypeError as e:
        locations_exception = e
    formatter = logging.Formatter(fmt or DEFAULT_LOGGING_FMT,
                                  datefmt or DEFAULT_DATEFMT)

    if locations_exception:
        print("Could not interpret {} as supplementary root logger target "
              "destinations; using {} as root logger location(s): {}".
              format(additional_locations, LOGGING_LOCATIONS))

    for loc in where:
        if isinstance(loc, str):
            dirpath = os.path.dirname(loc)
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)
            handler_type = logging.FileHandler
        elif hasattr(loc, "write"):
            handler_type = logging.StreamHandler
        else:
            print("{} as logs destination appears to be neither"
                  " a filepath nor a stream.".format(loc))
            continue
        LOOPER_LOGGER.addHandler(handler_type(formatter))


    # TODO: warn if requested level is less than the effective level.
