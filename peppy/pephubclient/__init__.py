import logging

import coloredlogs

from pephubclient.helpers import is_registry_path, save_pep
from pephubclient.pephubclient import PEPHubClient

__app_name__ = "pephubclient"
__version__ = "0.4.5"
__author__ = "Oleksandr Khoroshevskyi, Rafal Stepien"


# __all__ = [
#     "PEPHubClient",
#     __app_name__,
#     __author__,
#     __version__,
#     "is_registry_path",
#     "save_pep",
# ]
#
#
# _LOGGER = logging.getLogger(__app_name__)
# coloredlogs.install(
#     logger=_LOGGER,
#     datefmt="%H:%M:%S",
#     fmt="[%(levelname)s] [%(asctime)s] %(message)s",
# )
