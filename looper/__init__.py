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
SUBMISSION_TEMPLATES_FOLDER = "submit_templates"
DEFAULT_LOOPERENV_FILENAME = "default_looperenv.yaml"
DEFAULT_LOOPERENV_CONFIG_RELATIVE = os.path.join(SUBMISSION_TEMPLATES_FOLDER,
                                                 DEFAULT_LOOPERENV_FILENAME)

LOGGING_LEVEL = logging.INFO
LOGGING_LOCATIONS = (stderr, )
DEFAULT_LOGGING_FMT = "%(asctime)s %(name)s %(module)s : %(lineno)d - [%(levelname)s] > %(message)s"


LOOPER_LOGGER = None


def setup_looper_logger(level=LOGGING_LEVEL,
                        additional_locations=(),
                        fmt=DEFAULT_LOGGING_FMT, datefmt=None):
    """
    Called by test configuration via `pytest`'s `conftest`.
    All arguments are optional and have suitable defaults.

    :param int | str level: logging level
    :param tuple(str | FileIO[str]) additional_locations: supplementary
        destination(s) to which to ship logs
    :param str fmt: message format string for log message
    :param str datefmt: datetime format string for log message time
    """

    # Establish the logger.
    global LOOPER_LOGGER
    LOOPER_LOGGER = logging.getLogger(__name__.split(".")[0])
    LOOPER_LOGGER.handlers = []
    LOOPER_LOGGER.setLevel(level)

    # Process any additional locations.
    locations_exception = None
    where = LOGGING_LOCATIONS
    if isinstance(additional_locations, str):
        additional_locations = (additional_locations, )
    try:
        where = LOGGING_LOCATIONS + tuple(additional_locations)
    except TypeError as e:
        locations_exception = e
    if locations_exception:
        print("Could not interpret {} as supplementary root logger target "
              "destinations; using {} as root logger location(s)".
              format(additional_locations, LOGGING_LOCATIONS))

    # Add the handlers.
    formatter = logging.Formatter(fmt, datefmt)
    for loc in where:
        if isinstance(loc, str):
            # File destination
            dirpath = os.path.dirname(loc)
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)
            handler_type = logging.FileHandler
        elif hasattr(loc, "write"):
            # Stream destination
            handler_type = logging.StreamHandler
        else:
            # Strange supplementary destination
            print("{} as logs destination appears to be neither"
                  " a filepath nor a stream.".format(loc))
            continue
        handler = handler_type(loc)
        handler.setLevel(level)
        handler.setFormatter(formatter)
        LOOPER_LOGGER.addHandler(handler)
