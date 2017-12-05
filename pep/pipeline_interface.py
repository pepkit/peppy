""" Model the connection between a pipeline and a project or executor. """

import logging
import os
import sys
if sys.version_info < (3, 3):
    from collections import Mapping
else:
    from collections.abc import Mapping

import yaml

from .const import DEFAULT_COMPUTE_RESOURCES_NAME
from .utils import copy, expandpath


_LOGGER = logging.getLogger(__name__)



@copy
class PipelineInterface(object):
    """
    This class parses, holds, and returns information for a yaml file that
    specifies how to interact with each individual pipeline. This
    includes both resources to request for cluster job submission, as well as
    arguments to be passed from the sample annotation metadata to the pipeline

    :param config: path to file from which to parse configuration data,
        or pre-parsed configuration data.
    :type config: str | Mapping

    """
    def __init__(self, config):
        if isinstance(config, Mapping):
            # Unified pipeline_interface.yaml file (protocol mappings
            # and the actual pipeline interface data)
            _LOGGER.debug("Creating %s with preparsed data",
                          self.__class__.__name__)
            self.pipe_iface_file = None
            self.pipe_iface_config = config

        else:
            # More likely old-style, with protocol_mapping in its own file,
            # separate from the actual pipeline interface data
            _LOGGER.debug("Parsing '%s' for PipelineInterface config data",
                          config)
            self.pipe_iface_file = config
            with open(config, 'r') as f:
                self.pipe_iface_config = yaml.load(f)

        # Ensure that each pipeline path, if provided, is expanded.
        self._expand_paths()


    def __getitem__(self, item):
        try:
            return self._select_pipeline(item)
        except _MissingPipelineConfigurationException:
            raise KeyError("{} is not a known pipeline; known: {}".
                           format(item, self.pipe_iface_config.keys()))


    def __iter__(self):
        return iter(self.pipe_iface_config.items())


    def __repr__(self):
        source = self.pipe_iface_file or "Mapping"
        num_pipelines = len(self.pipe_iface_config)
        pipelines = ", ".join(self.pipe_iface_config.keys())
        return "{} from {}, with {} pipeline(s): {}".format(
                self.__class__.__name__, source, num_pipelines, pipelines)


    def _expand_paths(self):
        for pipe_data in self.pipe_iface_config.values():
            if "path" in pipe_data:
                pipe_path = pipe_data["path"]
                _LOGGER.log(5, "Expanding path: '%s'", pipe_path)
                pipe_path = expandpath(pipe_path)
                _LOGGER.log(5, "Expanded: '%s'", pipe_path)
                pipe_data["path"] = pipe_path


    @property
    def pipeline_names(self):
        """
        Names of pipelines about which this interface is aware.

        :return Iterable[str]: names of pipelines about which this
            interface is aware
        """
        return self.pipe_iface_config.keys()


    @property
    def pipelines(self):
        """
        Keyed collection of pipeline interface data.

        :return Mapping: pipeline interface configuration data
        """
        return self.pipe_iface_config.values()


    def choose_resource_package(self, pipeline_name, file_size):
        """
        Select resource bundle for given input file size to given pipeline.

        :param pipeline_name: Name of pipeline.
        :type pipeline_name: str
        :param file_size: Size of input data (in gigabytes).
        :type file_size: float
        :return: resource bundle appropriate for given pipeline,
            for given input file size
        :rtype: MutableMapping
        :raises ValueError: if indicated file size is negative, or if the
            file size value specified for any resource package is negative
        :raises _InvalidResourceSpecificationException: if no default
            resource package specification is provided
        """

        # Ensure that we have a numeric value before attempting comparison.
        file_size = float(file_size)

        if file_size < 0:
            raise ValueError("Attempted selection of resource package for "
                             "negative file size: {}".format(file_size))

        try:
            resources = self._select_pipeline(pipeline_name)["resources"]
        except KeyError:
            msg = "No resources for pipeline '{}'".format(pipeline_name)
            if self.pipe_iface_file is not None:
                msg += " in file '{}'".format(self.pipe_iface_file)
            _LOGGER.warn(msg)
            return {}

        # Require default resource package specification.
        try:
            default_resource_package = \
                    resources[DEFAULT_COMPUTE_RESOURCES_NAME]
        except KeyError:
            raise _InvalidResourceSpecificationException(
                "Pipeline resources specification lacks '{}' section".
                    format(DEFAULT_COMPUTE_RESOURCES_NAME))

        # Parse min file size to trigger use of a resource package.
        def file_size_ante(name, data):
            # Retrieve this package's minimum file size.
            # Retain backwards compatibility while enforcing key presence.
            try:
                fsize = data["min_file_size"]
            except KeyError:
                fsize = data["file_size"]
            fsize = float(fsize)
            # Negative file size is illogical and problematic for comparison.
            if fsize < 0:
                raise ValueError(
                        "Negative file size threshold for resource package "
                        "'{}': {}".format(name, fsize))
            return fsize

        # Enforce default package minimum of 0.
        if "file_size" in default_resource_package:
            del default_resource_package["file_size"]
        resources[DEFAULT_COMPUTE_RESOURCES_NAME]["min_file_size"] = 0

        try:
            # Sort packages by descending file size minimum to return first
            # package for which given file size satisfies the minimum.
            resource_packages = sorted(
                resources.items(),
                key=lambda name_and_data: file_size_ante(*name_and_data),
                reverse=True)
        except ValueError:
            _LOGGER.error("Unable to use file size to prioritize "
                          "resource packages: {}".format(resources))
            raise

        # "Descend" packages by min file size, choosing minimally-sufficient.
        for rp_name, rp_data in resource_packages:
            size_ante = file_size_ante(rp_name, rp_data)
            if file_size >= size_ante:
                msg = "Selected '{}' package with min file size {} Gb for file " \
                      "of size {} Gb.".format(rp_name, size_ante, file_size)
                _LOGGER.debug(msg)
                return rp_data


    def get_arg_string(self, pipeline_name, sample,
                       submission_folder_path="", **null_replacements):
        """
        For a given pipeline and sample, return the argument string.

        :param str pipeline_name: Name of pipeline.
        :param Sample sample: current sample for which job is being built
        :param str submission_folder_path: path to folder in which files
            related to submission of this sample will be placed.
        :param dict null_replacements: mapping from name of Sample attribute
            name to value to use in arg string if Sample attribute's value
            is null
        :return str: command-line argument string for pipeline
        """

        def update_argtext(argtext, option, argument):
            if argument is None or "" == argument:
                _LOGGER.debug("Skipping null/empty argument for option "
                              "'{}': {}".format(option, type(argument)))
                return argtext
            _LOGGER.debug("Adding argument for pipeline option '{}': {}".
                          format(option, argument))
            return "{} {} {}".format(argtext, option, argument)


        default_filepath = os.path.join(
                submission_folder_path, sample.generate_filename())
        _LOGGER.debug("Default sample filepath: '%s'", default_filepath)
        proxies = {"yaml_file": default_filepath}
        proxies.update(null_replacements)

        _LOGGER.debug("Building arguments string")
        config = self._select_pipeline(pipeline_name)
        argstring = ""

        if "arguments" not in config:
            _LOGGER.info("No arguments found for '%s' in '%s'",
                              pipeline_name, self.pipe_iface_file)
            return argstring

        args = config["arguments"]
        for pipe_opt, sample_attr in args.iteritems():
            if sample_attr is None:
                _LOGGER.debug("Option '%s' is not mapped to a sample "
                              "attribute, so it will be added to the pipeline "
                              "argument string as a flag-like option.",
                              str(pipe_opt))
                argstring += " {}".format(pipe_opt)
                continue

            try:
               arg = getattr(sample, sample_attr)
            except AttributeError:
                _LOGGER.error(
                        "Error (missing attribute): '%s' requires sample "
                        "attribute '%s' for option/argument '%s'",
                        pipeline_name, sample_attr, pipe_opt)
                raise

            # It's undesirable to put a null value in the argument string.
            if arg is None:
                _LOGGER.debug("Null value for sample attribute: '%s'",
                              sample_attr)
                try:
                    arg = proxies[sample_attr]
                except KeyError:
                    reason = "No default for null sample attribute: '{}'".\
                            format(sample_attr)
                    raise ValueError(reason)
                _LOGGER.debug("Found default for '{}': '{}'".
                              format(sample_attr, arg))

            argstring = update_argtext(
                    argstring, option=pipe_opt, argument=arg)

        # Add optional arguments
        if "optional_arguments" in config:
            _LOGGER.debug("Processing options")
            args = config["optional_arguments"]
            for pipe_opt, sample_attr in args.iteritems():
                _LOGGER.debug("Option '%s' maps to sample attribute '%s'",
                              pipe_opt, sample_attr)
                if sample_attr is None or sample_attr == "":
                    _LOGGER.debug("Null/empty sample attribute name for "
                                  "pipeline option '{}'".format(pipe_opt))
                    continue
                try:
                    arg = getattr(sample, sample_attr)
                except AttributeError:
                    _LOGGER.warn(
                        "> Note (missing optional attribute): '%s' requests "
                        "sample attribute '%s' for option '%s'",
                        pipeline_name, sample_attr, pipe_opt)
                    continue
                argstring = update_argtext(
                        argstring, option=pipe_opt, argument=arg)

        _LOGGER.debug("Script args: '%s'", argstring)

        return argstring


    def get_attribute(self, pipeline_name, attribute_key, path_as_list=True):
        """
        Return the value of the named attribute for the pipeline indicated.

        :param str pipeline_name: name of the pipeline of interest
        :param str attribute_key: name of the pipeline attribute of interest
        :param bool path_as_list: whether to ensure that a string attribute
            is returned as a list; this is useful for safe iteration over
            the returned value.
        """
        config = self._select_pipeline(pipeline_name)
        value = config.get(attribute_key)
        return [value] if isinstance(value, str) and path_as_list else value


    def get_pipeline_name(self, pipeline):
        """
        Translate a pipeline name (e.g., stripping file extension).

        :param pipeline: Pipeline name or script (top-level key in
            pipeline interface mapping).
        :type pipeline: str
        :return: translated pipeline name, as specified in config or by
            stripping the pipeline's file extension
        :rtype: str: translated name for pipeline
        """
        config = self._select_pipeline(pipeline)
        try:
            return config["name"]
        except KeyError:
            _LOGGER.debug("No 'name' for pipeline '{}'".format(pipeline))
            return os.path.splitext(pipeline)[0]


    def _select_pipeline(self, pipeline_name):
        """
        Check to make sure that pipeline has an entry and if so, return it.

        :param pipeline_name: Name of pipeline.
        :type pipeline_name: str
        :return: configuration data for pipeline indicated
        :rtype: Mapping
        :raises _MissingPipelineConfigurationException: if there's no
            configuration data for the indicated pipeline
        """
        try:
            # For unmapped pipeline, Return empty config instead of None.
            return self.pipe_iface_config[pipeline_name] or dict()
        except KeyError:
            _LOGGER.error(
                "Missing pipeline description: %s not found; %d known: %s",
                pipeline_name, len(self.pipe_iface_config),
                ", ".format(self.pipe_iface_config.keys()))
            # TODO: use defaults or force user to define this?
            raise _MissingPipelineConfigurationException(pipeline_name)



class _InvalidResourceSpecificationException(Exception):
    """ Pipeline interface resources--if present--needs default. """
    def __init__(self, reason):
        super(_InvalidResourceSpecificationException, self).__init__(reason)



class _MissingPipelineConfigurationException(Exception):
    """ A selected pipeline needs configuration data. """
    def __init__(self, pipeline):
        super(_MissingPipelineConfigurationException, self).__init__(pipeline)
