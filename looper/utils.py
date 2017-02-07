""" Helpers without an abvious logical home. """

from collections import defaultdict
import copy
import logging
import os
import yaml


_LOGGER = logging.getLogger(__name__)



class CommandChecker(object):
    """
    Validate call success of executables
    associated with sections of a config file.
    """

    def __init__(self, path_conf_file, include=None, exclude=None):
        """
        The path to the configuration file, and perhaps names of
        validation inclusion and exclusion sections define the instance.

        :param str path_conf_file: path to configuration file with
            sections detailing executable tools to validate
        :param collections.abc.Iterable(str) include: names of sections
            of the given configuration file that are relevant; optional, will
            default to all sections if not given, but some may be excluded
            via another optional parameter
        :param collections.abc.Iterable(str) exclude: analogous to the
            inclusion parameter, but for specific sections to exclude.
        """

        self._logger = logging.getLogger(
            "{}.{}".format(__name__, self.__class__.__name__))

        self.path = path_conf_file
        # TODO: could write strategy as argument if more than just YAML.
        # TODO: could also derive parsing behavior from extension.
        with open(self.path, 'r') as conf_file:
            data = yaml.safe_load(conf_file)


        sections = {include} if isinstance(include, str) else set(include or data.keys())
        excl = {exclude} if isinstance(exclude, str) else set(exclude or [])
        sections -= excl

        self._logger.info("Validating %d sections: %s",
                          len(sections), ", ".join(sections))

        self.section_to_fail_by_command = defaultdict(dict)
        self.failures_by_section = defaultdict(list)
        self.failures = set()
        for s in sections:
            try:
                section_data = data[s]
            except KeyError:
                _LOGGER.info("No section 's' in file %s, skipping", 
                             s, self.path)
                continue
            try:
                commands_iter = section_data.items()
                for name, command in commands_iter:
                    self._store_status(section=s, command=command, name=name)
            except AttributeError:
                commands_iter = data[s]
                for cmd_item in commands_iter:
                    try:
                        name, command = cmd_item
                    except ValueError:
                        name, command = "", cmd_item
                    self._store_status(section=s, command=command, name=name)


    def _store_status(self, section, command, name):
        failed = fails(command, name)
        self.section_to_fail_by_command[section][command] = failed
        if failed:
            self.failures_by_section[section].append(command)
            self.failures.add(command)


    @property
    def failed(self):
        if not self.section_to_fail_by_command:
            raise ValueError("No commands validated")
        return 0 == len(self.failures)



def fails(command, name=""):
    """
    Check if command can be called.

    :param str command: actual command to call
    :param str name: nickname/alias by which to reference the command, optional
    :return bool: whether given command's call succeeded
    """

    # Use `command` to see if command is callable, store exit code
    code = os.system(
        "command -v {0} >/dev/null 2>&1 || {{ exit 1; }}".format(command))

    if code != 0:
        _LOGGER.debug("Command{0}is not callable: {1}".
                      format("('{}')".format(name) if name else " ", command))
    return bool(code)
