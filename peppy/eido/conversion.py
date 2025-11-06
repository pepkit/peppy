import sys

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points

import inspect
import os
from logging import getLogger
from typing import Callable, Dict, List, NoReturn, Optional

from ..project import Project
from .exceptions import EidoFilterError

_LOGGER = getLogger(__name__)


def pep_conversion_plugins() -> Dict[str, Callable]:
    """Plugins registered by entry points in the current Python env.

    Returns:
        Dict which keys are names of all possible hooks and values are dicts
        mapping registered functions names to their values

    Raises:
        EidoFilterError: If any of the filters has an invalid signature
    """
    plugins = {}
    for ep in entry_points(group="pep.filters"):
        plugin_fun = ep.load()
        if len(list(inspect.signature(plugin_fun).parameters)) != 2:
            raise EidoFilterError(
                f"Invalid filter plugin signature: {ep.name}. "
                f"Filter functions must take 2 arguments: peppy.Project and **kwargs"
            )
        plugins[ep.name] = plugin_fun
    return plugins


def convert_project(
    prj: Project, target_format: str, plugin_kwargs: Optional[Dict] = None
) -> Dict[str, str]:
    """Convert a `peppy.Project` object to a selected format.

    Args:
        prj: A Project object to convert
        target_format: The format to convert the Project object to
        plugin_kwargs: Kwargs to pass to the plugin function

    Returns:
        Dictionary with conversion results

    Raises:
        EidoFilterError: If the requested filter is not defined
    """
    return run_filter(prj, target_format, plugin_kwargs=plugin_kwargs or dict())


def run_filter(
    prj: Project,
    filter_name: str,
    verbose: bool = True,
    plugin_kwargs: Optional[Dict] = None,
) -> Dict[str, str]:
    """Run a selected filter on a peppy.Project object.

    Args:
        prj: A Project to run filter on
        filter_name: Name of the filter to run
        verbose: Whether to print output to stdout
        plugin_kwargs: Kwargs to pass to the plugin function

    Returns:
        Dictionary with conversion results

    Raises:
        EidoFilterError: If the requested filter is not defined
    """
    # convert to empty dictionary if no plugin_kwargs are passed
    plugin_kwargs = plugin_kwargs or dict()

    # get necessary objects
    installed_plugins = pep_conversion_plugins()
    installed_plugin_names = list(installed_plugins.keys())
    paths = plugin_kwargs.get("paths")
    env = plugin_kwargs.get("env")

    # set environment
    if env is not None:
        for var in env:
            os.environ[var] = env[var]

    # check for valid filter
    if filter_name not in installed_plugin_names:
        raise EidoFilterError(
            f"Requested filter ({filter_name}) not found. "
            f"Available: {', '.join(installed_plugin_names)}"
        )
    _LOGGER.info(f"Running plugin {filter_name}")
    func = installed_plugins[filter_name]

    # run filter
    conv_result = func(prj, **plugin_kwargs)

    # if paths supplied, write to disk
    if paths is not None:
        # map conversion result to the
        # specified path
        for result_key in conv_result:
            result_path = paths.get(result_key)
            if result_path is None:
                _LOGGER.warning(
                    f"Conversion plugin returned key that doesn't exist in specified paths: '{result_key}'."
                )
            else:
                # create path if it doesn't exist
                if not os.path.exists(result_path) and os.path.isdir(
                    os.path.dirname(result_path)
                ):
                    os.makedirs(os.path.dirname(result_path), exist_ok=True)
                save_result(result_path, conv_result[result_key])

    if verbose:
        for result_key in conv_result:
            sys.stdout.write(conv_result[result_key])

    return conv_result


def save_result(result_path: str, content: str) -> NoReturn:
    with open(result_path, "w") as f:
        f.write(content)


def get_available_pep_filters() -> List[str]:
    """Get a list of available target formats.

    Returns:
        A list of available formats
    """
    return list(pep_conversion_plugins().keys())
