""" Helpers without an abvious logical home. """

from collections import defaultdict
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

        :param str path_conf_file:
        :param include:
        :param exclude:
        """
        self.path = path_conf_file
        # TODO: could write strategy as argument if more than just YAML.
        # TODO: could also derive parsing behavior from extension.
        with open(self.path, 'r') as conf_file:
            data = yaml.safe_load(conf_file)


        sections = {include} if isinstance(include, str) else set(include or data.keys())
        excl = {exclude} if isinstance(exclude, str) else set(exclude or [])
        sections -= excl

        self.section_to_fail_by_command = defaultdict(dict)
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
                    self.section_to_fail_by_command[s][command] = \
                            fails(command=command, name=name)
            except AttributeError:
                commands_iter = data[s]
                for cmd_item in commands_iter:
                    try:
                        name, cmd = cmd_item
                    except ValueError:
                        name = ""
                    self.section_to_fail_by_command[s][cmd] = \
                            fails(command=cmd, name=name)
    
    def fail(self):
        if not self.section_to_fail_by_command:
            raise ValueError("No commands validated")
        for fail_by_command in \
                self.section_to_fail_by_command.values():
            if any(fail_by_command.values()):
                return True
        return False



def fails(command, name=""):
    """
    Check if command can be called.

    :param str command: actual command to call
    :param str name: nickname/alias by which to reference the command, optional
    :return bool: whether given command's call succeded
    """

    # Use `command` to see if command is callable, store exit code
    code = os.system(
        "command -v {0} >/dev/null 2>&1 || {{ exit 1; }}".format(command))

    if code != 0:
        _LOGGER.debug("Command{0}is not callable: {1}".
                      format("('{}')".format(name) if name else " ", command))
    return bool(code)
