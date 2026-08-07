"""pephubclient: a client for the PEPhub registry.

Formerly the standalone ``pephubclient`` package, now vendored into ``peppy``
and available as ``peppy.pephubclient``. This module re-exports the public API
so that ``from peppy.pephubclient import PEPHubClient`` keeps working.
"""

from .constants import RegistryPath
from .helpers import is_registry_path
from .pephubclient import PEPHubClient

__all__ = [
    "PEPHubClient",
    "RegistryPath",
    "is_registry_path",
]
