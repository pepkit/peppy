""" Helpers without an obvious logical home. """

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

    # TODO:
    # It appears that this isn't currently used.
    # It could be included as a validation stage in Project instantiation.
    # If Project instance being validated lacked specific relevant
    # configuration section the call here would either need to be skipped,
    # or this would need to pass in such a scenario. That would not be
    # a challenge, but it just needs to be noted.

    # TODO:
    # Test this with additional pipeline config file,
    # pointed to in relevant section of project config file:
    # http://looper.readthedocs.io/en/latest/define-your-project.html#project-config-section-pipeline-config

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

        super(CommandChecker, self).__init__()

        self._logger = logging.getLogger(
            "{}.{}".format(__name__, self.__class__.__name__))

        # TODO: could provide parse strategy as parameter to supplement YAML.
        # TODO: could also derive parsing behavior from extension.
        self.path = path_conf_file
        with open(self.path, 'r') as conf_file:
            data = yaml.safe_load(conf_file)

        # Determine which sections to validate.
        sections = {include} if isinstance(include, str) else \
                   set(include or data.keys())
        excl = {exclude} if isinstance(exclude, str) else set(exclude or [])
        sections -= excl

        self._logger.info("Validating %d sections: %s",
                          len(sections),
                          ", ".join(["'{}'".format(s) for s in sections]))

        # Store per-command mapping of status, nested under section.
        self.section_to_status_by_command = defaultdict(dict)
        # Store only information about the failures.
        self.failures_by_section = defaultdict(list)    # Access by section.
        self.failures = set()                           # Access by command.

        for s in sections:
            # Fetch section data or skip.
            try:
                section_data = data[s]
            except KeyError:
                _LOGGER.info("No section '%s' in file '%s', skipping",
                             s, self.path)
                continue
            # Test each of the section's commands.
            try:
                # Is section's data a mapping?
                commands_iter = section_data.items()
                self._logger.debug("Processing section '%s' data "
                                   "as mapping", s)
                for name, command in commands_iter:
                    failed = self._store_status(section=s, command=command,
                                                name=name)
                    self._logger.debug("Command '%s': %s", command,
                                       "FAILURE" if failed else "SUCCESS")
            except AttributeError:
                self._logger.debug("Processing section '%s' data as list", s)
                commands_iter = data[s]
                for cmd_item in commands_iter:
                    # Item is K-V pair?
                    try:
                        name, command = cmd_item
                    except ValueError:
                        # Treat item as command itself.
                        name, command = "", cmd_item
                    success = self._store_status(section=s, command=command,
                                                 name=name)
                    self._logger.debug("Command '%s': %s", command,
                                       "SUCCESS" if success else "FAILURE")


    def _store_status(self, section, command, name):
        """
        Based on new command execution attempt, update instance's
        data structures with information about the success/fail status.
        Return the result of the execution test.
        """
        succeeded = succeeds(command, name)
        # Store status regardless of its value in the instance's largest DS.
        self.section_to_status_by_command[section][command] = succeeded
        if not succeeded:
            # Only update the failure-specific structures conditionally.
            self.failures_by_section[section].append(command)
            self.failures.add(command)
        return succeeded


    @property
    def failed(self):
        """
        Determine whether *every* command succeeded for *every* config file
        section that was validated during instance construction.

        :return bool: conjunction of execution success test result values,
            obtained by testing each executable in every validated section
        """
        # This will raise exception even if validation was attempted,
        # but no sections were used. Effectively, delegate responsibility
        # to the caller to initiate validation only if doing so is relevant.
        if not self.section_to_status_by_command:
            raise ValueError("No commands validated")
        return 0 == len(self.failures)



def succeeds(command, name=""):
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
        alias_value = " ('{}') ".format(name) if name else " "
        _LOGGER.debug("Command{0}is not callable: {1}".
                      format(alias_value, command))
    return not bool(code)
