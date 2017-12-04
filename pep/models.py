"""
Project Models
=======================

Workflow explained:
    - Create a Project object
        - Samples are created and added to project (automatically)

In the process, Models will check:
    - Project structure (created if not existing)
    - Existence of csv sample sheet with minimal fields
    - Constructing a path to a sample's input file and checking for its existence
    - Read type/length of samples (optionally)

Example:

.. code-block:: python

    from models import Project
    prj = Project("config.yaml")
    # that's it!

Explore:

.. code-block:: python

    # see all samples
    prj.samples
    # get fastq file of first sample
    prj.samples[0].fastq
    # get all bam files of WGBS samples
    [s.mapped for s in prj.samples if s.protocol == "WGBS"]

    prj.metadata.results  # results directory of project
    # export again the project's annotation
    prj.sheet.write(os.path.join(prj.metadata.output_dir, "sample_annotation.csv"))

    # project options are read from the config file
    # but can be changed on the fly:
    prj = Project("test.yaml")
    # change options on the fly
    prj.config["merge_technical"] = False
    # annotation sheet not specified initially in config file
    prj.add_sample_sheet("sample_annotation.csv")

"""

# TODO: perhaps update examples based on removal of guarantee of some attrs.
# TODO: the examples changes would involve library and output_dir.

from collections import \
    Counter, defaultdict, Iterable, Mapping, MutableMapping, namedtuple, \
    OrderedDict as _OrderedDict
from functools import partial
import glob
import inspect
import itertools
import logging
from operator import itemgetter
import os as _os
import warnings

import pandas as _pd
import yaml

from .const import *
from .utils import \
    add_project_sample_constants, alpha_cased, check_bam, check_fastq, \
    expandpath, get_file_size, grab_project_data, import_from_source, \
    is_command_callable, parse_ftype, partition, sample_folder, \
    standard_stream_redirector


# TODO: decide if we want to denote functions for export.
__functions__ = []


MAX_PROJECT_SAMPLES_REPR = 12

_LOGGER = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    _LOGGER.addHandler(logging.NullHandler())



def check_sheet(sample_file, dtype=str):
    """
    Check if csv file exists and has all required columns.

    :param str sample_file: path to sample annotations file.
    :param type dtype: data type for CSV read.
    :raises IOError: if given annotations file can't be read.
    :raises ValueError: if required column(s) is/are missing.
    """
    # Although no null value replacements or supplements are being passed,
    # toggling the keep_default_na value to False solved an issue with 'nan'
    # and/or 'None' as an argument for an option in the pipeline command
    # that's generated from a Sample's attributes.
    #
    # See https://github.com/pepkit/pep/issues/159 for the original issue
    # and https://github.com/pepkit/pep/pull/160 for the pull request
    # that resolved it.
    df = _pd.read_table(sample_file, sep=None, dtype=dtype,
                        index_col=False, engine="python", keep_default_na=False)
    req = [SAMPLE_NAME_COLNAME]
    missing = set(req) - set(df.columns)
    if len(missing) != 0:
        raise ValueError(
            "Annotation sheet ('{}') is missing column(s): {}; has: {}".
                format(sample_file, missing, df.columns))
    return df



def process_pipeline_interfaces(pipeline_interface_locations):
    """
    Create a ProtocolInterface for each pipeline location given.

    :param Iterable[str] pipeline_interface_locations: locations, each of
        which should be either a directory path or a filepath, that specifies
        pipeline interface and protocol mappings information. Each such file
        should be have a pipelines section and a protocol mappings section
        whereas each folder should have a file for each of those sections.
    :return Mapping[str, Iterable[ProtocolInterface]]: mapping from protocol
        name to interface(s) for which that protocol is mapped
    """
    interface_by_protocol = defaultdict(list)
    for pipe_iface_location in pipeline_interface_locations:
        if not _os.path.exists(pipe_iface_location):
            _LOGGER.warn("Ignoring nonexistent pipeline interface "
                         "location: '%s'", pipe_iface_location)
            continue
        proto_iface = ProtocolInterface(pipe_iface_location)
        for proto_name in proto_iface.protomap:
            _LOGGER.log(5, "Adding protocol name: '%s'", proto_name)
            interface_by_protocol[alpha_cased(proto_name)].append(proto_iface)
    return interface_by_protocol



# Collect PipelineInterface, Sample type, pipeline path, and script with flags.
SubmissionBundle = namedtuple(
    "SubmissionBundle",
    field_names=["interface", "subtype", "pipeline", "pipeline_with_flags"])
SUBMISSION_BUNDLE_PIPELINE_KEY_INDEX = 2


class IFilteredRepr(object):
    def __repr__(self):
        return




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


        default_filepath = _os.path.join(
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
            return _os.path.splitext(pipeline)[0]


    def uses_looper_args(self, pipeline_name):
        """
        Determine whether the indicated pipeline uses looper arguments.

        :param pipeline_name: name of a pipeline of interest
        :type pipeline_name: str
        :return: whether the indicated pipeline uses looper arguments
        :rtype: bool
        """
        config = self._select_pipeline(pipeline_name)
        return "looper_args" in config and config["looper_args"]


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



class ProtocolInterface(object):
    """ PipelineInterface and ProtocolMapper for a single pipelines location.

    This class facilitates use of pipelines from multiple locations by a
    single project. Also stored are path attributes with information about
    the location(s) from which the PipelineInterface and ProtocolMapper came.

    :param interface_data_source: location (e.g., code repository) of pipelines
    :type interface_data_source: str | Mapping

    """

    SUBTYPE_MAPPING_SECTION = "sample_subtypes"


    def __init__(self, interface_data_source):
        super(ProtocolInterface, self).__init__()

        if isinstance(interface_data_source, Mapping):
            # TODO: for implementation, we need to determine pipelines_path.
            raise NotImplementedError(
                    "Raw Mapping as source of {} data is not yet supported".
                    format(self.__class__.__name__))
            _LOGGER.debug("Creating %s from raw Mapping",
                          self.__class__.__name__)
            self.source = None
            self.pipe_iface_path = None
            for name, value in self._parse_iface_data(interface_data_source):
                setattr(self, name, value)

        elif _os.path.isfile(interface_data_source):
            # Secondary version that passes combined yaml file directly,
            # instead of relying on separate hard-coded config names.
            _LOGGER.debug("Creating %s from file: '%s'",
                          self.__class__.__name__, interface_data_source)
            self.source = interface_data_source
            self.pipe_iface_path = self.source
            self.pipelines_path = _os.path.dirname(self.source)

            with open(interface_data_source, 'r') as interface_file:
                iface = yaml.load(interface_file)
            try:
                iface_data = self._parse_iface_data(iface)
            except Exception:
                _LOGGER.error("Error parsing data from pipeline interface "
                              "file: %s", interface_data_source)
                raise
            for name, value in iface_data:
                setattr(self, name, value)

        elif _os.path.isdir(interface_data_source):
            _LOGGER.debug("Creating %s from files in directory: '%s'",
                          self.__class__.__name__, interface_data_source)
            self.source = interface_data_source
            self.pipe_iface_path = _os.path.join(
                    self.source, "config", "pipeline_interface.yaml")
            self.pipelines_path = _os.path.join(self.source, "pipelines")

            self.pipe_iface = PipelineInterface(self.pipe_iface_path)
            self.protomap = ProtocolMapper(_os.path.join(
                    self.source, "config", "protocol_mappings.yaml"))

        else:
            raise ValueError("Alleged pipelines location '{}' exists neither "
                             "as a file nor as a folder.".
                             format(interface_data_source))


    def __repr__(self):
        return "ProtocolInterface from '{}'".format(self.source or "Mapping")


    def fetch_pipelines(self, protocol):
        """
        Fetch the mapping for a particular protocol, null if unmapped.

        :param str protocol: name/key for the protocol for which to fetch the
            pipeline(s)
        :return str | Iterable[str] | NoneType: pipeline(s) to which the given
            protocol is mapped, otherwise null
        """
        return self.protomap.mappings.get(alpha_cased(protocol))


    def fetch_sample_subtype(
            self, protocol, strict_pipe_key, full_pipe_path):
        """
        Determine the interface and Sample subtype for a protocol and pipeline.

        :param str protocol: name of the relevant protocol
        :param str strict_pipe_key: key for specific pipeline in a pipeline
            interface mapping declaration; this must exactly match a key in
            the PipelineInterface (or the Mapping that represent it)
        :param str full_pipe_path: (absolute, expanded) path to the
            pipeline script
        :return type: Sample subtype to use for jobs for the given protocol,
            that use the pipeline indicated
        :raises KeyError: if given a pipeline key that's not mapped in this
            ProtocolInterface instance's PipelineInterface
        """

        subtype = None

        this_pipeline_data = self.pipe_iface[strict_pipe_key]

        try:
            subtypes = this_pipeline_data[self.SUBTYPE_MAPPING_SECTION]
        except KeyError:
            _LOGGER.debug("%s from '%s' doesn't define section '%s' "
                          "for pipeline '%s'",
                          self.pipe_iface.__class__.__name__, self.source,
                          self.SUBTYPE_MAPPING_SECTION, strict_pipe_key)
            # Without a subtypes section, if pipeline module defines a single
            # Sample subtype, we'll assume that type is to be used when in
            # this case, when the interface section for this pipeline lacks
            # an explicit subtypes section specification.
            subtype_name = None
        else:
            if subtypes is None:
                # Designate lack of need for import attempt and provide
                # class with name to format message below.
                subtype = Sample
                _LOGGER.debug("Null %s subtype(s) section specified for "
                              "pipeline: '%s'; using base %s type",
                              subtype.__name__, strict_pipe_key,
                              subtype.__name__)
            elif isinstance(subtypes, str):
                subtype_name = subtypes
                _LOGGER.debug("Single subtype name for pipeline '%s' "
                              "in interface from '%s': '%s'", subtype_name,
                              strict_pipe_key, self.source)
            else:
                temp_subtypes = {
                        alpha_cased(p): st for p, st in subtypes.items()}
                try:
                    subtype_name = temp_subtypes[alpha_cased(protocol)]
                except KeyError:
                    # Designate lack of need for import attempt and provide
                    # class with name to format message below.
                    subtype = Sample
                    _LOGGER.debug("No %s subtype specified in interface from "
                                  "'%s': '%s', '%s'; known: %s",
                                  subtype.__name__, self.source,
                                  strict_pipe_key, protocol,
                                  ", ".join(temp_subtypes.keys()))

        # subtype_name is defined if and only if subtype remained null.
        # The import helper function can return null if the import attempt
        # fails, so provide the base Sample type as a fallback.
        subtype = subtype or \
                  _import_sample_subtype(full_pipe_path, subtype_name) or \
                  Sample
        _LOGGER.debug("Using Sample subtype: %s", subtype.__name__)
        return subtype


    def finalize_pipeline_key_and_paths(self, pipeline_key):
        """
        Determine pipeline's full path, arguments, and strict key.

        This handles multiple ways in which to refer to a pipeline (by key)
        within the mapping that contains the data that defines a
        PipelineInterface. It also ensures proper handling of the path to the
        pipeline (i.e., ensuring that it's absolute), and that the text for
        the arguments are appropriately dealt parsed and passed.

        :param str pipeline_key: the key in the pipeline interface file used
            for the protocol_mappings section. Previously was the script name.
        :return (str, str, str): more precise version of input key, along with
            absolute path for pipeline script, and full script path + options

        """

        # The key may contain extra command-line flags; split key from flags.
        # The strict key is the script name itself, something like "ATACseq.py"
        strict_pipeline_key, _, pipeline_key_args = pipeline_key.partition(' ')

        full_pipe_path = \
                self.pipe_iface.get_attribute(strict_pipeline_key, "path")
        if full_pipe_path:
            script_path_only = _os.path.expanduser(_os.path.expandvars(full_pipe_path[0].strip()))
            if _os.path.isdir(script_path_only):
                script_path_only = _os.path.join(script_path_only, pipeline_key)
            script_path_with_flags = \
                    "{} {}".format(script_path_only, pipeline_key_args)
        else:
            # backwards compatibility w/ v0.5
            script_path_only = strict_pipeline_key
            script_path_with_flags = pipeline_key 

        # Clear trailing whitespace.
        script_path_only = script_path_only.rstrip()

        if not _os.path.isabs(script_path_only) and not \
                is_command_callable(script_path_only):
            _LOGGER.log(5, "Expanding non-absolute script path: '%s'",
                        script_path_only)
            script_path_only = _os.path.join(
                    self.pipelines_path, script_path_only)
            _LOGGER.log(5, "Absolute script path: '%s'", script_path_only)
            script_path_with_flags = _os.path.join(
                    self.pipelines_path, script_path_with_flags)
            _LOGGER.log(5, "Absolute script path with flags: '%s'",
                        script_path_with_flags)

        return strict_pipeline_key, script_path_only, script_path_with_flags


    @classmethod
    def _parse_iface_data(cls, pipe_iface_data):
        """
        Parse data from mappings to set instance attributes.

        The data that define a ProtocolInterface are a "protocol_mapping"
        Mapping and a "pipelines" Mapping, which are used to create a
        ProtocolMapper and a PipelineInterface, representing the configuration
        data for pipeline(s) from a single location. There are a couple of
        different ways (file, folder, and eventually, raw Mapping) to provide
        this data, and this function provides some standardization to how
        those data are processed, independent of input type/format.

        :param Mapping[str, Mapping] pipe_iface_data: mapping from section
            name to section data mapping; more specifically, the protocol
            mappings Mapping and the PipelineInterface mapping
        :return list[(str, ProtocolMapper | PipelineInterface)]: pairs of
            attribute name for the ProtocolInterface being created, and the
            value for that attribute,
        """
        assignments = [("protocol_mapping", ProtocolMapper, "protomap"),
                       ("pipelines", PipelineInterface, "pipe_iface")]
        attribute_values = []
        for section_name, data_type, attr_name in assignments:
            try:
                data = pipe_iface_data[section_name]
            except KeyError:
                _LOGGER.error("Error creating %s from data: %s",
                              cls.__name__, str(pipe_iface_data))
                raise Exception("PipelineInterface file lacks section: '{}'".
                                format(section_name))
            attribute_values.append((attr_name, data_type(data)))
        return attribute_values



@copy
class ProtocolMapper(Mapping):
    """
    Map protocol/library name to pipeline key(s). For example, "WGBS" --> wgbs.

    :param mappings_input: data encoding correspondence between a protocol
        name and pipeline(s)
    :type mappings_input: str | Mapping

    """
    def __init__(self, mappings_input):
        if isinstance(mappings_input, Mapping):
            mappings = mappings_input
            self.filepath = None
        else:
            # Parse file mapping protocols to pipeline(s).
            with open(mappings_input, 'r') as mapfile:
                mappings = yaml.load(mapfile)
            self.filepath = mappings_input
        self.mappings = {alpha_cased(k): v for k, v in mappings.items()}


    def __getitem__(self, protocol_name):
        return self.mappings[protocol_name]

    def __iter__(self):
        return iter(self.mappings)

    def __len__(self):
        return len(self.mappings)


    def __repr__(self):
        source = self.filepath or "mapping"
        num_protocols = len(self.mappings)
        protocols = ", ".join(self.mappings.keys())
        return "{} from {}, with {} protocol(s): {}".format(
                self.__class__.__name__, source, num_protocols, protocols)


    def build_pipeline(self, protocol):
        """
        Create command-line text for given protocol's pipeline(s).

        :param str protocol: Name of protocol.
        """

        _LOGGER.debug("Building pipeline for protocol '%s'", protocol)

        if protocol not in self.mappings:
            _LOGGER.warn(
                    "Missing Protocol Mapping: '%s' is not found in '%s'",
                    protocol, self.mappings_file)
            return []

        # First list level
        split_jobs = [x.strip() for x in self.mappings[protocol].split(';')]
        return split_jobs  # hack works if no parallelism

        # Placeholder for parallelism.
        """
        for i in range(0, len(split_jobs)):
            if i == 0:
                self.parse_parallel_jobs(split_jobs[i], None)
            else:
                self.parse_parallel_jobs(split_jobs[i], split_jobs[i - 1])
        """


    def parse_parallel_jobs(self, job, dep):
        job = job.replace("(", "").replace(")", "")
        split_jobs = [x.strip() for x in job.split(',')]
        if len(split_jobs) > 1:
            for s in split_jobs:
                self.register_job(s, dep)
        else:
            self.register_job(job, dep)


    def register_job(self, job, dep):
        _LOGGER.info("Register Job Name: %s\tDep: %s", str(job), str(dep))



class _InvalidResourceSpecificationException(Exception):
    """ Pipeline interface resources--if present--needs default. """
    def __init__(self, reason):
        super(_InvalidResourceSpecificationException, self).__init__(reason)



class _MissingMetadataException(Exception):
    """ Project needs certain metadata. """
    def __init__(self, missing_section, path_config_file=None):
        reason = "Project configuration lacks required metadata section {}".\
                format(missing_section)
        if path_config_file:
            reason += "; used config file '{}'".format(path_config_file)
        super(_MissingMetadataException, self).__init__(reason)



class _MissingPipelineConfigurationException(Exception):
    """ A selected pipeline needs configuration data. """
    def __init__(self, pipeline):
        super(_MissingPipelineConfigurationException, self).__init__(pipeline)



def _import_sample_subtype(pipeline_filepath, subtype_name=None):
    """
    Import a particular Sample subclass from a Python module.

    :param str pipeline_filepath: path to file to regard as Python module
    :param str subtype_name: name of the target class (which must derive from
        the base Sample class in order for it to be used), optional; if
        unspecified, if the module defines a single subtype, then that will
        be used; otherwise, the base Sample type will be used.
    :return type: the imported class, defaulting to base Sample in case of
        failure with the import or other logic
    """
    base_type = Sample

    _, ext = _os.path.splitext(pipeline_filepath)
    if ext != ".py":
        return base_type

    try:
        _LOGGER.debug("Attempting to import module defined by {}".
                      format(pipeline_filepath))

        # TODO: consider more fine-grained control here. What if verbose
        # TODO: logging is only to file, not to stdout/err?

        # Redirect standard streams during the import to prevent noisy
        # error messaging in the shell that may distract or confuse a user.
        if _LOGGER.getEffectiveLevel() > logging.DEBUG:
            with open(_os.devnull, 'w') as temp_standard_streams:
                with standard_stream_redirector(temp_standard_streams):
                    pipeline_module = import_from_source(pipeline_filepath)
        else:
            pipeline_module = import_from_source(pipeline_filepath)

    except SystemExit:
        # SystemExit would be caught as BaseException, but SystemExit is
        # particularly suggestive of an a script without a conditional
        # check on __main__, and as such warrant a tailored message.
        _LOGGER.warn("'%s' appears to attempt to run on import; "
                     "does it lack a conditional on '__main__'? "
                     "Using base type: %s",
                     pipeline_filepath, base_type.__name__)
        return base_type

    except (BaseException, Exception) as e:
        _LOGGER.warn("Using base %s because of failure in attempt to "
                     "import pipeline module '%s': %r",
                     base_type.__name__, pipeline_filepath, e)
        return base_type

    else:
        _LOGGER.debug("Successfully imported pipeline module '%s', "
                      "naming it '%s'", pipeline_filepath,
                      pipeline_module.__name__)

    def class_names(cs):
        return ", ".join([c.__name__ for c in cs])

    # Find classes from pipeline module and determine which derive from Sample.
    classes = _fetch_classes(pipeline_module)
    _LOGGER.debug("Found %d classes: %s", len(classes), class_names(classes))

    # Base Sample could be imported; we want the true subtypes.
    proper_subtypes = _proper_subtypes(classes, base_type)
    _LOGGER.debug("%d proper %s subtype(s): %s", len(proper_subtypes),
                  base_type.__name__, class_names(proper_subtypes))

    # Determine course of action based on subtype request and number found.
    if not subtype_name:
        _LOGGER.debug("No specific subtype is requested from '%s'",
                      pipeline_filepath)
        if len(proper_subtypes) == 1:
            # No specific request and single subtype --> use single subtype.
            subtype = proper_subtypes[0]
            _LOGGER.debug("Single %s subtype found in '%s': '%s'",
                          base_type.__name__, pipeline_filepath,
                          subtype.__name__)
            return subtype
        else:
            # We can't arbitrarily select from among 0 or multiple subtypes.
            # Note that this text is used in the tests, as validation of which
            # branch of the code in this function is being hit in order to
            # return the base Sample type. If it changes, the corresponding
            # tests will also need to change.
            _LOGGER.debug("%s subtype cannot be selected from %d found in "
                          "'%s'; using base type", base_type.__name__,
                          len(proper_subtypes), pipeline_filepath)
            return base_type
    else:
        # Specific subtype request --> look for match.
        for st in proper_subtypes:
            if st.__name__ == subtype_name:
                _LOGGER.debug("Successfully imported %s from '%s'",
                              subtype_name, pipeline_filepath)
                return st
        raise ValueError(
                "'{}' matches none of the {} {} subtype(s) defined "
                "in '{}': {}".format(subtype_name, len(proper_subtypes),
                                     base_type.__name__, pipeline_filepath,
                                     class_names(proper_subtypes)))



def _fetch_classes(mod):
    """ Return the classes defined in a module. """
    try:
        _, classes = zip(*inspect.getmembers(
                mod, lambda o: inspect.isclass(o)))
    except ValueError:
        return []
    return list(classes)



def _proper_subtypes(types, supertype):
    """ Determine the proper subtypes of a supertype. """
    return list(filter(
            lambda t: issubclass(t, supertype) and t != supertype, types))



def _is_member(item, items):
    """ Determine whether an iterm is a member of a collection. """
    return item in items
