""" Model interface between executor, protocols, and pipelines. """

from collections import defaultdict
import inspect
import logging
import os
import sys
if sys.version_info < (3, 3):
    from collections import Mapping
else:
    from collections.abc import Mapping

import yaml

from .pipeline_interface import PipelineInterface
from .sample import Sample
from .utils import alpha_cased, copy, is_command_callable, \
    import_from_source, standard_stream_redirector


_LOGGER = logging.getLogger(__name__)



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
        if not os.path.exists(pipe_iface_location):
            _LOGGER.warn("Ignoring nonexistent pipeline interface "
                         "location: '%s'", pipe_iface_location)
            continue
        proto_iface = ProtocolInterface(pipe_iface_location)
        for proto_name in proto_iface.protomap:
            _LOGGER.log(5, "Adding protocol name: '%s'", proto_name)
            interface_by_protocol[alpha_cased(proto_name)].append(proto_iface)
    return interface_by_protocol



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

        elif os.path.isfile(interface_data_source):
            # Secondary version that passes combined yaml file directly,
            # instead of relying on separate hard-coded config names.
            _LOGGER.debug("Creating %s from file: '%s'",
                          self.__class__.__name__, interface_data_source)
            self.source = interface_data_source
            self.pipe_iface_path = self.source
            self.pipelines_path = os.path.dirname(self.source)

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

        elif os.path.isdir(interface_data_source):
            _LOGGER.debug("Creating %s from files in directory: '%s'",
                          self.__class__.__name__, interface_data_source)
            self.source = interface_data_source
            self.pipe_iface_path = os.path.join(
                    self.source, "config", "pipeline_interface.yaml")
            self.pipelines_path = os.path.join(self.source, "pipelines")

            self.pipe_iface = PipelineInterface(self.pipe_iface_path)
            self.protomap = ProtocolMapper(os.path.join(
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
            script_path_only = os.path.expanduser(os.path.expandvars(full_pipe_path[0].strip()))
            if os.path.isdir(script_path_only):
                script_path_only = os.path.join(script_path_only, pipeline_key)
            script_path_with_flags = \
                    "{} {}".format(script_path_only, pipeline_key_args)
        else:
            # backwards compatibility w/ v0.5
            script_path_only = strict_pipeline_key
            script_path_with_flags = pipeline_key 

        # Clear trailing whitespace.
        script_path_only = script_path_only.rstrip()

        if not os.path.isabs(script_path_only) and not \
                is_command_callable(script_path_only):
            _LOGGER.log(5, "Expanding non-absolute script path: '%s'",
                        script_path_only)
            script_path_only = os.path.join(
                    self.pipelines_path, script_path_only)
            _LOGGER.log(5, "Absolute script path: '%s'", script_path_only)
            script_path_with_flags = os.path.join(
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
        """ Indexing syntax is on protocol name. """
        return self.mappings[protocol_name]

    def __iter__(self):
        """ Iteration is over the protocol names. """
        return iter(self.mappings)

    def __len__(self):
        """ The interface size is the number of protocol names supported. """
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
        :return list[str]: Sequence of pipelines capable of handling a sample
            of the indicated protocol.
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
        """
        Message about job(s) associated with a particular protocol.

        :param str job: a string of information about job(s)
        :param obj dep: dependency specification
        """
        job = job.replace("(", "").replace(")", "")
        split_jobs = [x.strip() for x in job.split(',')]
        if len(split_jobs) > 1:
            for s in split_jobs:
                self.register_job(s, dep)
        else:
            self.register_job(job, dep)


    @staticmethod
    def register_job(job, dep):
        """ Provide a message about a particular job's registration. """
        _LOGGER.info("Register Job Name: %s\tDep: %s", str(job), str(dep))



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

    _, ext = os.path.splitext(pipeline_filepath)
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
            with open(os.devnull, 'w') as temp_standard_streams:
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
