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
import sys
if sys.version_info < (3, 0):
    from urlparse import urlparse
else:
    from urllib.parse import urlparse
import warnings

import pandas as _pd
import yaml

from . import IMPLICATIONS_DECLARATION
from .utils import \
    alpha_cased, check_bam, check_fastq, expandpath, \
    get_file_size, grab_project_data, import_from_source, parse_ftype, \
    partition, sample_folder, standard_stream_redirector


# TODO: decide if we want to denote functions for export.
__functions__ = []
__classes__ = ["AttributeDict", "PipelineInterface", "Project",
               "ProtocolInterface", "ProtocolMapper", "Sample"]
__all__ = __functions__ + __classes__


COMPUTE_SETTINGS_VARNAME = "PEPENV"
DEFAULT_COMPUTE_RESOURCES_NAME = "default"
DATA_SOURCE_COLNAME = "data_source"
SAMPLE_NAME_COLNAME = "sample_name"
SAMPLE_ANNOTATIONS_KEY = "sample_annotation"
DATA_SOURCES_SECTION = "data_sources"
SAMPLE_EXECUTION_TOGGLE = "toggle"
COL_KEY_SUFFIX = "_key"
VALID_READ_TYPES = ["single", "paired"]

ATTRDICT_METADATA = {"_force_nulls": False, "_attribute_identity": False}

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
    # See https://github.com/epigen/looper/issues/159 for the original issue
    # and https://github.com/epigen/looper/pull/160 for the pull request
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



def copy(obj):
    def copy(self):
        """
        Copy self to a new object.
        """
        from copy import deepcopy

        return deepcopy(self)
    obj.copy = copy
    return obj



def fetch_samples(proj, inclusion=None, exclusion=None):
    """
    Collect samples of particular protocol(s).

    Protocols can't be both positively selected for and negatively
    selected against. That is, it makes no sense and is not allowed to
    specify both inclusion and exclusion protocols. On the other hand, if
    neither is provided, all of the Project's Samples are returned.
    If inclusion is specified, Samples without a protocol will be excluded,
    but if exclusion is specified, protocol-less Samples will be included.

    :param Project proj: the Project with Samples to fetch
    :param Iterable[str] | str inclusion: protocol(s) of interest;
        if specified, a Sample must
    :param Iterable[str] | str exclusion: protocol(s) to include
    :return list[Sample]: Collection of this Project's samples with
        protocol that either matches one of those in inclusion, or either
        lacks a protocol or does not match one of those in exclusion
    :raise TypeError: if both inclusion and exclusion protocols are
        specified; TypeError since it's basically providing two arguments
        when only one is accepted, so remain consistent with vanilla Python2
    """

    # Intersection between inclusion and exclusion is nonsense user error.
    if inclusion and exclusion:
        raise TypeError("Specify only inclusion or exclusion protocols, "
                         "not both.")

    if not inclusion and not exclusion:
        # Simple; keep all samples.  In this case, this function simply
        # offers a list rather than an iterator.
        return list(proj.samples)

    # Ensure that we're working with sets.
    def make_set(items):
        if isinstance(items, str):
            items = [items]
        return {alpha_cased(i) for i in items}

    # Use the attr check here rather than exception block in case the
    # hypothetical AttributeError would occur in alpha_cased; we want such
    # an exception to arise, not to catch it as if the Sample lacks "protocol"
    if not inclusion:
        # Loose; keep all samples not in the exclusion.
        def keep(s):
            return not hasattr(s, "protocol") or \
                   alpha_cased(s.protocol) not in make_set(exclusion)
    else:
        # Strict; keep only samples in the inclusion.
        def keep(s):
            return hasattr(s, "protocol") and \
                   alpha_cased(s.protocol) in make_set(inclusion)

    return list(filter(keep, proj.samples))



def include_in_repr(attr, klazz):
    """
    Determine whether to include attribute in an object's text representation.

    :param str attr: attribute to include/exclude from object's representation
    :param str | type klazz: name of type or type itself of which the object
        to be represented is an instance
    :return bool: whether to include attribute in an object's
        text representation
    """
    classname = klazz.__name__ if isinstance(klazz, type) else klazz
    return attr not in \
           {"Project": ["sheet", "interfaces_by_protocol"]}[classname]



def is_url(maybe_url):
    """
    Determine whether a path is a URL.

    :param str maybe_url: path to investigate as URL
    :return bool: whether path appears to be a URL
    """
    return urlparse(maybe_url).scheme != ""



def merge_sample(sample, merge_table, data_sources=None, derived_columns=None):
    """
    Use merge table data to augment/modify Sample.

    :param Sample sample: sample to modify via merge table data
    :param merge_table: data with which to alter Sample
    :param Mapping data_sources: collection of named paths to data locations,
        optional
    :param Iterable[str] derived_columns: names of columns for which
        corresponding Sample attribute's value is data-derived, optional
    :return Set[str]: names of columns that were merged
    """

    merged_attrs = {}

    if merge_table is None:
        _LOGGER.log(5, "No data for sample merge, skipping")
        return merged_attrs

    if SAMPLE_NAME_COLNAME not in merge_table.columns:
        raise KeyError(
            "Merge table requires a column named '{}'.".
                format(SAMPLE_NAME_COLNAME))

    _LOGGER.debug("Merging Sample with data sources: {}".
                  format(data_sources))
    
    # Hash derived columns for faster lookup in case of many samples/columns.
    derived_columns = set(derived_columns or [])
    _LOGGER.debug("Merging Sample with derived columns: {}".
                  format(derived_columns))

    sample_name = getattr(sample, SAMPLE_NAME_COLNAME)
    sample_indexer = merge_table[SAMPLE_NAME_COLNAME] == sample_name
    this_sample_rows = merge_table[sample_indexer]
    if len(this_sample_rows) == 0:
        _LOGGER.debug("No merge rows for sample '%s', skipping", sample.name)
        return merged_attrs
    _LOGGER.log(5, "%d rows to merge", len(this_sample_rows))
    _LOGGER.log(5, "Merge rows dict: {}".format(this_sample_rows.to_dict()))

    # For each row in the merge table of this sample:
    # 1) populate any derived columns
    # 2) derived columns --> space-delimited strings
    # 3) update the sample values with the merge table
    # Keep track of merged cols,
    # so we don't re-derive them later.
    merged_attrs = {key: "" for key in this_sample_rows.columns}
    
    for _, row in this_sample_rows.iterrows():
        rowdata = row.to_dict()

        # Iterate over column names to avoid Python3 RuntimeError for
        # during-iteration change of dictionary size.
        for attr_name in this_sample_rows.columns:
            if attr_name == SAMPLE_NAME_COLNAME or \
                            attr_name not in derived_columns:
                _LOGGER.log(5, "Skipping merger of attribute '%s'", attr_name)
                continue

            attr_value = rowdata[attr_name]

            # Initialize key in parent dict.
            col_key = attr_name + COL_KEY_SUFFIX
            merged_attrs[col_key] = ""
            rowdata[col_key] = attr_value
            data_src_path = sample.locate_data_source(
                    data_sources, attr_name, source_key=rowdata[attr_name],
                    extra_vars=rowdata)  # 1)
            rowdata[attr_name] = data_src_path

        _LOGGER.log(5, "Adding derived columns")
        
        for attr in derived_columns:
            
            # Skip over any attributes that the sample lacks or that are
            # covered by the data from the current (row's) data.
            if not hasattr(sample, attr) or attr in rowdata:
                _LOGGER.log(5, "Skipping column: '%s'", attr)
                continue
            
            # Map key to sample's value for the attribute given by column name.
            col_key = attr + COL_KEY_SUFFIX
            rowdata[col_key] = getattr(sample, attr)
            # Map the col/attr name itself to the populated data source 
            # template string.
            rowdata[attr] = sample.locate_data_source(
                    data_sources, attr, source_key=getattr(sample, attr),
                    extra_vars=rowdata)
            _LOGGER.debug("PROBLEM adding derived column: "
                          "{}, {}, {}".format(attr, rowdata[attr],
                                              getattr(sample, attr)))

        # Since we are now jamming multiple (merged) entries into a single
        # attribute on a Sample, we have to join the individual items into a
        # space-delimited string and then use that value as the Sample
        # attribute. The intended use case for this sort of merge is for
        # multiple data source paths associated with a single Sample, hence
        # the choice of space-delimited string as the joined-/merged-entry
        # format--it's what's most amenable to use in building up an argument
        # string for a pipeline command.
        for attname, attval in rowdata.items():
            if attname == SAMPLE_NAME_COLNAME or not attval:
                _LOGGER.log(5, "Skipping KV: {}={}".format(attname, attval))
                continue
            _LOGGER.log(5, "merge: sample '%s'; '%s'='%s'",
                        str(sample.name), str(attname), str(attval))
            if attname not in merged_attrs:
                new_attval = str(attval).rstrip()
            else:
                new_attval = "{} {}".format(merged_attrs[attname], str(attval)).strip()
            merged_attrs[attname] = new_attval  # 2)
            _LOGGER.log(5, "Stored '%s' as value for '%s' in merged_attrs",
                        new_attval, attname)

    # If present, remove sample name from the data with which to update sample.
    merged_attrs.pop(SAMPLE_NAME_COLNAME, None)

    _LOGGER.log(5, "Updating Sample {}: {}".format(sample.name, merged_attrs))
    sample.update(merged_attrs)  # 3)
    sample.merged_cols = merged_attrs
    sample.merged = True

    return sample



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
                         "location '%s'", pipe_iface_location)
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



class ProjectContext(object):
    """ Wrap a Project to provide protocol-specific Sample selection. """

    def __init__(self, prj, include_protocols=None, exclude_protocols=None):
        """ Project and what to include/exclude defines the context. """
        self.prj = prj
        self.include = include_protocols
        self.exclude = exclude_protocols

    def __getattr__(self, item):
        """ Samples are context-specific; other requests are handled
        locally or dispatched to Project. """
        if item == "samples":
            return fetch_samples(
                self.prj, inclusion=self.include, exclusion=self.exclude)
        if item in ["prj", "include", "exclude"]:
            # Attributes requests that this context/wrapper handles
            return self.__dict__[item]
        else:
            # Dispatch attribute request to Project.
            return getattr(self.prj, item)

    def __getitem__(self, item):
        return self.prj[item]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass



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
        self.add_entries(entries)


    def add_entries(self, entries):
        """
        Update this `AttributeDict` with provided key-value pairs.

        :param Iterable[(object, object)] | Mapping | pandas.Series entries:
            collection of pairs of keys and values
        """
        if entries is None:
            return
        # Permit mapping-likes and iterables/generators of pairs.
        if callable(entries):
            entries = entries()
        elif isinstance(entries, _pd.Series):
            entries = entries.to_dict()
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
        except (AttributeError, TypeError):
            # Handle potential property and non-string failures.
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
        if isinstance(value, Mapping):
            try:
                # Combine AttributeDict instances.
                self.__dict__[key].add_entries(value)
            except (AttributeError, KeyError):
                # Create new AttributeDict, replacing previous value.
                self.__dict__[key] = AttributeDict(value)
        elif value is not None or \
                key not in self.__dict__ or self.__dict__["_force_nulls"]:
            self.__dict__[key] = value


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

    def __str__(self):
        return "{}: {}".format(self.__class__.__name__, repr(self))



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
    :param compute_env_file: Environment configuration YAML file specifying
        compute settings.
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

        # Ensure data_sources is at least set if it wasn't parsed.
        self.setdefault("data_sources", None)

        self.name = self.infer_name(self.config_file)

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

        self.finalize_pipelines_directory()

        # SampleSheet creation populates project's samples, adds the
        # sheet itself, and adds any derived columns.
        _LOGGER.debug("Processing {} pipeline location(s): {}".
                      format(len(self.metadata.pipelines_dir),
                             self.metadata.pipelines_dir))
        self.interfaces_by_protocol = \
                process_pipeline_interfaces(self.metadata.pipelines_dir)

        path_anns_file = self.metadata.sample_annotation
        _LOGGER.debug("Reading sample annotations sheet: '%s'", path_anns_file)
        try:
            _LOGGER.info("Setting sample sheet from file '%s'", path_anns_file)
            self.sheet = check_sheet(path_anns_file)
        except IOError:
            _LOGGER.error("Alleged annotations file doesn't exist: '%s'",
                          path_anns_file)
            anns_folder_path = _os.path.dirname(path_anns_file)
            try:
                annotations_file_folder_contents = \
                        _os.listdir(anns_folder_path)
            except OSError:
                _LOGGER.error("Annotations file folder doesn't exist either: "
                              "'%s'", anns_folder_path)
            else:
                _LOGGER.error("Annotations file folder's contents: {}".
                              format(annotations_file_folder_contents))
            raise

        self.merge_table = None

        # Basic sample maker will handle name uniqueness check.
        if defer_sample_construction:
            self._samples = None
        else:
            self._set_basic_samples()


    def __repr__(self):
        """ Self-represent in the interpreter. """
        # First, parameterize the attribute filtration function by the class.
        include = partial(include_in_repr, klazz=self.__class__)
        # Then iterate over items, filtering what to include in representation.
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
                protos.add(s.protocol)
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

        :return Iterable[Sample]: Sample instance for each
            of this Project's samples
        """
        if self._samples is None:
            _LOGGER.debug("Building basic sample object(s) for %s",
                          self.__class__.__name__)
            self._set_basic_samples()
        return self._samples


    @property
    def templates_folder(self):
        """
        Path to folder with default submission templates.

        :return str: path to folder with default submission templates
        """
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


    def build_sheet(self, *protocols):
        """
        Create all Sample object for this project for the given protocol(s).

        :return pandas.core.frame.DataFrame: DataFrame with from base version
            of each of this Project's samples, for indicated protocol(s) if
            given, else all of this Project's samples
        """
        # Use all protocols if none are explicitly specified.
        protocols = {alpha_cased(p) for p in (protocols or self.protocols)}
        include_samples = []
        for s in self.samples:
            try:
                proto = s.protocol
            except AttributeError:
                include_samples.append(s)
                continue
            check_proto = alpha_cased(proto)
            if check_proto in protocols:
                include_samples.append(s)
            else:
                _LOGGER.debug("Sample skipped due to protocol ('%s')", proto)
        return _pd.DataFrame(include_samples)
        """
        return _pd.DataFrame(
                [s.as_series() for s in samples if
                 hasattr(s, "protocol") and alpha_cased(s.protocol) in protocols])
        """


    def build_submission_bundles(self, protocol, priority=True):
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

            this_protocol_pipelines = proto_iface.fetch_pipelines(protocol)
            if not this_protocol_pipelines:
                _LOGGER.warn("No mapping for protocol '%s' in %s", 
                             protocol, proto_iface)
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
                                 proto_iface.source, new_scripts))

            # For each pipeline script to which this protocol will pertain,
            # create the new jobs/submission bundles.
            new_jobs = []
            for pipeline_key in new_scripts:
                # Determine how to reference the pipeline and where it is.
                strict_pipe_key, full_pipe_path, full_pipe_path_with_flags = \
                        proto_iface.finalize_pipeline_key_and_paths(
                                pipeline_key)

                # Skip and warn about nonexistent alleged pipeline path.
                if not _os.path.exists(full_pipe_path):
                    _LOGGER.warn(
                            "Missing pipeline script: '%s'", full_pipe_path)
                    continue

                # Determine which interface and Sample subtype to use.
                sample_subtype = \
                        proto_iface.fetch_sample_subtype(
                                protocol, strict_pipe_key, full_pipe_path)
                # Package the pipeline's interface, subtype, command, and key.
                submission_bundle = SubmissionBundle(
                        proto_iface.pipe_iface, sample_subtype,
                        strict_pipe_key, full_pipe_path_with_flags)
                # Add this bundle to the collection of ones relevant for the
                # current ProtocolInterface.
                new_jobs.append(submission_bundle)

            job_submission_bundles.append(new_jobs)

        # Repeat logic check of short-circuit conditional to account for
        # edge case in which it's satisfied during the final iteration.
        if priority and len(job_submission_bundles) > 1:
            return job_submission_bundles[0]
        else:
            return list(itertools.chain(*job_submission_bundles))


    def _check_unique_samples(self):
        """ Handle scenario in which sample names are not unique. """
        # Defining this here but then calling out to the repeats counter has
        # a couple of advantages. We get an unbound, isolated method (the
        # Project-external repeat sample name counter), but we can still
        # do this check from the sample builder, yet have it be override-able.
        repeats = {name: n for name, n in Counter(
                s.name for s in self._samples).items() if n > 1}
        if repeats:
            histogram_text = "\n".join(
                    "{}: {}".format(name, n) for name, n in repeats.items())
            _LOGGER.warn("Non-unique sample names:\n{}".format(histogram_text))


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
        _LOGGER.debug("Creating additional argstring text for pipeline '%s'",
                      pipeline_name)
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


    def _set_basic_samples(self):
        """ Build the base Sample objects from the annotations sheet data. """

        # This should be executed just once, establishing the Project's
        # base Sample objects if they don't already exist.
        if hasattr(self.metadata, "merge_table"):
            if self.merge_table is None:
                if self.metadata.merge_table and \
                        _os.path.isfile(self.metadata.merge_table):
                    _LOGGER.info("Reading merge table: %s",
                                 self.metadata.merge_table)
                    self.merge_table = _pd.read_table(
                        self.metadata.merge_table,
                        sep=None, engine="python")
                    _LOGGER.debug("Merge table shape: {}".
                                  format(self.merge_table.shape))
                else:
                    _LOGGER.debug(
                        "Alleged path to merge table data is not a "
                        "file: '%s'", self.metadata.merge_table)
            else:
                _LOGGER.debug("Already parsed merge table")
        else:
            _LOGGER.debug("No merge table")

        # Set samples and handle non-unique names situation.
        self._samples = self._merge_samples()
        self._check_unique_samples()


    def _merge_samples(self):
        """
        Merge this Project's Sample object and set file paths.

        :return list[Sample]: collection of this Project's Sample objects
        """

        samples = []

        for _, row in self.sheet.iterrows():
            sample = Sample(row.dropna(), prj=self)

            sample.set_genome(self.get("genomes"))
            sample.set_transcriptome(self.get("transcriptomes"))

            _LOGGER.debug("Merging sample '%s'", sample.name)
            merge_sample(sample, self.merge_table,
                         self.data_sources, self.derived_columns)
            _LOGGER.debug("Setting sample file paths")
            sample.set_file_paths(self)
            # Hack for backwards-compatibility
            # Pipelines should now use `data_source`)
            _LOGGER.debug("Setting sample data path")
            try:
                sample.data_path = sample.data_source
            except AttributeError:
                _LOGGER.log(5, "Sample '%s' lacks data source; skipping "
                              "data path assignment", sample.sample_name)
            else:
                _LOGGER.log(5, "Path to sample data: '%s'", sample.data_source)
            samples.append(sample)

        return samples


    def parse_config_file(self, subproject=None):
        """
        Parse provided yaml config file and check required fields exist.
        
        :raises KeyError: if config file lacks required section(s)
        """

        _LOGGER.debug("Setting %s data from '%s'",
                      self.__class__.__name__, self.config_file)
        with open(self.config_file, 'r') as conf_file:
            config = yaml.safe_load(conf_file)

        _LOGGER.debug("{} config data: {}".format(
                self.__class__.__name__, config))

        # Parse yaml into the project's attributes.
        _LOGGER.debug("Adding attributes for {}: {}".format(
                self.__class__.__name__, config.keys()))
        _LOGGER.debug("Config metadata: {}".format(config["metadata"]))
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
        expanded = _os.path.expanduser(_os.path.expandvars(maybe_relpath))
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



@copy
class Sample(AttributeDict):
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
    def __init__(self, series, prj=None):

        # Create data, handling library/protocol.
        data = dict(series)
        try:
            protocol = data.pop("library")
        except KeyError:
            pass
        else:
            data["protocol"] = protocol
        super(Sample, self).__init__(entries=data)

        self.prj = prj
        self.merged_cols = {}
        self.derived_cols_done = []

        if isinstance(series, _pd.Series):
            series = series.to_dict()
        elif isinstance(series, Sample):
            series = series.as_series().to_dict()

        # Keep a list of attributes that came from the sample sheet,
        # so we can create a minimal, ordered representation of the original.
        # This allows summarization of the sample (i.e.,
        # appending new columns onto the original table)
        self.sheet_attributes = series.keys()

        # Ensure Project reference is actual Project or AttributeDict.
        if not isinstance(self.prj, Project):
            self.prj = AttributeDict(self.prj or {})

        # Check if required attributes exist and are not empty.
        missing_attributes_message = self.check_valid()
        if missing_attributes_message:
            raise ValueError(missing_attributes_message)

        # Short hand for getting sample_name
        self.name = self.sample_name

        # Default to no required paths and no YAML file.
        self.required_paths = None
        self.yaml_file = None

        # Not yet merged, potentially toggled when merge step is considered.
        self.merged = False

        # Collect sample-specific filepaths.
        # Only when sample is added to project, can paths be added.
        # Essentially, this provides an empty container for tool-specific
        # filepaths, into which a pipeline may deposit such filepaths as
        # desired. Such use provides a sort of communication interface
        # between times and perhaps individuals (processing time vs.
        # analysis time, and a pipeline author vs. a pipeline user).
        self.paths = Paths()


    def __eq__(self, other):
        return self.__dict__ == other.__dict__


    def __ne__(self, other):
        return not self == other


    def __repr__(self):
        return "Sample '{}': {}".format(self.name, self.__dict__)


    def __str__(self):
        return "Sample '{}'".format(self.name)


    @property
    def input_file_paths(self):
        """
        List the sample's data source / input files

        :return list[str]: paths to data sources / input file for this Sample.
        """
        return self.data_source.split(" ") if self.data_source else []


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
        :return str: message about missing/empty attribute(s); empty string if
            there are no missing/empty attributes
        """
        missing, empty = [], []
        for attr in (required or [SAMPLE_NAME_COLNAME]):
            if not hasattr(self, attr):
                missing.append(attr)
            if attr == "nan":
                empty.append(attr)
        missing_attributes_message = \
                "Sample lacks attribute(s). missing={}; empty={}".\
                        format(missing, empty) if (missing or empty) else ""
        return missing_attributes_message


    def determine_missing_requirements(self):
        """
        Determine which of this Sample's required attributes/files are missing.

        :return (type, str): hypothetical exception type along with message
            about what's missing; null and empty if nothing exceptional
            is detected
        """

        # set_pipeline_attributes must be run first.
        if not hasattr(self, "required_inputs"):
            _LOGGER.warn("You must run set_pipeline_attributes "
                         "before determine_missing_requirements")
            return None, ""

        if not self.required_inputs:
            _LOGGER.debug("No required inputs")
            return None, ""

        # First, attributes
        missing, empty = [], []
        for file_attribute in self.required_inputs_attr:
            _LOGGER.log(5, "Checking '{}'".format(file_attribute))
            try:
                attval = getattr(self, file_attribute)
            except AttributeError:
                _LOGGER.log(5, "Missing required input attribute '%s'",
                             file_attribute)
                missing.append(file_attribute)
                continue
            if attval == "":
                _LOGGER.log(5, "Empty required input attribute '%s'",
                             file_attribute)
                empty.append(file_attribute)
            else:
                _LOGGER.log(5, "'{}' is valid: '{}'".
                              format(file_attribute, attval))

        if missing or empty:
            return AttributeError, \
                   "Missing attributes: {}. Empty attributes: {}".\
                    format(missing, empty)

        # Second, files
        missing_files = []
        for paths in self.required_inputs:
            _LOGGER.log(5, "Text to split and check paths: '%s'", paths)
            # There can be multiple, space-separated values here.
            for path in paths.split(" "):
                _LOGGER.log(5, "Checking path: '{}'".format(path))
                if not _os.path.exists(path):
                    _LOGGER.log(5, "Missing required input file: '{}'".
                                  format(path))
                    missing_files.append(path)

        if not missing_files:
            return None, ""
        else:
            missing_message = \
                    "Missing file(s): {}".format(", ".join(missing_files))
            return IOError, missing_message


    def generate_filename(self, delimiter="_"):
        """
        Create a name for file in which to represent this Sample.

        This uses knowledge of the instance's subtype, sandwiching a delimiter
        between the name of this Sample and the name of the subtype before the
        extension. If the instance is a base Sample type, then the filename
        is simply the sample name with an extension.

        :param str delimiter: what to place between sample name and name of
            subtype; this is only relevant if the instance is of a subclass
        :return str: name for file with which to represent this Sample on disk
        """
        base = self.name if type(self) is Sample else \
            "{}{}{}".format(self.name, delimiter, self.__class__.__name__)
        return "{}.yaml".format(base)


    def generate_name(self):
        """
        Generate name for the sample by joining some of its attribute strings.
        """
        raise NotImplementedError("Not implemented in new code base.")


    def get_attr_values(self, attrlist):
        """
        Get value corresponding to each given attribute.

        :param str attrlist: name of an attribute storing a list of attr names
        :return list | NoneType: value (or empty string) corresponding to
            each named attribute; null if this Sample's value for the
            attribute given by the argument to the "attrlist" parameter is
            empty/null, or if this Sample lacks the indicated attribute
        """
        # If attribute is None, then value is also None.
        attribute_list = getattr(self, attrlist, None)
        if not attribute_list:
            return None

        if not isinstance(attribute_list, list):
            attribute_list = [attribute_list]

        # Strings contained here are appended later so shouldn't be null.
        return [getattr(self, attr, "") for attr in attribute_list]


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


    @property
    def library(self):
        """
        Backwards-compatible alias.

        :return str: The protocol / NGS library name for this Sample.
        """
        warnings.warn("Sample 'library' attribute is deprecated; instead, "
                      "refer to 'protocol'", DeprecationWarning)
        return self.protocol


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
            return None

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
            _LOGGER.debug(
                    "{}: config lacks entry for data_source key: '{}' "
                    "in column '{}'; known: {}".format(
                    self.name, source_key, column_name, data_sources.keys()))
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


    def set_file_paths(self, project=None):
        """
        Sets the paths of all files for this sample.

        :param AttributeDict project: object with pointers to data paths and
            such, either full Project or AttributeDict with sufficient data
        """
        # Any columns specified as "derived" will be constructed
        # based on regex in the "data_sources" section of project config.

        project = project or self.prj

        self.infer_columns(implications=project.get(IMPLICATIONS_DECLARATION))

        for col in project.get("derived_columns", []):
            # Only proceed if the specified column exists
            # and was not already merged or derived.
            if not hasattr(self, col):
                _LOGGER.debug("%s lacks attribute '%s'", self.name, col)
                continue
            elif col in self.merged_cols:
                _LOGGER.debug("'%s' is already merged for %s", col, self.name)
                continue
            elif col in self.derived_cols_done:
                _LOGGER.debug("'%s' has been derived for %s", col, self.name)
                continue
            _LOGGER.debug("Deriving column for %s '%s': '%s'",
                          self.__class__.__name__, self.name, col)

            # Set a variable called {col}_key, so the
            # original source can also be retrieved.
            col_key = col + COL_KEY_SUFFIX
            col_key_val = getattr(self, col)
            _LOGGER.debug("Setting '%s' to '%s'", col_key, col_key_val)
            setattr(self, col_key, col_key_val)

            # Determine the filepath for the current data source and set that
            # attribute on this sample if it's non-empty/null.
            filepath = self.locate_data_source(
                    data_sources=project.get(DATA_SOURCES_SECTION),
                    column_name=col)
            if filepath:
                _LOGGER.debug("Setting '%s' to '%s'", col, filepath)
                setattr(self, col, filepath)
            else:
                _LOGGER.debug("Not setting null/empty value for data source "
                              "'{}': {}".format(col, type(filepath)))

            self.derived_cols_done.append(col)

        # Parent
        self.results_subdir = project.metadata.results_subdir
        self.paths.sample_root = sample_folder(project, self)

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
        """
        Set the genome for this Sample.

        :param Mapping[str, str] genomes: genome assembly by organism name
        """
        self._set_assembly("genome", genomes)
        
        
    def set_transcriptome(self, transcriptomes):
        """
        Set the transcriptome for this Sample.

        :param Mapping[str, str] transcriptomes: transcriptome assembly by
            organism name
        """
        self._set_assembly("transcriptome", transcriptomes)
        
        
    def _set_assembly(self, ome, assemblies):
        if not assemblies:
            _LOGGER.debug("Empty/null assemblies mapping")
            return
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
        req_attr_names = [("ngs_input_files", "ngs_inputs_attr"),
                          ("required_input_files", "required_inputs_attr"),
                          ("all_input_files", "all_inputs_attr")]
        for name_src_attr, name_dst_attr in req_attr_names:
            _LOGGER.log(5, "Value of '%s' will be assigned to '%s'",
                        name_src_attr, name_dst_attr)
            value = pipeline_interface.get_attribute(
                    pipeline_name, name_src_attr)
            _LOGGER.log(5, "Assigning '{}': {}".format(name_dst_attr, value))
            setattr(self, name_dst_attr, value)

        # Post-processing of input attribute assignments.
        # Ensure that there's a valid all_inputs_attr.
        if not self.all_inputs_attr:
            self.all_inputs_attr = self.required_inputs_attr
        # Convert attribute keys into values.
        if self.ngs_inputs_attr:
            _LOGGER.log(5, "Handling NGS input attributes: '%s'", self.name)
            # NGS data inputs exit, so we can add attributes like
            # read_type, read_length, paired.
            self.ngs_inputs = self.get_attr_values("ngs_inputs_attr")

            set_rtype = False
            if not hasattr(self, "read_type"):
                set_rtype_reason = "read_type not yet set"
                set_rtype = True
            elif not self.read_type or self.read_type.lower() \
                    not in VALID_READ_TYPES:
                set_rtype_reason = "current read_type is invalid: '{}'".\
                        format(self.read_type)
                set_rtype = True
            if set_rtype:
                _LOGGER.debug(
                        "Setting read_type for %s '%s': %s",
                        self.__class__.__name__, self.name, set_rtype_reason)
                self.set_read_type(permissive=permissive)
            else:
                _LOGGER.debug("read_type is already valid: '%s'",
                              self.read_type)
        else:
            _LOGGER.log(5, "No NGS inputs: '%s'", self.name)

        # Assign values for actual inputs attributes.
        self.required_inputs = self.get_attr_values("required_inputs_attr")
        self.all_inputs = self.get_attr_values("all_inputs_attr")
        self.input_file_size = get_file_size(self.all_inputs)


    def set_read_type(self, rlen_sample_size=10, permissive=True):
        """
        For a sample with attr `ngs_inputs` set, this sets the 
        read type (single, paired) and read length of an input file.

        :param rlen_sample_size: Number of reads to sample to infer read type,
            default 10.
        :type rlen_sample_size: int
        :param permissive: whether to simply log a warning or error message 
            rather than raising an exception if sample file is not found or 
            otherwise cannot be read, default True.
        :type permissive: bool
        """

        # TODO: determine how return is being used and standardized (null vs. bool)

        # Initialize the parameters in case there is no input_file, so these
        # attributes at least exist - as long as they are not already set!
        for attr in ["read_length", "read_type", "paired"]:
            if not hasattr(self, attr):
                _LOGGER.log(5, "Setting null for missing attribute: '%s'", attr)
                setattr(self, attr, None)

        # ngs_inputs must be set
        if not self.ngs_inputs:
            return False

        ngs_paths = " ".join(self.ngs_inputs)

        # Determine extant/missing filepaths.
        existing_files = list()
        missing_files = list()
        for path in ngs_paths.split(" "):
            if not _os.path.exists(path):
                missing_files.append(path)
            else:
                existing_files.append(path)
        _LOGGER.debug("{} extant file(s): {}".
                      format(len(existing_files), existing_files))
        _LOGGER.debug("{} missing file(s): {}".
                      format(len(missing_files), missing_files))

        # For samples with multiple original BAM files, check all.
        files = list()
        check_by_ftype = {"bam": check_bam, "fastq": check_fastq}
        for input_file in existing_files:
            try:
                file_type = parse_ftype(input_file)
                read_lengths, paired = check_by_ftype[file_type](
                        input_file, rlen_sample_size)
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

            # Determine most frequent read length among sample.
            rlen, _ = sorted(read_lengths.items(), key=itemgetter(1))[-1]
            _LOGGER.log(5,
                    "Selected {} as most frequent read length from "
                    "sample read length distribution: {}".format(
                            rlen, read_lengths))

            # Decision about paired-end status is majority-rule.
            if paired > (rlen_sample_size / 2):
                read_type = "paired"
                paired = True
            else:
                read_type = "single"
                paired = False

            files.append([rlen, read_type, paired])

        # Check agreement between different files
        # if all values are equal, set to that value;
        # if not, set to None and warn the user about the inconsistency
        for i, feature in enumerate(self._FEATURE_ATTR_NAMES):
            feature_values = set(f[i] for f in files)
            if 1 == len(feature_values):
                feat_val = files[0][i]
            else:
                _LOGGER.log(5, "%d values among %d files for feature '%s'",
                            len(feature_values), len(files), feature)
                feat_val = None
            _LOGGER.log(5, "Setting '%s' on %s to %s",
                        feature, self.__class__.__name__, feat_val)
            setattr(self, feature, feat_val)

            if getattr(self, feature) is None and len(existing_files) > 0:
                _LOGGER.warn("Not all input files agree on '%s': '%s'",
                             feature, self.name)


    def to_yaml(self, path=None, subs_folder_path=None, delimiter="_"):
        """
        Serializes itself in YAML format.

        :param str path: A file path to write yaml to; provide this or
            the subs_folder_path
        :param str subs_folder_path: path to folder in which to place file
            that's being written; provide this or a full filepath
        :param str delimiter: text to place between the sample name and the
            suffix within the filename; irrelevant if there's no suffix
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
            _LOGGER.debug("Creating filename for %s: '%s'",
                          self.__class__.__name__, self.name)
            filename = self.generate_filename(delimiter=delimiter)
            _LOGGER.debug("Filename: '%s'", filename)
            path = _os.path.join(subs_folder_path, filename)

        _LOGGER.debug("Setting %s filepath: '%s'",
                      self.__class__.__name__, path)
        self.yaml_file = path

        def _is_project(obj, name=None):
            """ Determine if item to prep for disk is Sample's project. """
            return name == "prj"

        def obj2dict(obj, name=None,
                to_skip=("merge_table", "samples", "sheet", "sheet_attributes")):
            """
            Build representation of object as a dict, recursively
            for all objects that might be attributes of self.

            :param object obj: what to serialize to write to YAML.
            :param str name: name of the object to represent.
            :param Iterable[str] to_skip: names of attributes to ignore.
            """
            if name:
                _LOGGER.log(5, "Converting to dict: '{}'".format(name))
            if _is_project(obj, name):
                _LOGGER.debug("Attempting to store %s's project metadata",
                              self.__class__.__name__)
                prj_data = grab_project_data(obj)
                _LOGGER.debug("Sample's project data: {}".format(prj_data))
                return {k: obj2dict(v, name=k) for k, v in prj_data.items()}
            if isinstance(obj, list):
                return [obj2dict(i) for i in obj]
            if isinstance(obj, AttributeDict):
                return {k: obj2dict(v, name=k) for k, v in obj.__dict__.items()
                        if k not in to_skip and
                        (k not in ATTRDICT_METADATA or
                         v != ATTRDICT_METADATA[k])}
            elif isinstance(obj, Mapping):
                return {k: obj2dict(v, name=k)
                        for k, v in obj.items() if k not in to_skip}
            elif isinstance(obj, (Paths, Sample)):
                return {k: obj2dict(v, name=k)
                        for k, v in obj.__dict__.items() if
                        k not in to_skip}
            elif isinstance(obj, _pd.Series):
                _LOGGER.warn("Serializing series as mapping, not array-like")
                return obj.to_dict()
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

        # TODO: this is the way to add the project metadata reference if
        # the metadata items are to be accessed directly on the Sample rather
        # than through the Project; that is:
        #
        # sample.output_dir
        # instead of
        # sample.prj.output_dir
        #
        # In this case, "prj" should be added to the default argument to the
        # to_skip parameter in the function signature, and the instance check
        # of the object to serialize against Project can be dropped.
        """
        try:
            serial.update(self.prj.metadata)
        except AttributeError:
            _LOGGER.debug("%s lacks %s reference",
                          self.__class__.__name__, Project.__class__.__name__)
        else:
            _LOGGER.debug("Added %s metadata to serialized %s",
                          Project.__class__.__name__, self.__class__.__name__)
        """

        with open(self.yaml_file, 'w') as outfile:
            _LOGGER.debug("Generating YAML data for %s: '%s'",
                          self.__class__.__name__, self.name)
            try:
                yaml_data = yaml.safe_dump(serial, default_flow_style=False)
            except yaml.representer.RepresenterError:
                _LOGGER.error("SERIALIZED SAMPLE DATA: {}".format(serial))
                raise
            outfile.write(yaml_data)


    def update(self, newdata):
        """
        Update Sample object with attributes from a dict.
        """
        for key, value in newdata.items():
            setattr(self, key, value)



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
            return self.pipe_iface_config[pipeline_name] or {}
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

        if not _os.path.isabs(script_path_only):
            _LOGGER.log(5, "Expanding non-absolute script path: '%s'",
                        script_path_only)
            script_path_only = _os.path.join(
                    self.pipelines_path, script_path_only)
            _LOGGER.log(5, "Absolute script path: '%s'", script_path_only)
            script_path_with_flags = _os.path.join(
                    self.pipelines_path, script_path_with_flags)
            _LOGGER.log(5, "Absolute script path with flags: '%s'",
                        script_path_with_flags)

        if not _os.path.exists(script_path_only):
            _LOGGER.warn(
                    "Missing pipeline script: '%s'", script_path_only)

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
