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
    [s.mapped for s in prj.samples if s.library == "WGBS"]

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
    defaultdict, Iterable, Mapping, MutableMapping, namedtuple, \
    OrderedDict as _OrderedDict
from functools import partial
import glob
import itertools
import logging
import os as _os
import sys
if sys.version_info < (3, 0):
    from urlparse import urlparse
else:
    from urllib.parse import urlparse

import pandas as _pd
import yaml

from .utils import \
    alpha_cased, check_bam, check_fastq, get_file_size, \
    import_from_source, parse_ftype, partition


COMPUTE_SETTINGS_VARNAME = "PEPENV"
DEFAULT_COMPUTE_RESOURCES_NAME = "default"
DATA_SOURCE_COLNAME = "data_source"
SAMPLE_NAME_COLNAME = "sample_name"
SAMPLE_ANNOTATIONS_KEY = "sample_annotation"
IMPLICATIONS_DECLARATION = "implied_columns"
DATA_SOURCES_SECTION = "data_sources"
SAMPLE_EXECUTION_TOGGLE = "toggle"
COL_KEY_SUFFIX = "_key"

ATTRDICT_METADATA = {"_force_nulls": False, "_attribute_identity": False}

_LOGGER = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    _LOGGER.addHandler(logging.NullHandler())



def copy(obj):
    def copy(self):
        """
        Copy self to a new object.
        """
        from copy import deepcopy

        return deepcopy(self)
    obj.copy = copy
    return obj



def is_url(maybe_url):
    return urlparse(maybe_url).scheme != ""



def include_in_repr(attr, klazz):
    return attr not in \
           {"Project": ["sheet", "interfaces_by_protocol"]}[klazz.__name__]



class PepYamlRepresenter(yaml.representer.Representer):
    """ Should object's YAML representation fail, get additional info. """

    def represent_data(self, data):
        """
        Supplement PyYAML's context info in case of representation failure.

        :param object data: same as superclass
        :return object: same as superclass
        """
        try:
            return super(PepYamlRepresenter, self).represent_data(data)
        except yaml.representer.RepresenterError:
            _LOGGER.error("YAML representation error: {} ({})".
                          format(data, type(data)))
            raise


# Bespoke YAML dumper, using the custom data/object Representer.
PepYamlDumper = type("PepYamlDumper",
                     (yaml.emitter.Emitter, yaml.serializer.Serializer,
                      PepYamlRepresenter, yaml.resolver.Resolver),
                     dict(yaml.dumper.Dumper.__dict__))



@copy
class Paths(object):
    """ A class to hold paths as attributes. """

    def __getitem__(self, key):
        """
        Provides dict-style access to attributes
        """
        return getattr(self, key)

    def __iter__(self):
        """
        Iteration is over the paths themselves.
        
        Note that this implementation constrains the assignments to be 
        non-nested. That is, the value for any attribute attached to the 
        instance should be a path.
        
        """
        return iter(self.__dict__.values())

    def __repr__(self):
        return "Paths object."



@copy
class AttributeDict(MutableMapping):
    """
    A class to convert a nested mapping(s) into an object(s) with key-values
    using object syntax (attr_dict.attribute) instead of getitem syntax 
    (attr_dict["key"]). This class recursively sets mappings to objects, 
    facilitating attribute traversal (e.g., attr_dict.attr.attr).
    """

    def __init__(self, entries=None,
                 _force_nulls=False, _attribute_identity=False):
        """
        Establish a logger for this instance, set initial entries,
        and determine behavior with regard to null values and behavior
        for attribute requests.

        :param collections.Iterable | collections.Mapping entries: collection
            of key-value pairs, initial data for this mapping
        :param bool _force_nulls: whether to allow a null value to overwrite
            an existing non-null value
        :param bool _attribute_identity: whether to return attribute name
            requested rather than exception when unset attribute/key is queried
        """
        # Null value can squash non-null?
        self.__dict__["_force_nulls"] = _force_nulls
        # Return requested attribute name if not set?
        self.__dict__["_attribute_identity"] = _attribute_identity
        if entries:
            self.add_entries(entries)


    def add_entries(self, entries):
        """
        Update this `AttributeDict` with provided key-value pairs.

        :param collections.Iterable | collections.Mapping entries: collection
            of pairs of keys and values
        """
        _LOGGER.log(5, "Adding entries {}".format(entries))
        # Permit mapping-likes and iterables/generators of pairs.
        if callable(entries):
            entries = entries()
        try:
            entries_iter = entries.items()
        except AttributeError:
            entries_iter = entries
        # Assume we now have pairs; allow corner cases to fail hard here.
        for key, value in entries_iter:
            self.__setitem__(key, value)


    def __setattr__(self, key, value):
        self.__setitem__(key, value)


    def __getattr__(self, item, default=None):
        """
        Fetch the value associated with the provided identifier.

        :param int | str item: identifier for value to fetch
        :return object: whatever value corresponds to the requested key/item
        :raises AttributeError: if the requested item has not been set,
            no default value is provided, and this instance is not configured
            to return the requested key/item itself when it's missing; also,
            if the requested item is unmapped and appears to be protected,
            i.e. by flanking double underscores, then raise AttributeError
            anyway. More specifically, respect attribute naming that appears
            to be indicative of the intent of protection.
        """
        try:
            return super(AttributeDict, self).__getattribute__(item)
        except AttributeError:
            pass
        try:
            # Fundamentally, this is still a mapping;
            # route object notation access pattern accordingly.
            # Ideally, the requested item maps to a value.
            return self.__dict__[item]
        except KeyError:
            # If not, arbitrage and cope accordingly.
            if item.startswith("__") and item.endswith("__"):
                # Some libraries use exception for protected attribute
                # access as a control flow mechanism.
                error_reason = "Protected-looking attribute: {}".format(item)
                raise AttributeError(error_reason)
            if default is not None:
                # For compatibility with ordinary getattr() invocation, allow
                # caller the ability to provide a default value.
                return default
            if self.__dict__.setdefault("_attribute_identity", False):
                # Check if we should return the attribute name as the value.
                return item
            # Throw up our hands in despair and resort to exception behavior.
            raise AttributeError(item)


    def __setitem__(self, key, value):
        """
        This is the key to making this a unique data type. Flag set at
        time of construction determines whether it's possible for a null
        value to squash a non-null value. The combination of that flag and
        one indicating whether request for value for unset attribute should
        return the attribute name itself determines if any attribute/key
        may be set to a null value.

        :param str key: name of the key/attribute for which to establish value
        :param object value: value to which set the given key; if the value is
            a mapping-like object, other keys' values may be combined.
        :raises _MetadataOperationException: if attempt is made
            to set value for privileged metadata key
        """
        _LOGGER.log(5, "Executing __setitem__ for '{}', '{}'".
                    format(key, str(value)))
        if isinstance(value, Mapping):
            try:
                # Combine AttributeDict instances.
                _LOGGER.log(5, "Updating key: '{}'".format(key))
                self.__dict__[key].add_entries(value)
            except (AttributeError, KeyError):
                # Create new AttributeDict, replacing previous value.
                self.__dict__[key] = AttributeDict(value)
            _LOGGER.log(5, "'{}' now has keys {}".
                          format(key, self.__dict__[key].keys()))
        elif value is not None or \
                key not in self.__dict__ or self.__dict__["_force_nulls"]:
            _LOGGER.log(5, "Setting '{}' to {}".format(key, value))
            self.__dict__[key] = value
        else:
            _LOGGER.log(5, "Not setting {k} to {v}; _force_nulls: {nulls}".
                        format(k=key, v=value,
                               nulls=self.__dict__["_force_nulls"]))


    def __getitem__(self, item):
        try:
            # Ability to return requested item name itself is delegated.
            return self.__getattr__(item)
        except AttributeError:
            # Requested item is unknown, but request was made via
            # __getitem__ syntax, not attribute-access syntax.
            raise KeyError(item)

    def __delitem__(self, item):
        if item in ATTRDICT_METADATA:
            raise _MetadataOperationException(self, item)
        try:
            del self.__dict__[item]
        except KeyError:
            _LOGGER.debug("No item {} to delete".format(item))

    def __eq__(self, other):
        try:
            # Ensure target itself and any values are AttributeDict.
            other = AttributeDict(other)
        except Exception:
            return False
        if len(self) != len(other):
            # Ensure we don't have to worry about other containing self.
            return False
        for k, v in self.items():
            try:
                if v != other[k]:
                    return False
            except KeyError:
                return  False
        return True

    def __ne__(self, other):
        return not self == other

    def __iter__(self):
        return iter([k for k in self.__dict__.keys()
                     if k not in ATTRDICT_METADATA])

    def __len__(self):
        return sum(1 for _ in iter(self))

    def __repr__(self):
        return repr(self.__dict__)



def process_pipeline_interfaces(pipeline_interface_locations):
    """
    Create a ProtocolInterface for each pipeline location given.
    
    :param Iterable[str] pipeline_interface_locations: locations, each of
        which should be either a directory path or a filepath, that specifies
        pipeline interface and protocol mappings information. Each such file
        should be have a pipelines section and a protocol mappings section
        whereas each folder should have a file for each of those sections.
    :return Mapping[str, ProtocolInterface]: mapping from protocol name to
        interface(s) for which that protocol is mapped
    """
    ifproto_by_proto_name = defaultdict(list)
    for pipe_iface_location in pipeline_interface_locations:
        if not _os.path.exists(pipe_iface_location):
            _LOGGER.warn("Ignoring nonexistent pipeline interface "
                         "location '%s'", pipe_iface_location)
            continue
        proto_iface = ProtocolInterface(pipe_iface_location)
        for proto_name in proto_iface.protomap:
            _LOGGER.log(5, "Adding protocol name: '%s'", proto_name)
            ifproto_by_proto_name[alpha_cased(proto_name)].append(proto_iface)
    return ifproto_by_proto_name



# Collect PipelineInterface, Sample type, pipeline path, and script with flags.
SubmissionBundle = namedtuple(
        "SubmissionBundle",
        field_names=["interface", "subtype", "pipeline", "pipeline_with_flags"])



def merge_sample(sample, merge_table, data_sources, derived_columns):
    """
    Use merge table data to augment/modify Sample.

    :param Sample sample: sample to modify via merge table data
    :param merge_table: data with which to alter Sample
    :param Mapping data_sources: collection of named paths to data locations
    :param derived_columns: names of columns with data-derived value
    :return Sample: updated input instance
    """

    if SAMPLE_NAME_COLNAME not in merge_table.columns:
        raise KeyError(
            "Merge table requires a column named '{}'.".
            format(SAMPLE_NAME_COLNAME))

    sample_indexer = merge_table[SAMPLE_NAME_COLNAME] == \
                     getattr(sample, SAMPLE_NAME_COLNAME)
    merge_rows = merge_table[sample_indexer]

    if len(merge_rows) > 0:
        # For each row in the merge table of this sample:
        # 1) populate any derived columns
        # 2) derived columns --> space-delimited strings
        # 3) update the sample values with the merge table

        # Keep track of merged cols,
        # so we don't re-derive them later.
        merged_cols = {
            key: "" for key in merge_rows.columns}
        for _, row in merge_rows.iterrows():
            row_dict = row.to_dict()
            for col in merge_rows.columns:
                if col == SAMPLE_NAME_COLNAME or \
                                col not in derived_columns:
                    continue
                # Initialize key in parent dict.
                col_key = col + COL_KEY_SUFFIX
                merged_cols[col_key] = ""
                row_dict[col_key] = row_dict[col]
                row_dict[col] = sample.locate_data_source(
                        data_sources, col, row_dict[col], row_dict)  # 1)

            # Also add in any derived cols present.
            for col in derived_columns:
                # Skip over attributes that the sample
                # either lacks, and those covered by the
                # data from the current (row's) data.
                if not hasattr(sample, col) or \
                                col in row_dict:
                    continue
                # Map column name key to sample's value
                # for the attribute given by column name.
                col_key = col + COL_KEY_SUFFIX
                row_dict[col_key] = getattr(sample, col)
                # Map the column name itself to the
                # populated data source template string.
                row_dict[col] = sample.locate_data_source(
                        data_sources, col, getattr(sample, col), row_dict)
                _LOGGER.debug("PROBLEM adding derived column: "
                              "{}, {}, {}".format(col, row_dict[col],
                                                  getattr(sample, col)))

            # Since we are now jamming multiple (merged)
            # entries into a single attribute, we have to
            # join them into a space-delimited string
            # and then set to sample attribute.
            for key, val in row_dict.items():
                if key == SAMPLE_NAME_COLNAME or not val:
                    continue
                _LOGGER.debug("merge: sample '%s'; %s=%s",
                              str(sample.name),  str(key), str(val))
                if not key in merged_cols:
                    new_val = str(val).rstrip()
                else:
                    new_val = "{} {}".format(
                        merged_cols[key], str(val)).strip()
                merged_cols[key] = new_val  # 2)

        # Don't update sample_name.
        merged_cols.pop(SAMPLE_NAME_COLNAME, None)

        sample.update(merged_cols)  # 3)
        sample.merged = True  # mark sample as merged
        sample.merged_cols = merged_cols

    return sample



@copy
class Project(AttributeDict):
    """
    A class to model a Project.

    :param config_file: Project config file (YAML).
    :type config_file: str
    :param subproject: Subproject to use within configuration file, optional
    :type subproject: str
    :param default_compute: Configuration file (YAML) for 
        default compute settings.
    :type default_compute: str
    :param dry: If dry mode is activated, no directories 
        will be created upon project instantiation.
    :type dry: bool
    :param permissive: Whether a error should be thrown if 
        a sample input file(s) do not exist or cannot be open.
    :type permissive: bool
    :param file_checks: Whether sample input files should be checked 
        for their  attributes (read type, read length) 
        if this is not set in sample metadata.
    :type file_checks: bool
    :param compute_env_file: Looperenv YAML file specifying compute settings.
    :type compute_env_file: str
    :param no_environment_exception: type of exception to raise if environment
        settings can't be established, optional; if null (the default),
        a warning message will be logged, and no exception will be raised.
    :type no_environment_exception: type
    :param no_compute_exception: type of exception to raise if compute
        settings can't be established, optional; if null (the default),
        a warning message will be logged, and no exception will be raised.
    :type no_compute_exception: type
    :param defer_sample_construction: whether to wait to build this Project's
        Sample objects until they're needed, optional; by default, the basic
        Sample is created during Project construction
    :type defer_sample_construction: bool


    :Example:

    .. code-block:: python

        from models import Project
        prj = Project("config.yaml")
    
    """

    DERIVED_COLUMNS_DEFAULT = [DATA_SOURCE_COLNAME]


    def __init__(self, config_file, subproject=None,
                 default_compute=None, dry=False,
                 permissive=True, file_checks=False, compute_env_file=None,
                 no_environment_exception=None, no_compute_exception=None,
                 defer_sample_construction=False):

        _LOGGER.debug("Creating %s from file: '%s'",
                          self.__class__.__name__, config_file)
        super(Project, self).__init__()

        # Initialize local, serial compute as default (no cluster submission)
        # Start with default environment settings.
        _LOGGER.debug("Establishing default environment settings")
        self.environment, self.environment_file = None, None

        try:
            self.update_environment(
                    default_compute or self.default_compute_envfile)
        except Exception as e:
            _LOGGER.error("Can't load environment config file '%s'",
                          str(default_compute))
            _LOGGER.error(str(type(e).__name__) + str(e))
        
        self._handle_missing_env_attrs(
                default_compute, when_missing=no_environment_exception)

        # Load settings from environment yaml for local compute infrastructure.
        if compute_env_file:
            _LOGGER.debug("Updating environment settings based on file '%s'",
                          compute_env_file)
            self.update_environment(compute_env_file)

        else:
            _LOGGER.info("Using default {envvar}. You may set environment "
                         "variable {envvar} to configure environment "
                         "settings.".format(envvar=self.compute_env_var))

        # Initialize default compute settings.
        _LOGGER.debug("Establishing project compute settings")
        self.compute = None
        self.set_compute(DEFAULT_COMPUTE_RESOURCES_NAME)

        # Either warn or raise exception if the compute is null.
        if self.compute is None:
            message = "Failed to establish project compute settings"
            if no_compute_exception:
                no_compute_exception(message)
            else:
                _LOGGER.warn(message)
        else:
            _LOGGER.debug("Compute: %s", str(self.compute))

        # optional configs
        self.permissive = permissive
        self.file_checks = file_checks

        # include the path to the config file
        self.config_file = _os.path.abspath(config_file)

        # Parse config file
        _LOGGER.debug("Parsing %s config file", self.__class__.__name__)
        if subproject:
            _LOGGER.info("Using subproject: '{}'".format(subproject))
        self.parse_config_file(subproject)

        self.name = self.infer_name(self.config_file)
        self.subproject = subproject

        # Set project's directory structure
        if not dry:
            _LOGGER.debug("Ensuring project directories exist")
            self.make_project_dirs()

        # Establish derived columns.
        try:
            # Do not duplicate derived column names.
            self.derived_columns.extend(
                    [colname for colname in self.DERIVED_COLUMNS_DEFAULT
                     if colname not in self.derived_columns])
        except AttributeError:
            self.derived_columns = self.DERIVED_COLUMNS_DEFAULT

        # SampleSheet creation populates project's samples, adds the
        # sheet itself, and adds any derived columns.
        _LOGGER.debug("Processing {} pipeline location(s): {}".
                      format(len(self.metadata.pipelines_dir),
                             self.metadata.pipelines_dir))
        self.finalize_pipelines_directory()
        self.interfaces_by_protocol = \
                process_pipeline_interfaces(self.metadata.pipelines_dir)
        self.sheet = check_sheet(self.metadata.sample_annotation)
        self.merge_table = None
        self._samples = None if defer_sample_construction else self.samples


    def __repr__(self):
        include = partial(include_in_repr, klazz=self.__class__)
        return repr({k: v for k, v in self.__dict__.items() if include(k)})


    @property
    def compute_env_var(self):
        """
        Environment variable through which to access compute settings.

        :return str: name of the environment variable to pointing to
            compute settings
        """
        return COMPUTE_SETTINGS_VARNAME


    @property
    def default_compute_envfile(self):
        """ Path to default compute environment settings file. """
        return _os.path.join(
                self.templates_folder, "default_compute_settings.yaml")


    @property
    def num_samples(self):
        """ Number of samples available in this Project. """
        return sum(1 for _ in self.sample_names)


    @property
    def output_dir(self):
        """
        Directory in which to place results and submissions folders.

        By default, assume that the project's configuration file specifies
        an output directory, and that this is therefore available within
        the project metadata. If that assumption does not hold, though,
        consider the folder in which the project configuration file lives
        to be the project's output directory.

        :return str: path to the project's output directory, either as
            specified in the configuration file or the folder that contains
            the project's configuration file.
        """
        try:
            return self.metadata.output_dir
        except AttributeError:
            return _os.path.dirname(self.config_file)


    @property
    def project_folders(self):
        """
        Names of folders to nest within a project output directory.

        :return Iterable[str]: names of output-nested folders
        """
        return ["results_subdir", "submission_subdir"]


    @property
    def protocols(self):
        """
        Determine this Project's unique protocol names.

        :return Set[str]: collection of this Project's unique protocol names
        """
        protos = set()
        for s in self.samples:
            try:
                protos.add(s.library)
            except AttributeError:
                _LOGGER.debug("Sample '%s' lacks protocol", s.sample_name)
        return protos


    @property
    def required_metadata(self):
        """
        Names of metadata fields that must be present for a valid project.
        
        Make a base project as unconstrained as possible by requiring no 
        specific metadata attributes. It's likely that some common-sense 
        requirements may arise in domain-specific client applications, in 
        which case this can be redefined in a subclass.
        
        :return Iterable[str]: names of metadata fields required by a project
        """
        return []


    @property
    def sample_names(self):
        """ Names of samples of which this Project is aware. """
        return iter(self.sheet[SAMPLE_NAME_COLNAME])


    @property
    def samples(self):
        """
        Generic/base Sample instance for each of this Project's samples.

        :return generator[Sample]: Sample instance for each
            of this Project's samples
        """
        if hasattr(self, "_samples") and self._samples is not None:
            _LOGGER.debug("%s has %d basic Sample(s)",
                          self.__class__.__name__, len(self._samples))
            return self._samples
        else:
            _LOGGER.debug("Building basic Sample(s) for %s",
                          self.__class__.__name__)

        # This should be executed just once, establishing the Project's
        # base Sample objects if they don't already exist.
        if hasattr(self.metadata, "merge_table"):
            if self.merge_table is None:
                if _os.path.isfile(self.metadata.merge_table):
                    self.merge_table = _pd.read_table(
                            self.metadata.merge_table,
                            sep=None, engine="python")
                else:
                    _LOGGER.debug(
                            "Alleged path to merge table data is not a "
                            "file: '%s'", self.metadata.merge_table)
            else:
                _LOGGER.debug("Already parsed merge table")
        else:
            _LOGGER.debug("No merge table")

        # Define merge behavior based on presence of merge table.
        if self.merge_table is None:
            def merge(s):
                return s
        else:
            def merge(s):
                return merge_sample(s, self.merge_table, self.data_sources,
                                    self.derived_columns)

        # Create the Sample(s).
        samples = []
        for _, row in self.sheet.iterrows():
            sample = Sample(row.dropna())
            sample.set_genome(self.genomes)
            sample.set_transcriptome(self.transcriptomes)

            sample.set_file_paths(self)
            # Hack for backwards-compatibility
            # Pipelines should now use `data_source`)
            try:
                sample.data_path = sample.data_source
            except AttributeError:
                _LOGGER.debug("Sample '%s' lacks data source --> skipping "
                              "data path assignment", sample.sample_name)
            sample = merge(sample)
            samples.append(sample)

        self._samples = samples
        return self._samples


    @property
    def templates_folder(self):
        """ Path to folder with default submission templates. """
        return _os.path.join(_os.path.dirname(__file__), "submit_templates")


    @staticmethod
    def infer_name(path_config_file):
        """
        Infer project name based on location of configuration file.
        
        Provide the project with a name, taken to be the name of the folder 
        in which its configuration file lives.
        
        :param str path_config_file: path to the project's configuration file.
        :return str: name of the configuration file's folder, to name project.
        """
        config_dirpath = _os.path.dirname(path_config_file)
        _, config_folder = _os.path.split(config_dirpath)
        return config_folder


    def build_pipelines(self, protocol, priority=True):
        """
        Create pipelines to submit for each sample of a particular protocol.

        With the argument (flag) to the priority parameter, there's control
        over whether to submit pipeline(s) from only one of the project's
        known pipeline locations with a match for the protocol, or whether to
        submit pipelines created from all locations with a match for the
        protocol.
        
        :param str protocol: name of the protocol/library for which to
            create pipeline(s)
        :param bool priority: to only submit pipeline(s) from the first of the
            pipelines location(s) (indicated in the project config file) that
            has a match for the given protocol; optional, default True
        :return Iterable[(PipelineInterface, str, str)]:
        :raises AssertionError: if there's a failure in the attempt to
            partition an interface's pipeline scripts into disjoint subsets of
            those already mapped and those not yet mapped
        """

        # Pull out the collection of interfaces (potentially one from each of
        # the locations indicated in the project configuration file) as a
        # sort of pool of information about possible ways in which to submit
        # pipeline(s) for sample(s) of the indicated protocol.
        try:
            protocol_interfaces = \
                    self.interfaces_by_protocol[protocol]
        except KeyError:
            _LOGGER.warn("Unknown protocol: '{}'".format(protocol))
            return []

        job_submission_bundles = []
        pipeline_keys_used = set()
        _LOGGER.debug("Building pipelines for {} PIs...".
                      format(len(protocol_interfaces)))
        for proto_iface in protocol_interfaces:
            # Short-circuit if we care only about the highest-priority match
            # for pipeline submission. That is, if the intent is to submit
            # pipeline(s) from a single location for each sample of the given
            # protocol, we can stop searching the pool of pipeline interface
            # information once we've found a match for the protocol.
            if priority and len(job_submission_bundles) > 0:
                return job_submission_bundles[0]

            this_protocol_pipelines = proto_iface.fetch(protocol)
            if not this_protocol_pipelines:
                _LOGGER.warn("No mapping for protocol '%s' in '%s', skipping",
                             protocol, proto_iface.location)
                continue
            
            # TODO: update once dependency-encoding logic is in place.
            # The proposed dependency-encoding format uses a semicolon
            # between pipelines for which the dependency relationship is
            # serial. For now, simply treat those as multiple independent
            # pipelines by replacing the semicolon with a comma, which is the
            # way in which multiple independent pipelines for a single protocol
            # are represented in the mapping declaration.
            pipeline_keys = \
                    this_protocol_pipelines.replace(";", ",")\
                                           .strip(" ()\n")\
                                           .split(",")
            # These cleaned pipeline keys are what's used to resolve the path
            # to the pipeline to run.
            pipeline_keys = [pk.strip() for pk in pipeline_keys]

            # Skip over pipelines already mapped by another location.
            already_mapped, new_scripts = \
                    partition(pipeline_keys,
                              partial(_is_member, items=pipeline_keys_used))
            pipeline_keys_used |= set(pipeline_keys)

            # Attempt to validate that partition yielded disjoint subsets.
            try:
                disjoint_partition_violation = \
                        set(already_mapped) & set(new_scripts)
            except TypeError:
                _LOGGER.debug("Unable to hash partitions for validation")
            else:
                assert not disjoint_partition_violation, \
                        "Partitioning {} with membership in {} as " \
                        "predicate produced intersection: {}".format(
                        pipeline_keys, pipeline_keys_used, 
                        disjoint_partition_violation)

            if len(already_mapped) > 0:
                _LOGGER.debug("Skipping {} already-mapped script name(s): {}".
                              format(len(already_mapped), already_mapped))
            _LOGGER.debug("{} new scripts for protocol {} from "
                          "pipeline(s) location '{}': {}".
                          format(len(new_scripts), protocol,
                                 proto_iface.location, new_scripts))

            new_jobs = [proto_iface.create_submission_bundle(pipeline_key,
                                                             protocol)
                        for pipeline_key in new_scripts]
            job_submission_bundles.append(new_jobs)

        # Repeat logic check of short-circuit conditional to account for
        # edge case in which it's satisfied during the final iteration.
        if priority and len(job_submission_bundles) > 1:
            return job_submission_bundles[0]
        else:
            return list(itertools.chain(*job_submission_bundles))


    def finalize_pipelines_directory(self, pipe_path=""):
        """
        Finalize the establishment of a path to this project's pipelines.

        With the passed argument, override anything already set.
        Otherwise, prefer path provided in this project's config, then
        local pipelines folder, then a location set in project environment.

        :param str pipe_path: (absolute) path to pipelines
        :raises PipelinesException: if (prioritized) search in attempt to
            confirm or set pipelines directory failed
        :raises TypeError: if pipeline(s) path(s) argument is provided and
            can't be interpreted as a single path or as a flat collection
            of path(s)
        """

        # TODO: check for local pipelines or those from environment.

        # Pass pipeline(s) dirpath(s) or use one already set.
        if not pipe_path:
            try:
                # TODO: beware of AttributeDict with _attribute_identity = True
                #  here, as that may return 'pipelines_dir' name itself.
                pipe_path = self.metadata.pipelines_dir
            except AttributeError:
                pipe_path = []

        # Ensure we're working with a flattened list.
        if isinstance(pipe_path, str):
            pipe_path = [pipe_path]
        elif isinstance(pipe_path, Iterable) and \
                not isinstance(pipe_path, Mapping):
            pipe_path = list(pipe_path)
        else:
            _LOGGER.debug("Got {} as pipelines path(s) ({})".
                          format(pipe_path, type(pipe_path)))
            pipe_path = []

        self.metadata.pipelines_dir = pipe_path


    def get_arg_string(self, pipeline_name):
        """
        For this project, given a pipeline, return an argument string
        specified in the project config file.
        """

        def make_optarg_text(opt, arg):
            """ Transform flag/option into CLI-ready text version. """
            return "{} {}".format(opt, _os.path.expandvars(arg)) \
                    if arg else opt

        def create_argtext(name):
            """ Create command-line argstring text from config section. """
            try:
                optargs = getattr(self.pipeline_args, name)
            except AttributeError:
                return ""
            # NS using __dict__ will add in the metadata from AttrDict (doh!)
            _LOGGER.debug("optargs.items(): {}".format(optargs.items()))
            optargs_texts = [make_optarg_text(opt, arg)
                             for opt, arg in optargs.items()]
            _LOGGER.debug("optargs_texts: {}".format(optargs_texts))
            # TODO: may need to fix some spacing issues here.
            return " ".join(optargs_texts)

        default_argtext = create_argtext(DEFAULT_COMPUTE_RESOURCES_NAME)
        pipeline_argtext = create_argtext(pipeline_name)

        if not pipeline_argtext:
            # The project config may not have an entry for this pipeline;
            # no problem! There are no pipeline-specific args. Return text
            # from default arguments, whether empty or not.
            return default_argtext
        elif default_argtext:
            # Non-empty pipeline-specific and default argtext
            return " ".join([default_argtext, pipeline_argtext])
        else:
            # No default argtext, but non-empty pipeline-specific argtext
            return pipeline_argtext


    def make_project_dirs(self):
        """
        Creates project directory structure if it doesn't exist.
        """
        for folder_name in self.project_folders:
            folder_path = self.metadata[folder_name]
            _LOGGER.debug("Ensuring project dir exists: '%s'", folder_path)
            if not _os.path.exists(folder_path):
                _LOGGER.debug("Attempting to create project folder: '%s'",
                              folder_path)
                try:
                    _os.makedirs(folder_path)
                except OSError as e:
                    _LOGGER.warn("Could not create project folder: '%s'",
                                 str(e))


    def parse_config_file(self, subproject=None):
        """
        Parse provided yaml config file and check required fields exist.
        
        :raises KeyError: if config file lacks required section(s)
        """

        _LOGGER.debug("Setting %s data from '%s'",
                      self.__class__.__name__, self.config_file)
        with open(self.config_file, 'r') as conf_file:
            config = yaml.safe_load(conf_file)

        # Parse yaml into the project's attributes.
        _LOGGER.debug("Adding attributes for {}: {}".format(
                self.__class__.__name__, config.keys()))
        _LOGGER.debug("Config metadata: {}")
        self.add_entries(config)
        _LOGGER.debug("{} now has {} keys: {}".format(
                self.__class__.__name__, len(self.keys()), self.keys()))

        # Overwrite any config entries with entries in the subproject.
        if "subprojects" in config and subproject:
            _LOGGER.debug("Adding entries for subproject '{}'".
                          format(subproject))
            subproj_updates = config['subprojects'][subproject]
            _LOGGER.debug("Updating with: {}".format(subproj_updates))
            self.add_entries(subproj_updates)
        else:
            _LOGGER.debug("No subproject")

        # In looper 0.4, for simplicity the paths section was eliminated.
        # For backwards compatibility, mirror the paths section into metadata.
        if "paths" in config:
            _LOGGER.warn(
                "Paths section in project config is deprecated. "
                "Please move all paths attributes to metadata section. "
                "This option will be removed in future versions.")
            self.metadata.add_entries(self.paths)
            _LOGGER.debug("Metadata: %s", str(self.metadata))
            delattr(self, "paths")

        # In looper 0.6, we added pipeline_interfaces to metadata
        # For backwards compatibility, merge it with pipelines_dir

        if "metadata" in config:
            if "pipelines_dir" in self.metadata:
                _LOGGER.warning("Looper v0.6 suggests "
                    "switching from pipelines_dir to "
                    "pipeline_interfaces. See docs for details: "
                    "http://looper.readthedocs.io/en/latest/")
            if "pipeline_interfaces" in self.metadata:
                if "pipelines_dir" in self.metadata:
                    raise AttributeError(
                            "You defined both 'pipeline_interfaces' and "
                            "'pipelines_dir'. Please remove your "
                            "'pipelines_dir' definition.")
                else:
                    self.metadata.pipelines_dir = \
                            self.metadata.pipeline_interfaces
                _LOGGER.debug("Adding pipeline_interfaces to "
                    "pipelines_dir. New value: {}".
                    format(self.metadata.pipelines_dir))


        # Ensure required absolute paths are present and absolute.
        for var in self.required_metadata:
            if var not in self.metadata:
                raise ValueError("Missing required metadata item: '%s'")
            setattr(self.metadata, var,
                    _os.path.expandvars(getattr(self.metadata, var)))

        _LOGGER.debug("{} metadata: {}".format(self.__class__.__name__,
                                               self.metadata))

        # These are optional because there are defaults
        config_vars = {
            # Defaults = {"variable": "default"}, relative to output_dir.
            "results_subdir": "results_pipeline",
            "submission_subdir": "submission"
        }

        for key, value in config_vars.items():
            if hasattr(self.metadata, key):
                if not _os.path.isabs(getattr(self.metadata, key)):
                    setattr(self.metadata, key,
                            _os.path.join(self.output_dir,
                                          getattr(self.metadata, key)))
            else:
                outpath = _os.path.join(self.output_dir, value)
                setattr(self.metadata, key, outpath)

        # Variables which are relative to the config file
        # All variables in these sections should be relative to project config.
        relative_sections = ["metadata", "pipeline_config"]

        _LOGGER.debug("Parsing relative sections")
        for sect in relative_sections:
            if not hasattr(self, sect):
                _LOGGER.log(5, "%s lacks relative section '%s', skipping",
                            self.__class__.__name__, sect)
                continue
            relative_vars = getattr(self, sect)
            if not relative_vars:
                _LOGGER.log(5, "No relative variables, continuing")
                continue
            for var in relative_vars.keys():
                if not hasattr(relative_vars, var) or \
                                getattr(relative_vars, var) is None:
                    continue

                relpath = getattr(relative_vars, var)
                _LOGGER.debug("Ensuring absolute path(s) for '%s'", var)
                # Parsed from YAML, so small space of possible datatypes.
                if isinstance(relpath, list):
                    absolute = [self._ensure_absolute(maybe_relpath)
                                for maybe_relpath in relpath]
                else:
                    absolute = self._ensure_absolute(relpath)
                _LOGGER.debug("Setting '%s' to '%s'", var, absolute)
                setattr(relative_vars, var, absolute)

        # Project config may have made compute.submission_template relative.
        # Make sure it's absolute.
        if self.compute is None:
            _LOGGER.log(5, "No compute, no submission template")
        elif not _os.path.isabs(self.compute.submission_template):
            # Relative to environment config file.
            self.compute.submission_template = _os.path.join(
                    _os.path.dirname(self.environment_file),
                    self.compute.submission_template
            )

        # Required variables check
        if not hasattr(self.metadata, SAMPLE_ANNOTATIONS_KEY):
            raise _MissingMetadataException(
                    missing_section=SAMPLE_ANNOTATIONS_KEY, 
                    path_config_file=self.config_file)


    def set_compute(self, setting):
        """
        Set the compute attributes according to the
        specified settings in the environment file.

        :param str setting:	name for non-resource compute bundle, the name of
            a subsection in an environment configuration file
        :return bool: success flag for attempt to establish compute settings
        """

        # Hope that environment & environment compute are present.
        if setting and self.environment and "compute" in self.environment:
            # Augment compute, creating it if needed.
            if self.compute is None:
                _LOGGER.debug("Creating Project compute")
                self.compute = AttributeDict()
                _LOGGER.debug("Adding entries for setting '%s'", setting)
            self.compute.add_entries(self.environment.compute[setting])

            # Ensure submission template is absolute.
            if not _os.path.isabs(self.compute.submission_template):
                try:
                    self.compute.submission_template = _os.path.join(
                            _os.path.dirname(self.environment_file),
                            self.compute.submission_template)
                except AttributeError as e:
                    # Environment and environment compute should at least have been
                    # set as null-valued attributes, so execution here is an error.
                    _LOGGER.error(str(e))
                    # Compute settings have been established.
                else:
                    return True
        else:
            # Scenario in which environment and environment compute are
            # both present but don't evaluate to True is fairly
            # innocuous, even common if outside of the looper context.
            _LOGGER.debug("Environment = {}".format(self.environment))

        return False


    def set_project_permissions(self):
        """
        Make the project's public_html folder executable.
        """
        try:
            _os.chmod(self.trackhubs.trackhub_dir, 0o0755)
        except OSError:
            # This currently does not fail now
            # ("cannot change folder's mode: %s" % d)
            pass


    def update_environment(self, env_settings_file):
        """
        Parse data from environment configuration file.

        :param str env_settings_file: path to file with 
            new environment configuration data
        """

        with open(env_settings_file, 'r') as f:
            _LOGGER.info("Loading %s: %s",
                         self.compute_env_var, env_settings_file)
            env_settings = yaml.load(f)
            _LOGGER.debug("Parsed environment settings: %s",
                          str(env_settings))

            # Any compute.submission_template variables should be made
            # absolute, relative to current environment settings file.
            y = env_settings["compute"]
            for key, value in y.items():
                if type(y[key]) is dict:
                    for key2, value2 in y[key].items():
                        if key2 == "submission_template":
                            if not _os.path.isabs(y[key][key2]):
                                y[key][key2] = _os.path.join(
                                        _os.path.dirname(env_settings_file),
                                        y[key][key2])

            env_settings["compute"] = y
            if self.environment is None:
                self.environment = AttributeDict(env_settings)
            else:
                self.environment.add_entries(env_settings)

        self.environment_file = env_settings_file


    def _ensure_absolute(self, maybe_relpath):
        """ Ensure that a possibly relative path is absolute. """
        _LOGGER.log(5, "Ensuring absolute: '%s'", maybe_relpath)
        if _os.path.isabs(maybe_relpath) or is_url(maybe_relpath):
            _LOGGER.log(5, "Already absolute")
            return maybe_relpath
        # Maybe we have env vars that make the path absolute?
        expanded = _os.path.expandvars(maybe_relpath)
        _LOGGER.log(5, "Expanded: '%s'", expanded)
        if _os.path.isabs(expanded):
            _LOGGER.log(5, "Expanded is absolute")
            return expanded
        _LOGGER.log(5, "Making non-absolute path '%s' be absolute",
                      maybe_relpath)
        # Set path to an absolute path, relative to project config.
        config_dirpath = _os.path.dirname(self.config_file)
        _LOGGER.log(5, "config_dirpath: %s", config_dirpath)
        abs_path = _os.path.join(config_dirpath, maybe_relpath)
        return abs_path


    def _handle_missing_env_attrs(self, env_settings_file, when_missing):
        """ Default environment settings aren't required; warn, though. """
        missing_env_attrs = \
            [attr for attr in ["environment", "environment_file"]
             if not hasattr(self, attr) or getattr(self, attr) is None]
        if not missing_env_attrs:
            return
        message = "'{}' lacks environment attributes: {}".\
                format(env_settings_file, missing_env_attrs)
        if when_missing is None:
            _LOGGER.warn(message)
        else:
            when_missing(message)



def check_sheet(sample_file, dtype=str):
    """
    Check if csv file exists and has all required columns.

    :param str sample_file: path to sample annotations file.
    :param type dtype: data type for CSV read.
    :raises IOError: if given annotations file can't be read.
    :raises ValueError: if required column(s) is/are missing.
    """

    df = _pd.read_table(sample_file, sep=None, dtype=dtype,
                        index_col=False, engine="python")
    req = [SAMPLE_NAME_COLNAME]
    missing = set(req) - set(df.columns)
    if len(missing) != 0:
        raise ValueError(
            "Annotation sheet ('{}') is missing column(s): {}; has: {}".
                format(sample_file, missing, df.columns))
    return df



@copy
class Sample(object):
    """
    Class to model Samples based on a pandas Series.

    :param series: Sample's data.
    :type series: Mapping | pandas.core.series.Series

    :Example:

    .. code-block:: python

        from models import Project, SampleSheet, Sample
        prj = Project("ngs")
        sheet = SampleSheet("~/projects/example/sheet.csv", prj)
        s1 = Sample(sheet.iloc[0])
    """

    _FEATURE_ATTR_NAMES = ["read_length", "read_type", "paired"]

    # Originally, this object was inheriting from _pd.Series,
    # but complications with serializing and code maintenance
    # made me go back and implement it as a top-level object
    def __init__(self, series):
        super(Sample, self).__init__()
        self.merged_cols = {}
        self.derived_cols_done = []

        # Keep a list of attributes that came from the sample sheet,
        # so we can create a minimal, ordered representation of the original.
        # This allows summarization of the sample (i.e.,
        # appending new columns onto the original table)
        self.sheet_attributes = series.keys()

        if isinstance(series, _pd.Series):
            series = series.to_dict()
        elif isinstance(series, Sample):
            series = series.as_series().to_dict()

        # Set series attributes on self.
        for key, value in series.items():
            setattr(self, key, value)

        # Check if required attributes exist and are not empty.
        lacking = self.check_valid()
        if lacking:
            missing_kwarg = "missing"
            empty_kwarg = "empty"
            raise ValueError("Sample lacks attribute(s). {}={}; {}={}".
                             format(missing_kwarg, lacking[missing_kwarg],
                                    empty_kwarg, lacking[empty_kwarg]))

        # Short hand for getting sample_name
        self.name = self.sample_name

        # Default to no required paths and no YAML file.
        self.required_paths = None
        self.yaml_file = None

        # Sample dirs
        self.paths = Paths()
        # Only when sample is added to project, can paths be added -
        # This is because sample-specific files will be created in a
        # data root directory dependent on the project.
        # The SampleSheet object, after being added to a project, will
        # call Sample.set_file_paths().


    def __getitem__(self, item):
        """
        Provides dict-style access to attributes
        """
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)


    def __repr__(self):
        return "Sample '{}'".format(self.name)


    def as_series(self):
        """
        Returns a `pandas.Series` object with all the sample's attributes.

        :return pandas.core.series.Series: pandas Series representation
            of this Sample, with its attributes.
        """
        return _pd.Series(self.__dict__)


    def check_valid(self, required=None):
        """
        Check provided sample annotation is valid.

        :param Iterable[str] required: collection of required sample attribute
            names, optional; if unspecified, only a name is required.

        """
        lacking = defaultdict(list)
        for attr in required or [SAMPLE_NAME_COLNAME]:
            if not hasattr(self, attr):
                lacking["missing"].append(attr)
            if attr == "nan":
                lacking["empty"].append(attr)
        return lacking


    def confirm_required_inputs(self, permissive=False):

        # set_pipeline_attributes must be run first.
        if not hasattr(self, "required_inputs"):
            _LOGGER.warn("You must run set_pipeline_attributes "
                         "before confirm_required_inputs")
            return True

        if not self.required_inputs:
            _LOGGER.debug("No required inputs")
            return True

        # First, attributes
        for file_attribute in self.required_inputs_attr:
            _LOGGER.debug("Checking '{}'".format(file_attribute))
            if not hasattr(self, file_attribute):
                message = "Missing required input attribute '{}'".\
                    format(file_attribute)
                _LOGGER.warn(message)
                if not permissive:
                    raise IOError(message)
                else:
                    return False
            if getattr(self, file_attribute) is "":
                message = "Empty required input attribute '{}'".\
                    format(file_attribute)
                _LOGGER.warn(message)
                if not permissive:
                    raise IOError(message)
                else:
                    return False

        # Second, files
        missing_files = []
        for paths in self.required_inputs:
            # There can be multiple, space-separated values here.
            for path in paths.split(" "):
                _LOGGER.debug("Checking path: '{}'".format(path))
                if not _os.path.exists(path):
                    _LOGGER.warn("Missing required input file: '{}'".format(path))
                    missing_files.append(path)

        if len(missing_files) > 0:
            message = "Missing/unreadable file(s): {}".\
                    format(", ".join(["'{}'".format(path)
                                      for path in missing_files]))
            if not permissive:
                raise IOError(message)
            else:
                _LOGGER.error(message)
                return False

        return True


    def is_dormant(self):
        """
        Determine whether this Sample is inactive.

        By default, a Sample is regarded as active. That is, if it lacks an
        indication about activation status, it's assumed to be active. If,
        however, and there's an indication of such status, it must be '1'
        in order to be considered switched 'on.'

        :return bool: whether this Sample's been designated as dormant
        """
        try:
            flag = self[SAMPLE_EXECUTION_TOGGLE]
        except KeyError:
            # Regard default Sample state as active.
            return False
        # If specified, the activation flag must be set to '1'.
        return flag != "1"


    def generate_name(self):
        """
        Generate name for the sample by joining some of its attribute strings.
        """
        raise NotImplementedError("Not implemented in new code base.")


    def get_attr_values(self, attrlist):
        """
        Get value corresponding to each given attribute.

        :param str attrlist: name of an attribute storing a list of attr names
        :return list: value (or empty string) corresponding to each named attr
        """
        if not hasattr(self, attrlist):
            return None

        attribute_list = getattr(self, attrlist)

        # If attribute is None, then value is also None.
        if not attribute_list:
            return None

        if not isinstance(attribute_list, list):
            attribute_list = [attribute_list]

        # Strings contained here are appended later so shouldn't be null.
        return [getattr(self, attr) if hasattr(self, attr) else ""
                for attr in attribute_list]


    def get_sheet_dict(self):
        """
        Create a K-V pairs for items originally passed in via the sample sheet.

        This is useful for summarizing; it provides a representation of the
        sample that excludes things like config files and derived entries.

        :return OrderedDict: mapping from name to value for data elements
            originally provided via the sample sheet (i.e., the a map-like
            representation of the instance, excluding derived items)
        """
        return _OrderedDict([[k, getattr(self, k)]
                             for k in self.sheet_attributes])


    def infer_columns(self, implications):
        """
        Infer value for additional field(s) from other field(s).

        Add columns/fields to the sample based on values in those already-set
        that the sample's project defines as indicative of implications for
        additional data elements for the sample.

        :param Mapping implications: Project's implied columns data
        :return None: this function mutates state and is strictly for effect
        """

        _LOGGER.log(5, "Sample attribute implications: {}".
                    format(implications))
        if not implications:
            return

        for implier_name, implied in implications.items():
            _LOGGER.debug(
                "Setting Sample variable(s) implied by '%s'", implier_name)
            try:
                implier_value = self[implier_name]
            except KeyError:
                _LOGGER.debug("No '%s' for this sample", implier_name)
                continue
            try:
                implied_value_by_column = implied[implier_value]
                _LOGGER.debug("Implications for '%s' = %s: %s",
                              implier_name, implier_value,
                              str(implied_value_by_column))
                for colname, implied_value in \
                        implied_value_by_column.items():
                    _LOGGER.log(5, "Setting '%s'=%s",
                                colname, implied_value)
                    setattr(self, colname, implied_value)
            except KeyError:
                _LOGGER.log(
                    5, "Unknown implied value for implier '%s' = '%s'",
                    implier_name, implier_value)


    def locate_data_source(self, data_sources, column_name=DATA_SOURCE_COLNAME,
                           source_key=None, extra_vars=None):
        """
        Uses the template path provided in the project config section
        "data_sources" to piece together an actual path by substituting
        variables (encoded by "{variable}"") with sample attributes.

        :param Mapping data_sources: mapping from key name (as a value in
            a cell of a tabular data structure) to, e.g., filepath
        :param str column_name: Name of sample attribute
            (equivalently, sample sheet column) specifying a derived column.
        :param str source_key: The key of the data_source,
            used to index into the project config data_sources section.
            By default, the source key will be taken as the value of
            the specified column (as a sample attribute).
            For cases where the sample doesn't have this attribute yet
            (e.g. in a merge table), you must specify the source key.
        :param dict extra_vars: By default, this will look to
            populate the template location using attributes found in the
            current sample; however, you may also provide a dict of extra
            variables that can also be used for variable replacement.
            These extra variables are given a higher priority.
        :return str: regex expansion of data source specified in configuration,
            with variable substitutions made
        :raises ValueError: if argument to data_sources parameter is null/empty
        """

        if not data_sources:
            # TODO: should this be a null/empty-string return, or actual error?
            raise ValueError("No data sources")

        if not source_key:
            try:
                source_key = getattr(self, column_name)
            except AttributeError:
                reason = "'{attr}': to locate sample's data source, provide " \
                         "the name of a key from '{sources}' or ensure " \
                         "sample has attribute '{attr}'".format(
                         attr=column_name, sources=DATA_SOURCES_SECTION)
                raise AttributeError(reason)

        try:
            regex = data_sources[source_key]
        except KeyError:
            _LOGGER.warn(
                    "Config lacks entry for data_source key: '{}' "
                    "(in column: '{}')".format(source_key, column_name))
            return ""

        # Populate any environment variables like $VAR with os.environ["VAR"]
        regex = _os.path.expandvars(regex)

        try:
            # Grab a temporary dictionary of sample attributes and update these
            # with any provided extra variables to use in the replacement.
            # This is necessary for derived_columns in the merge table.
            # Here the copy() prevents the actual sample from being
            # updated by update().
            temp_dict = self.__dict__.copy()
            temp_dict.update(extra_vars or {})
            val = regex.format(**temp_dict)
            if '*' in val or '[' in val:
                _LOGGER.debug("Pre-glob: %s", val)
                val_globbed = sorted(glob.glob(val))
                val = " ".join(val_globbed)
                _LOGGER.debug("Post-glob: %s", val)

        except Exception as e:
            _LOGGER.error("Can't format data source correctly: %s", regex)
            _LOGGER.error(str(type(e).__name__) + str(e))
            return regex

        return val


    def make_sample_dirs(self):
        """
        Creates sample directory structure if it doesn't exist.
        """
        for path in self.paths:
            if not _os.path.exists(path):
                _os.makedirs(path)


    def set_file_paths(self, project):
        """
        Sets the paths of all files for this sample.

        :param Project project: object with pointers to data paths and such
        """
        # Any columns specified as "derived" will be constructed
        # based on regex in the "data_sources" section of project config.

        for col in project.derived_columns:
            # Only proceed if the specified column exists
            # and was not already merged or derived.
            if hasattr(self, col) and col not in self.merged_cols \
                    and col not in self.derived_cols_done:
                # Set a variable called {col}_key, so the
                # original source can also be retrieved.
                setattr(self, col + COL_KEY_SUFFIX, getattr(self, col))
                setattr(self, col, self.locate_data_source(
                        data_sources=project.get(DATA_SOURCES_SECTION),
                        column_name=col))
                self.derived_cols_done.append(col)

        self.infer_columns(implications=project.get(IMPLICATIONS_DECLARATION))

        # Parent
        self.results_subdir = project.metadata.results_subdir
        self.paths.sample_root = _os.path.join(
                project.metadata.results_subdir, self.sample_name)

        # Track url
        bigwig_filename = self.name + ".bigWig"
        try:
            # Project's public_html folder
            self.bigwig = _os.path.join(
                    project.trackhubs.trackhub_dir, bigwig_filename)
            self.track_url = \
                    "{}/{}".format(project.trackhubs.url, bigwig_filename)
        except:
            _LOGGER.debug("No trackhub/URL")
            pass

    
    def set_genome(self, genomes):
        self._set_assembly("genome", genomes)
        
        
    def set_transcriptome(self, transcriptomes):
        self._set_assembly("transcriptome", transcriptomes)
        
        
    def _set_assembly(self, ome, assemblies):
        try:
            assembly = assemblies[self.organism]
        except AttributeError:
            _LOGGER.debug("Sample '%s' lacks organism attribute", self.name)
            assembly = None
        except KeyError:
            _LOGGER.log(5, "Unknown {} value: '{}'".
                    format(ome, self.organism))
            assembly = None
        _LOGGER.log(5, "Setting {} as {} on sample: '{}'".
                format(assembly, ome, self.name))
        setattr(self, ome, assembly)
        

    def set_pipeline_attributes(
            self, pipeline_interface, pipeline_name, permissive=True):
        """
        Set pipeline-specific sample attributes.
        
        Some sample attributes are relative to a particular pipeline run,
        like which files should be considered inputs, what is the total
        input file size for the sample, etc. This function sets these
        pipeline-specific sample attributes, provided via a PipelineInterface
        object and the name of a pipeline to select from that interface.
        
        :param PipelineInterface pipeline_interface: A PipelineInterface
            object that has the settings for this given pipeline.
        :param str pipeline_name: Which pipeline to choose.
        :param bool permissive: whether to simply log a warning or error 
            message rather than raising an exception if sample file is not 
            found or otherwise cannot be read, default True
        """

        # Settings ending in _attr are lists of attribute keys.
        # These attributes are then queried to populate values
        # for the primary entries.
        self.ngs_inputs_attr = pipeline_interface.get_attribute(
                pipeline_name, "ngs_input_files")
        self.required_inputs_attr = pipeline_interface.get_attribute(
                pipeline_name, "required_input_files")
        self.all_inputs_attr = pipeline_interface.get_attribute(
                pipeline_name, "all_input_files")

        if self.ngs_inputs_attr:
            _LOGGER.debug("Handling NGS input attributes: '%s'", self.name)
            # NGS data inputs exit, so we can add attributes like
            # read_type, read_length, paired.
            self.ngs_inputs = self.get_attr_values("ngs_inputs_attr")
            self.set_read_type(permissive=permissive)
        else:
            _LOGGER.debug("No NGS inputs: '%s'", self.name)

        # input_size
        if not self.all_inputs_attr:
            self.all_inputs_attr = self.required_inputs_attr

        # Convert attribute keys into values
        self.required_inputs = self.get_attr_values("required_inputs_attr")
        self.all_inputs = self.get_attr_values("all_inputs_attr")
        self.input_file_size = get_file_size(self.all_inputs)


    def set_read_type(self, n=10, permissive=True):
        """
        For a sample with attr `ngs_inputs` set, this sets the 
        read type (single, paired) and read length of an input file.

        :param n: Number of reads to read to determine read type. Default=10.
        :type n: int
        :param permissive: whether to simply log a warning or error message 
            rather than raising an exception if sample file is not found or 
            otherwise cannot be read, default True
        :type permissive: bool
        """
        # Initialize the parameters in case there is no input_file, so these
        # attributes at least exist - as long as they are not already set!
        if not hasattr(self, "read_length"):
            self.read_length = None
        if not hasattr(self, "read_type"):
            self.read_type = None
        if not hasattr(self, "paired"):
            self.paired = None

        # ngs_inputs must be set
        if not self.ngs_inputs:
            return False

        ngs_paths = " ".join(self.ngs_inputs)

        existing_files = list()
        missing_files = list()
        for path in ngs_paths.split(" "):
            if not _os.path.exists(path):
                missing_files.append(path)
            else:
                existing_files.append(path)

        # For samples with multiple original BAM files, check all.
        files = list()
        check_by_ftype = {"bam": check_bam, "fastq": check_fastq}
        for input_file in existing_files:
            try:
                file_type = parse_ftype(input_file)
                read_length, paired = check_by_ftype[file_type](input_file, n)
            except (KeyError, TypeError):
                message = "Input file type should be one of: {}".format(
                        check_by_ftype.keys())
                if not permissive:
                    raise TypeError(message)
                _LOGGER.error(message)
                return
            except NotImplementedError as e:
                if not permissive:
                    raise
                _LOGGER.warn(e.message)
                return
            except IOError:
                if not permissive:
                    raise
                _LOGGER.error("Input file does not exist or "
                              "cannot be read: %s", str(input_file))
                for feat_name in self._FEATURE_ATTR_NAMES:
                    if not hasattr(self, feat_name):
                        setattr(self, feat_name, None)
                return
            except OSError as e:
                _LOGGER.error(str(e) + " [file: {}]".format(input_file))
                for feat_name in self._FEATURE_ATTR_NAMES:
                    if not hasattr(self, feat_name):
                        setattr(self, feat_name, None)
                return

            # Get most abundant read length
            read_length = sorted(read_length)[-1]

            # If at least half is paired, consider paired end reads
            if paired > (n / 2):
                read_type = "paired"
                paired = True
            else:
                read_type = "single"
                paired = False

            files.append([read_length, read_type, paired])

        # Check agreement between different files
        # if all values are equal, set to that value;
        # if not, set to None and warn the user about the inconsistency
        for i, feature in enumerate(self._FEATURE_ATTR_NAMES):
            setattr(self, feature,
                    files[0][i] if len(set(f[i] for f in files)) == 1 else None)

            if getattr(self, feature) is None and len(existing_files) > 0:
                _LOGGER.warn("Not all input files agree on "
                             "feature '%s' for sample '%s'",
                             feature, self.name)


    def to_yaml(self, path=None, subs_folder_path=None, pipeline_name=None):
        """
        Serializes itself in YAML format.

        :param str path: A file path to write yaml to; provide this or
            the subs_folder_path
        :param str pipeline_name: name of a pipeline to which this particular
            Sample instance pertains (i.e., perhaps the name of a module
            that defined a Sample subclass of which this is an instance)
        :param str subs_folder_path: path to folder in which to place file
            that's being written; provide this or a full filepath
        :return str: filepath used (same as input if given, otherwise the
            path value that was inferred)
        :raises ValueError: if neither full filepath nor path to extant
            parent directory is provided.
        """

        # Determine filepath, prioritizing anything given, then falling
        # back to a default using this Sample's Project's submission_subdir.
        # Use the sample name and YAML extension as the file name,
        # interjecting a pipeline name as a subfolder within the Project's
        # submission_subdir if such a pipeline name is provided.
        if not path:
            if not subs_folder_path:
                raise ValueError(
                    "To represent {} on disk, provide a full path or a path "
                    "to a parent (submissions) folder".
                    format(self.__class__.__name__))
            filename = "{}_{}.yaml".format(self.sample_name, pipeline_name) \
                if pipeline_name else "{}.yaml".format(self.sample_name)
            path = _os.path.join(subs_folder_path, filename)
        self.yaml_file = path


        def obj2dict(obj,
                     to_skip=("samples", "sheet", "sheet_attributes")):
            """
            Build representation of object as a dict, recursively
            for all objects that might be attributes of self.

            :param object obj: what to serialize to write to YAML.
            :param Iterable[str] to_skip: names of attributes to ignore.
\            """
            if isinstance(obj, list):
                return [obj2dict(i) for i in obj]
            if isinstance(obj, AttributeDict):
                return {k: obj2dict(v) for k, v in obj.__dict__.items()
                        if k not in to_skip and
                        (k not in ATTRDICT_METADATA or
                         v != ATTRDICT_METADATA[k])}
            elif isinstance(obj, Mapping):
                return {k: obj2dict(v)
                        for k, v in obj.items() if k not in to_skip}
            elif isinstance(obj, (Paths, Sample)):
                return {k: obj2dict(v)
                        for k, v in obj.__dict__.items() if
                        k not in to_skip}
            elif hasattr(obj, 'dtype'):  # numpy data types
                # TODO: this fails with ValueError for multi-element array.
                return obj.item()
            elif _pd.isnull(obj):
                # Missing values as evaluated by pd.isnull().
                # This gets correctly written into yaml.
                return "NaN"
            else:
                return obj

        _LOGGER.debug("Serializing %s: '%s'",
                      self.__class__.__name__, self.name)
        serial = obj2dict(self)
        with open(self.yaml_file, 'w') as outfile:
            _LOGGER.debug("Generating YAML data for %s: '%s'",
                          self.__class__.__name__, self.name)
            yaml_data = yaml.safe_dump(serial, default_flow_style=False)
            #yaml_data = yaml.dump(serial, Dumper=PepYamlDumper, default_flow_style=False)
            outfile.write(yaml_data)


    def update(self, newdata):
        """
        Update Sample object with attributes from a dict.
        """
        for key, value in newdata.items():
            setattr(self, key, value)


    @classmethod
    def select_sample_subtype(cls, pipeline_filepath, protocol=None):
        """
        From a pipeline module, select Sample subtype for a particular protocol.

        The indicated file needs to be a Python module that can be imported.
        Critically, it must be written such that importing it does not run it
        as a script. That is, its workflow logic should be bundled into
        function(s), or at least nested under a "if __name__ == '__main__'"
        conditional.

        :param str pipeline_filepath: path to file defining a pipeline
        :param str protocol: name of protocol for which to select Sample subtype
        :return type: Sample type most tailored to indicated protocol and
            defined within the module indicated by the given filepath,
            optional; if unspecified, or if the indicated file cannot be
            imported, then the base Sample type is returned.
        """

        if not _os.path.isfile(pipeline_filepath):
            _LOGGER.debug("Alleged pipeline module path is not a file: '%s'", 
                          pipeline_filepath)
            return cls

        # Determine whether it appears safe to import the pipeline module, 
        # and return a generic, base Sample if not.
        import subprocess
        def file_has_pattern(pattern, filepath):
            try:
                with open(_os.devnull, 'w') as devnull:
                    return subprocess.call(
                            ["grep", pattern, filepath], stdout=devnull)
            except Exception:
                return False
        safety_lines = ["if __name__ == '__main__'",
                        "if __name__ == \"__main__\""]
        safe_to_import = \
                any(map(partial(file_has_pattern,
                                filepath=pipeline_filepath),
                        safety_lines))
        if not safe_to_import:
            _LOGGER.debug("Attempt to import '{}' may run code so is refused.".
                          format(pipeline_filepath))
            return cls

        # Import pipeline module and find Sample subtypes.
        _, modname = _os.path.split(pipeline_filepath)
        modname, _ = _os.path.splitext(modname)
        try:
            _LOGGER.debug("Attempting to import module defined by {}, "
                          "calling it {}".format(pipeline_filepath, modname))
            pipeline_module = import_from_source(
                    name=modname, module_filepath=pipeline_filepath)
        except ImportError as e:
            _LOGGER.warn("Using base Sample because of failure in attempt to "
                         "import pipeline module: {}".format(e))
            return cls
        else:
            _LOGGER.debug("Successfully imported pipeline module '%s', "
                          "naming it '%s'", pipeline_filepath,
                      pipeline_module.__name__)

        import inspect
        sample_subtypes = inspect.getmembers(
                pipeline_module, lambda obj: isinstance(obj, Sample))
        _LOGGER.debug("%d sample subtype(s): %s", len(sample_subtypes), 
                      ", ".join([subtype.__name__ 
                                 for subtype in sample_subtypes]))

        # Match all subtypes for null protocol; use __library__ for non-null.
        if protocol is None:
            _LOGGER.debug("Null protocol, matching every subtypes...")
            matched_subtypes = sample_subtypes
        else:
            protocol_key = alpha_cased(protocol)
            matched_subtypes = \
                    [subtype for subtype in sample_subtypes 
                     if protocol_key == alpha_cased(subtype.__library__)]

        # Helpful for messages about protocol name for each subtype
        subtype_by_protocol_text = \
                ", ".join(["'{}' ({})".format(subtype.__library, subtype) 
                           for subtype in sample_subtypes])

        # Select subtype based on match count.
        if 0 == len(matched_subtypes):
            # Fall back to base Sample if we have no matches.
            _LOGGER.debug(
                    "No known Sample subtype for protocol '{}' in '{}'; "
                    "known: {}".format(protocol, pipeline_filepath,
                                       subtype_by_protocol_text))
            return cls
        elif 1 == len(matched_subtypes):
            # Use the single match if there's exactly one.
            subtype = matched_subtypes[0]
            _LOGGER.info("Matched protocol '{}' to Sample subtype {}".
                         format(protocol, subtype.__name__))
            return subtype
        else:
            # Throw up our hands and fall back to base Sample for multi-match.
            _LOGGER.debug("Unable to choose from {} Sample subtype matches "
                          "for protocol '{}' in '{}': {}".format(
                    len(matched_subtypes), protocol,
                    pipeline_filepath, subtype_by_protocol_text))
            return cls



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
            _LOGGER.debug("Creating %s with preparsed data",
                         self.__class__.__name__)
            self.pipe_iface_file = None
            self.pipe_iface_config = config

        else:
            _LOGGER.debug("Parsing '%s' for PipelineInterface config data",
                         config)
            self.pipe_iface_file = config
            with open(config, 'r') as f:
                self.pipe_iface_config = yaml.load(f)


    def __getitem__(self, item):
        try:
            return self._select_pipeline(item)
        except _MissingPipelineConfigurationException:
            raise KeyError("{} is not a known pipeline; known: {}".
                           format(item, self.pipe_iface_config.keys()))


    def __iter__(self):
        return iter(self.pipe_iface_config.items())


    def __repr__(self):
        source = self.pipe_iface_file or "mapping"
        num_pipelines = len(self.pipe_iface_config)
        pipelines = ", ".join(self.pipe_iface_config.keys())
        return "{} from {}, with {} pipeline(s): {}".format(
                self.__class__.__name__, source, num_pipelines, pipelines)


    @property
    def pipeline_names(self):
        return self.pipe_iface_config.keys()


    @property
    def pipelines(self):
        return self.pipe_iface_config.values()


    def choose_resource_package(self, pipeline_name, file_size):
        """
        Select resource bundle for given input file size to given pipeline.

        :param pipeline_name: Name of pipeline.
        :type pipeline_name: str
        :param file_size: Size of input data.
        :type file_size: float
        :return: resource bundle appropriate for given pipeline,
            for given input file size
        :rtype: MutableMapping
        :raises ValueError: if indicated file size is negative, or if the
            file size value specified for any resource package is negative
        :raises _InvalidResourceSpecificationException: if no default
            resource package specification is provided
        """

        if file_size < 0:
            raise ValueError("Attempted selection of resource package for "
                             "negative file size: {}".format(file_size))

        try:
            resources = self._select_pipeline(pipeline_name)["resources"]
        except KeyError:
            _LOGGER.warn("No resources found for pipeline '%s' in file '%s'",
                         pipeline_name, self.pipe_iface_file)
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
        # Sort packages by descending file size minimum to return first
        # package for which given file size satisfies the minimum.
        try:
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
                _LOGGER.debug(
                        "Selected '{}' package with min file size {} for {}.".
                        format(rp_name, size_ante, file_size))
                return rp_data


    def get_arg_string(self, pipeline_name, sample):
        """
        For a given pipeline and sample, return the argument string

        :param str pipeline_name: Name of pipeline.
        :param Sample sample: current sample for which job is being built
        :return str: command-line argument string for pipeline
        """

        _LOGGER.debug("Building arguments string")
        config = self._select_pipeline(pipeline_name)
        argstring = ""

        if "arguments" not in config:
            _LOGGER.info("No arguments found for '%s' in '%s'",
                              pipeline_name, self.pipe_iface_file)
            return argstring

        args = config["arguments"]

        for key, value in args.iteritems():
            if value is None:
                _LOGGER.debug("Null value for opt arg key '%s'",
                                   str(key))
                continue
            try:
               arg = getattr(sample, value)
            except AttributeError:
                _LOGGER.error(
                    "Error (missing attribute): '%s' "
                    "requires sample attribute '%s' "
                    "for argument '%s'",
                    pipeline_name, value, key)
                raise

            _LOGGER.debug("Adding '{}' from attribute '{}' for argument '{}'".
                          format(arg, value, key))
            argstring += " " + str(key) + " " + str(arg)

        # Add optional arguments
        if "optional_arguments" in config:
            args = config["optional_arguments"]
            for key, value in args.iteritems():
                _LOGGER.debug("%s, %s (optional)", key, value)
                if value is None:
                    _LOGGER.debug("Null value for opt arg key '%s'",
                                       str(key))
                    continue
                try:
                    arg = getattr(sample, value)
                except AttributeError:
                    _LOGGER.warn(
                        "> Note (missing attribute): '%s' requests "
                        "sample attribute '%s' for "
                        "OPTIONAL argument '%s'",
                        pipeline_name, value, key)
                    continue

                argstring += " " + str(key) + " " + str(arg)

        _LOGGER.debug("Script args: '%s'", argstring)

        return argstring


    def get_attribute(self, pipeline_name, attribute_key):
        """ Return value of given attribute for named pipeline. """
        config = self._select_pipeline(pipeline_name)
        try:
            value = config[attribute_key]
        except KeyError:
            value = None
        return [value] if isinstance(value, str) else value


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
            return self.pipe_iface_config[pipeline_name] or {}
        except KeyError:
            _LOGGER.error(
                "Missing pipeline description: '%s' not found in '%s'",
                pipeline_name, self.pipe_iface_file)
            # TODO: use defaults or force user to define this?
            raise _MissingPipelineConfigurationException(pipeline_name)



class ProtocolInterface(object):
    """ PipelineInterface and ProtocolMapper for a single pipelines location.

    This class facilitates use of pipelines from multiple locations by a
    single project. Also stored are path attributes with information about
    the location(s) from which the PipelineInterface and ProtocolMapper came.

    :param location: location (e.g., code repository) of pipelines
    :type location: str

    """

    SUBTYPE_MAPPING_SECTION = "sample_subtypes"


    def __init__(self, location):

        super(ProtocolInterface, self).__init__()

        if _os.path.isdir(location):
            self.location = location
            self.pipe_iface_path = _os.path.join(
                    location, "config", "pipeline_interface.yaml")
            self.pipe_iface = PipelineInterface(self.pipe_iface_path)
            self.protomap = ProtocolMapper(_os.path.join(
                    location, "config", "protocol_mappings.yaml"))
            self.pipelines_path = _os.path.join(location, "pipelines")

        elif _os.path.isfile(location):
            # Secondary version that passes combined yaml file directly,
            # instead of relying on separate hard-coded config names as above
            self.location = None
            self.pipe_iface_path = location
            self.pipelines_path = _os.path.dirname(location)

            with open(location, 'r') as interface_file:
                iface = yaml.load(interface_file)
            try:
                if "protocol_mapping" in iface:
                    self.protomap = ProtocolMapper(iface["protocol_mapping"])
                else:
                    raise Exception("pipeline_interface file is missing "
                                    "a 'protocol_mapping' section.")
                if "pipelines" in iface:
                    self.pipe_iface = PipelineInterface(iface["pipelines"])
                else:
                    raise Exception("pipeline_interface file is missing "
                                    "a 'pipelines' section.")
            except Exception as e:
                _LOGGER.error(str(iface))
                raise e

        else:
            raise ValueError("Alleged pipelines location '{}' exists neither "
                             "as a file nor as a folder.".format(location))


    def __repr__(self):
        return "ProtocolInterface from '{}'".format(self.location)


    def create_submission_bundle(self, pipeline_key, protocol):
        """
        Create the collection of values needed to submit Sample for processing.

        :param str pipeline_key: key for specific pipeline in a pipeline
            interface mapping declaration
        :param str protocol: name of the relevant protocol
        :return SubmissionBundle: a namedtuple with this ProtocolInterface's
            PipelineInterface, the Sample subtype to use for the submission,
            the pipeline (script) key, and the full pipeline path with
            command-line flags
        """

        subtype = None

        strict_pipe_key, full_pipe_path, full_pipe_path_with_flags = \
                self.pipeline_key_to_path(pipeline_key)
        this_pipeline_data = self.pipe_iface[strict_pipe_key]

        try:
            subtypes = this_pipeline_data[self.SUBTYPE_MAPPING_SECTION]
        except KeyError:
            _LOGGER.debug("%s from '%s' doesn't define section '%s'",
                          self.pipe_iface.__class__.__name__,
                          self.location, self.SUBTYPE_MAPPING_SECTION)
            subtype = Sample
        else:
            if isinstance(subtypes, str):
                subtype_name = subtypes
                _LOGGER.debug("Single subtype name for pipeline '%s' "
                              "in interface from '%s': '%s'", subtype_name,
                              strict_pipe_key, self.location)
            else:
                try:
                    subtype_name = subtypes[protocol]
                except KeyError:
                    subtype = Sample
                    _LOGGER.debug("No %s subtype specified for pipeline '%s' "
                                  "in interface from '%s'", subtype.__name__,
                                  strict_pipe_key, self.location)

        # subtype_name is defined if and only if subtype remained null.
        subtype = subtype or \
                  _import_sample_subtype(full_pipe_path, subtype_name)
        _LOGGER.debug("Using Sample subtype: %s", subtype.__name__)
        return SubmissionBundle(self.pipe_iface, subtype,
                                strict_pipe_key, full_pipe_path_with_flags)


    def fetch(self, protocol):
        """
        Fetch the mapping for a particular protocol, null if unmapped.

        :param str protocol:
        :return str | Iterable[str] | NoneType: pipeline(s) to which the given
            protocol is mapped, otherwise null
        """
        return self.protomap.mappings.get(alpha_cased(protocol))



    def pipeline_key_to_path(self, pipeline_key):
        """
        Given a pipeline_key, return the path to the script for that pipeline
        specified in this pipeline interface config file.

        :param str pipeline_key: the key in the pipeline interface file used
            for the protocol_mappings section. Previously was the script name.
        :return (str, str, str): more precise version of input key, along with
            absolute path for pipeline script, and full script path + options

        """

        # The key may contain extra command-line flags; split key from flags.
        # The strict key is the script name itself, something like "ATACseq.py"
        strict_pipeline_key, _, pipeline_key_args = pipeline_key.partition(' ')

        if self.pipe_iface.get_attribute(strict_pipeline_key, "path"):
            script_path_only = self.pipe_iface.get_attribute(
                    strict_pipeline_key, "path")[0].strip()
            script_path_with_flags = \
                    " ".join([script_path_only, pipeline_key_args])
        else:
            # backwards compatibility w/ v0.5
            script_path_only = strict_pipeline_key
            script_path_with_flags = pipeline_key 

        if not _os.path.isabs(script_path_only):
            script_path_only = _os.path.join(
                    self.pipelines_path, script_path_only)
            script_path_with_flags = _os.path.join(
                    self.pipelines_path, script_path_with_flags)
        if not _os.path.exists(script_path_only):
            _LOGGER.warn(
                    "Missing script command: '{}'".format(script_path_only))
        return strict_pipeline_key, script_path_only, script_path_with_flags



def _import_sample_subtype(pipeline_filepath, subtype_name):
    """
    Import a particular Sample subclass from a Python module.

    :param str pipeline_filepath: path to file to regard as Python module
    :param str subtype_name: name of the target class; this must derive from
        the base Sample class.
    :return type: the imported class, defaulting to base Sample in case of
        failure with the import or other logic
    :raises _UndefinedSampleSubtypeException: if the module is imported but
        type indicated by subtype_name is not found as a class
    """
    base_type = Sample

    _, modname = _os.path.split(pipeline_filepath)
    modname, _ = _os.path.splitext(modname)

    try:
        _LOGGER.debug("Attempting to import module defined by {}, "
                      "calling it {}".format(pipeline_filepath, modname))
        pipeline_module = import_from_source(
            name=modname, module_filepath=pipeline_filepath)
    except ImportError as e:
        _LOGGER.warn("Using base %s because of failure in attempt to "
                     "import pipeline module: %s", base_type.__name__, e)
        return base_type
    else:
        _LOGGER.debug("Successfully imported pipeline module '%s', "
                      "naming it '%s'", pipeline_filepath,
                      pipeline_module.__name__)

    import inspect
    def class_names(cs):
        return ", ".join([c.__name__ for c in cs])

    classes = inspect.getmembers(
            pipeline_module, lambda obj: inspect.isclass(obj))
    _LOGGER.debug("Found %d classes: %s", len(classes), class_names(classes))
    sample_subtypes = filter(lambda c: issubclass(c, base_type), classes)
    _LOGGER.debug("%d %s subtype(s): %s", len(sample_subtypes),
                  base_type.__name__, class_names(sample_subtypes))

    for st in sample_subtypes:
        if st.__name__ == subtype_name:
            _LOGGER.debug("Successfully imported %s from '%s'",
                          subtype_name, pipeline_filepath)
            return st
    raise _UndefinedSampleSubtypeException(
            subtype_name=subtype_name, pipeline_filepath=pipeline_filepath)



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



class _MetadataOperationException(Exception):
    """ Illegal/unsupported operation, motivated by `AttributeDict`. """

    def __init__(self, obj, meta_item):
        """
        Instance with which the access attempt was made, along with the
        name of the reserved/privileged metadata item, define the exception.

        :param object obj: instance with which
            offending operation was attempted
        :param str meta_item: name of the reserved metadata item
        """
        try:
            classname = obj.__class__.__name__
        except AttributeError:
            # Maybe we were given a class or function not an instance?
            classname = obj.__name__
        explanation = "Attempted unsupported operation on {} item '{}'". \
                format(classname, meta_item)
        super(_MetadataOperationException, self).__init__(explanation)



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



class _UndefinedSampleSubtypeException(Exception):
    """ Sample subtype--if declared in PipelineInterface--must be found. """
    def __init__(self, subtype_name, pipeline_filepath):
        reason = "Sample subtype {} cannot be imported from '{}'".\
                format(subtype_name, pipeline_filepath)
        super(_UndefinedSampleSubtypeException, self).__init__(reason)


def _is_member(item, items):
    return item in items
