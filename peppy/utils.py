"""Helpers without an obvious logical home."""

import logging
import os
import posixpath as psp
import re
from collections import defaultdict
from typing import Any, Dict, Mapping, Optional, Set, Type, Union
from urllib.request import urlopen

import yaml
from ubiquerg import expandpath, is_url

from .const import CONFIG_KEY, SAMPLE_TABLE_INDEX_KEY, SUBSAMPLE_TABLE_INDEX_KEY
from .exceptions import RemoteYAMLError

_LOGGER = logging.getLogger(__name__)


def copy(obj: Any) -> Any:
    def copy(self):
        """
        Copy self to a new object.
        """
        from copy import deepcopy

        return deepcopy(self)

    obj.copy = copy
    return obj


def make_abs_via_cfg(
    maybe_relpath: str, cfg_path: str, check_exists: bool = False
) -> str:
    """Ensure that a possibly relative path is absolute.

    Args:
        maybe_relpath: Path that may be relative
        cfg_path: Path to configuration file
        check_exists: Whether to verify the resulting path exists

    Returns:
        Absolute path

    Raises:
        TypeError: If maybe_relpath is not a string
        OSError: If check_exists is True and path doesn't exist
    """
    if not isinstance(maybe_relpath, str):
        raise TypeError(
            "Attempting to ensure non-text value is absolute path: {} ({})".format(
                maybe_relpath, type(maybe_relpath)
            )
        )
    if os.path.isabs(maybe_relpath) or is_url(maybe_relpath):
        _LOGGER.debug("Already absolute")
        return maybe_relpath
    # Maybe we have env vars that make the path absolute?
    expanded = expandpath(maybe_relpath)
    if os.path.isabs(expanded):
        _LOGGER.debug("Expanded: {}".format(expanded))
        return expanded
    # Set path to an absolute path, relative to project config.
    if is_url(cfg_path):
        config_dirpath = psp.dirname(cfg_path)
    else:
        config_dirpath = os.path.dirname(cfg_path)
    _LOGGER.debug("config_dirpath: {}".format(config_dirpath))

    if is_url(cfg_path):
        abs_path = psp.join(config_dirpath, maybe_relpath)
    else:
        abs_path = os.path.join(config_dirpath, maybe_relpath)
    _LOGGER.debug("Expanded and/or made absolute: {}".format(abs_path))
    if check_exists and not is_url(abs_path) and not os.path.exists(abs_path):
        raise OSError(f"Path made absolute does not exist: {abs_path}")
    return abs_path


def grab_project_data(prj: Any) -> Mapping:
    """From the given Project, grab Sample-independent data.

    There are some aspects of a Project of which it's beneficial for a Sample
    to be aware, particularly for post-hoc analysis. Since Sample objects
    within a Project are mutually independent, though, each doesn't need to
    know about any of the others. A Project manages its Sample instances,
    so for each Sample knowledge of Project data is limited. This method
    facilitates adoption of that conceptual model.

    Args:
        prj: Project from which to grab data

    Returns:
        Sample-independent data sections from given Project

    Raises:
        KeyError: If project lacks required config section
    """
    if not prj:
        return {}

    try:
        return dict(prj[CONFIG_KEY])
    except KeyError:
        raise KeyError("Project lacks section '{}'".format(CONFIG_KEY))


def make_list(arg: Union[list, str], obj_class: Type) -> list:
    """Convert an object of predefined class to a list or ensure list contains correct type.

    Args:
        arg: Object or list of objects to listify
        obj_class: Class that objects should be instances of

    Returns:
        List of objects of the predefined class

    Raises:
        TypeError: If a faulty argument was provided
    """

    def _raise_faulty_arg():
        raise TypeError(
            "Provided argument has to be a List[{o}] or a {o}, "
            "got '{a}'".format(o=obj_class.__name__, a=arg.__class__.__name__)
        )

    if isinstance(arg, obj_class):
        return [arg]
    elif isinstance(arg, list):
        if not all(isinstance(i, obj_class) for i in arg):
            _raise_faulty_arg()
        else:
            return arg
    else:
        _raise_faulty_arg()


def _expandpath(path: str) -> str:
    """Expand a filesystem path that may or may not contain user/env vars.

    Args:
        path: Path to expand

    Returns:
        Expanded version of input path
    """
    return os.path.expandvars(os.path.expanduser(path))


def expand_paths(x: dict) -> dict:
    """Recursively expand paths in a dict.

    Args:
        x: Dict to expand

    Returns:
        Dict with expanded paths
    """
    if isinstance(x, str):
        return expandpath(x)
    elif isinstance(x, Mapping):
        return {k: expand_paths(v) for k, v in x.items()}
    return x


def load_yaml(filepath: str) -> dict:
    """Load a local or remote YAML file into a Python dict.

    Args:
        filepath: Path to the file to read

    Returns:
        Read data

    Raises:
        RemoteYAMLError: If the remote YAML file reading fails
    """
    if is_url(filepath):
        _LOGGER.debug(f"Got URL: {filepath}")
        try:
            response = urlopen(filepath)
        except Exception as e:
            raise RemoteYAMLError(
                f"Could not load remote file: {filepath}. "
                f"Original exception: {getattr(e, 'message', repr(e))}"
            )
        else:
            data = response.read().decode("utf-8")
            return expand_paths(yaml.safe_load(data))
    else:
        with open(os.path.abspath(filepath), "r") as f:
            data = yaml.safe_load(f)
        return expand_paths(data)


def is_cfg_or_anno(
    file_path: Optional[str], formats: Optional[dict] = None
) -> Optional[bool]:
    """Determine if the input file seems to be a project config file (based on extension).

    Args:
        file_path: File path to examine
        formats: Formats dict to use. Must include 'config' and 'annotation' keys

    Returns:
        True if the file is a config, False if the file is an annotation,
        None if file_path is None

    Raises:
        ValueError: If the file seems to be neither a config nor an annotation
    """
    formats_dict = formats or {
        "config": (".yaml", ".yml"),
        "annotation": (".csv", ".tsv"),
    }
    if file_path is None:
        return None
    if file_path.lower().endswith(formats_dict["config"]):
        _LOGGER.debug(f"Creating a Project from a YAML file: {file_path}")
        return True
    elif file_path.lower().endswith(formats_dict["annotation"]):
        _LOGGER.debug(f"Creating a Project from a CSV file: {file_path}")
        return False
    raise ValueError(
        f"File path '{file_path}' does not point to an annotation or config. "
        f"Accepted extensions: {formats_dict}"
    )


def extract_custom_index_for_sample_table(pep_dictionary: Dict) -> Optional[str]:
    """Extracts a custom index for the sample table if it exists.

    Args:
        pep_dictionary: PEP configuration dictionary

    Returns:
        Custom index name or None if not specified
    """
    return (
        pep_dictionary[SAMPLE_TABLE_INDEX_KEY]
        if SAMPLE_TABLE_INDEX_KEY in pep_dictionary
        else None
    )


def extract_custom_index_for_subsample_table(pep_dictionary: Dict) -> Optional[str]:
    """Extracts a custom index for the subsample table if it exists.

    Args:
        pep_dictionary: PEP configuration dictionary

    Returns:
        Custom index name or None if not specified
    """
    return (
        pep_dictionary[SUBSAMPLE_TABLE_INDEX_KEY]
        if SUBSAMPLE_TABLE_INDEX_KEY in pep_dictionary
        else None
    )


def unpopulated_env_var(paths: Set[str]) -> None:
    """Print warnings for unpopulated environment variables in paths.

    Given a set of paths that may contain env vars, group by env var and
    print a warning for each group with the deepest common directory and
    the paths relative to that directory.

    Args:
        paths: Set of paths that may contain environment variables
    """
    _VAR_RE = re.compile(r"^\$(\w+)/(.*)$")
    groups: dict[str, list[str]] = defaultdict(list)

    # 1) Group by env var
    for s in paths:
        m = _VAR_RE.match(s.strip())
        if not m:
            # Not in "$VAR/..." form — skip or collect under a special key if you prefer
            continue
        var, tail = m.group(1), m.group(2)
        # normalize to POSIX-ish, no leading "./"
        tail = tail.lstrip("/")
        groups[var].append(tail)

    # 2) For each var, compute deepest common directory and print
    for var, tails in groups.items():
        if not tails:
            continue

        if len(tails) == 1:
            # With a single path, use its directory as the common dir
            common_dir = psp.dirname(tails[0]) or "."
        else:
            common_dir = psp.commonpath(tails) or "."
            # Ensure it's a directory; commonpath is component-wise, so it's fine.

        warning_message = "Not all environment variables were populated in derived attribute source: $%s/{"

        in_env = []
        for t in tails:
            rel = psp.relpath(t, start=common_dir or ".")
            in_env.append(rel)

        warning_message += ", ".join(in_env)
        warning_message += "}"
        _LOGGER.warning(
            warning_message,
            var,
        )
