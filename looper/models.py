"""
Models for NGS projects
=======================

Workflow explained:
    - Project is created
    - Add Sample sheet to project (spawns next)
        - Samples are created and added to project (automatically)

In the process, stuff is checked:
    - project structure (created if not existing)
    - existence of csv sample sheet with minimal fields
    - Constructing a path to a sample's input file and checking for its existence
    - read type/length of samples (optionally)

Example:

.. code-block:: python

    from models import Project
    prj = Project("config.yaml")
    prj.add_sample_sheet()
    # that's it!

Explore!

.. code-block:: python

    # see all samples
    prj.samples
    # get fastq file of first sample
    prj.samples[0].fastq
    # get all bam files of WGBS samples
    [s.mapped for s in prj.samples if s.library == "WGBS"]

    prj.metadata.results  # results directory of project
    # export again the project's annotation
    prj.sheet.to_csv(os.path.join(prj.metadata.output_dir, "sample_annotation.csv"))

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
    defaultdict, Iterable, Mapping, MutableMapping, OrderedDict as _OrderedDict
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
    parse_ftype, check_bam, check_fastq, get_file_size, partition


DATA_SOURCE_COLNAME = "data_source"
SAMPLE_NAME_COLNAME = "sample_name"
SAMPLE_ANNOTATIONS_KEY = "sample_annotation"
IMPLICATIONS_DECLARATION = "implied_columns"
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



@copy
class Paths(object):
    """ A class to hold paths as attributes. """

    def __str__(self):
        return "Paths object."

    def __iter__(self):
        """
        Iteration is over the paths themselves.
        
        Note that this implementation constrains the assignments to be 
        non-nested. That is, the value for any attribute attached to the 
        instance should be a path.
        
        """
        return iter(self.__dict__.values())

    def __getitem__(self, key):
        """
        Provides dict-style access to attributes
        """
        return getattr(self, key)



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
        Fetch the value associated with the provided identifier. Unlike an
        ordinary object, `AttributeDict` supports fetching

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
        :raises MetadataOperationException: if attempt is made
            to set value for privileged metadata key
        """
        _LOGGER.log(5, "Executing __setitem__ for '{}', '{}'".
                    format(key, str(value)))
        if isinstance(value, Mapping):
            try:
                # Combine AttributeDict instances.
                _LOGGER.debug("Updating key: '{}'".format(key))
                self.__dict__[key].add_entries(value)
            except (AttributeError, KeyError):
                # Create new AttributeDict, replacing previous value.
                self.__dict__[key] = AttributeDict(value)
            _LOGGER.debug("'{}' now has keys {}".
                          format(key, self.__dict__[key].keys()))
        elif value is not None or \
                key not in self.__dict__ or self.__dict__["_force_nulls"]:
            _LOGGER.log(5, "Setting '{}' to {}".format(key, value))
            self.__dict__[key] = value
        else:
            _LOGGER.debug("Not setting {k} to {v}; _force_nulls: {nulls}".
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
            raise MetadataOperationException(self, item)
        try:
            del self.__dict__[item]
        except KeyError:
            _LOGGER.debug("No item {} to delete".format(item))

    def __eq__(self, other):
        for k in iter(self):
            if k in other and self.__dict__[k] == other[k]:
                continue
            return False
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



@copy
class Project(AttributeDict):
    """
    A class to model a Project.

    :param config_file: Project config file (YAML).
    :type config_file: str
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

    :Example:

    .. code-block:: python

        from models import Project
        prj = Project("config.yaml")
    """

    DERIVED_COLUMNS_DEFAULT = [DATA_SOURCE_COLNAME]


    def __init__(self, config_file, default_compute, 
                 subproject=None, dry=False, permissive=True, 
                 file_checks=False, compute_env_file=None):

        super(Project, self).__init__()

        _LOGGER.info("Creating %s from file: '%s'",
                          self.__class__.__name__, config_file)

        # Initialize local, serial compute as default (no cluster submission)
        # Start with default compute settings.
        _LOGGER.debug("Establishing default environment settings")
        self.update_environment(default_compute)
        
        # Ensure that update set environment attributes.
        if self.environment is None or self.environment_file is None:
            raise RuntimeError(
                "Failed to establish environment settings from data in '{}'.".
                format(default_compute))

        # Load settings from environment yaml for local compute infrastructure.
        if not compute_env_file:
            _LOGGER.info("Using default {envvar}. You may set environment "
                              "variable {envvar} to configure environment "
                              "settings.".format(envvar=self.compute_env_var))
        else:
            _LOGGER.debug("Updating environment settings based on file '%s'", 
                          compute_env_file)
            self.update_environment(compute_env_file)

        # Initialize default compute settings.
        _LOGGER.debug("Establishing project compute settings")
        self.set_compute("default")
        if self.compute is None:
            raise RuntimeError("Failed to establish project compute settings")

        _LOGGER.debug("Compute: %s", str(self.compute))

        # optional configs
        self.permissive = permissive
        self.file_checks = file_checks

        # include the path to the config file
        self.config_file = _os.path.abspath(config_file)

        # Parse config file
        _LOGGER.info("Parsing %s config file", self.__class__.__name__)
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

        # Sheet will be set to non-null value by call to add_sample_sheet().
        # That call also sets the samples (list) attribute for the instance
        # and adds default derived columns.
        self.sheet = None
        self.samples = list()
        self.add_sample_sheet()

        self.finalize_pipelines_directory()


    @property
    def compute_env_var(self):
        """
        Environment variable through which to access compute settings.
        
        :return str: name of the environment variable to pointing to 
            compute settings
        """
        return "COMPUTE_SETTINGS"


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
    def project_folders(self):
        """
        Names of folders to nest within a project output directory.
        
        :return Iterable[str]: names of output-nested folders
        """
        return ["results_subdir", "submission_subdir"]


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
                _LOGGER.debug("%s lacks relative section '%s', skipping",
                                   self.__class__.__name__, sect)
                continue
            relative_vars = getattr(self, sect)
            if not relative_vars:
                _LOGGER.debug("No relative variables, continuing")
                continue
            for var in relative_vars.keys():
                if not hasattr(relative_vars, var) or \
                                getattr(relative_vars, var) is None:
                    continue

                relpath = getattr(relative_vars, var)
                _LOGGER.debug("Ensuring absolute path(s) for '%s'", var)
                # Parsed from YAML, so small space of possible datatypes.
                if isinstance(relpath, list):
                    setattr(relative_vars, var,
                            [self._ensure_absolute(maybe_relpath)
                             for maybe_relpath in relpath])
                else:
                    abs_path = self._ensure_absolute(relpath)
                    _LOGGER.debug("Setting '%s' to '%s'", var, abs_path)
                    setattr(relative_vars, var, abs_path)

        # compute.submission_template could have been reset by project config
        # into a relative path; make sure it stays absolute.
        if not _os.path.isabs(self.compute.submission_template):
            # Relative to environment config file.
            self.compute.submission_template = _os.path.join(
                    _os.path.dirname(self.environment_file),
                    self.compute.submission_template
            )

        # Required variables check
        if not hasattr(self.metadata, SAMPLE_ANNOTATIONS_KEY):
            raise MissingMetadataException(
                    missing_section=SAMPLE_ANNOTATIONS_KEY, 
                    path_config_file=self.config_file)


    def _ensure_absolute(self, maybe_relpath):
        _LOGGER.debug("Ensuring absolute path for '%s'", maybe_relpath)
        if _os.path.isabs(maybe_relpath) or is_url(maybe_relpath):
            _LOGGER.debug("Already absolute")
            return maybe_relpath
        # Maybe we have env vars that make the path absolute?
        expanded = _os.path.expandvars(maybe_relpath)
        _LOGGER.debug("Expanded: '%s'", expanded)
        if _os.path.isabs(expanded):
            _LOGGER.debug("Expanded is absolute")
            return expanded
        _LOGGER.debug("Making non-absolute path '%s' be absolute",
                      maybe_relpath)
        # Set path to an absolute path, relative to project config.
        config_dirpath = _os.path.dirname(self.config_file)
        _LOGGER.debug("config_dirpath: %s", config_dirpath)
        abs_path = _os.path.join(config_dirpath, maybe_relpath)
        return abs_path


    def update_environment(self, env_settings_file):
        """
        Parse data from environment configuration file.

        :param str env_settings_file: path to file with 
            new environment configuration data
        """
        try:
            with open(env_settings_file, 'r') as handle:
                _LOGGER.info("Loading %s: %s",
                             self.compute_env_var, env_settings_file)
                env_settings = yaml.load(handle)
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
                if hasattr(self, "environment"):
                    self.environment.add_entries(env_settings)
                else:
                    self.environment = AttributeDict(env_settings)

            self.environment_file = env_settings_file

        except Exception as e:
            _LOGGER.error("Can't load environment config file '%s'", 
                          str(env_settings_file))
            _LOGGER.error(str(type(e).__name__) + str(e))


    def make_project_dirs(self):
        """
        Creates project directory structure if it doesn't exist.
        """
        for folder_name in self.project_folders:
            folder_path = self.metadata[folder_name]
            _LOGGER.debug("Ensuring project dir exists: '%s'", folder_path)
            if not _os.path.exists(folder_path):
                _LOGGER.debug("Creating: '%s'", folder_path)
                _os.makedirs(folder_path)


    def set_project_permissions(self):
        """
        Makes the project's public_html folder executable.
        """
        for d in [self.trackhubs.trackhub_dir]:
            try:
                _os.chmod(d, 0o0755)
            except OSError:
                # This currently does not fail now
                # ("cannot change folder's mode: %s" % d)
                continue


    def set_compute(self, setting):
        """
        Sets the compute attributes according to the specified settings in the environment file
        :param: setting	An option for compute settings as specified in the environment file.
        """

        if setting and \
                hasattr(self, "environment") and \
                hasattr(self.environment, "compute"):
            _LOGGER.debug("Loading compute settings: '%s'", str(setting))
            if hasattr(self, "compute"):
                _LOGGER.debug("Adding compute entries for setting %s",
                                   setting)
                self.compute.add_entries(self.environment.compute[setting].__dict__)
            else:
                _LOGGER.debug("Creating compute entries for setting '%s'",
                                   setting)
                self.compute = AttributeDict(self.environment.compute[setting].__dict__)

            _LOGGER.debug("%s: %s", str(setting),
                               self.environment.compute[setting])
            _LOGGER.debug("Compute: %s", str(self.environment.compute))

            if not _os.path.isabs(self.compute.submission_template):
                # Relative to environment config file.
                self.compute.submission_template = _os.path.join(
                        _os.path.dirname(self.environment_file),
                        self.compute.submission_template)
        else:
            _LOGGER.warn("Cannot load compute settings: %s (%s)",
                         setting, str(type(setting)))


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

        default_argtext, pipeline_argtext = \
                create_argtext("default"), create_argtext(pipeline_name)

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


    def add_sample_sheet(self, csv=None):
        """
        Build a `SampleSheet` object from a csv file and
        add it and its samples to the project.

        :param csv: Path to csv file.
        :type csv: str
        """

        _LOGGER.debug("Adding sample sheet")

        # Make SampleSheet object
        # By default read sample_annotation, but allow explict CSV arg.
        self.sheet = SampleSheet(csv or self.metadata.sample_annotation)

        # Pair project and sheet.
        self.sheet.prj = self

        # Generate sample objects from annotation sheet.
        _LOGGER.debug("Creating samples from annotation sheet")
        self.sheet.make_samples()

        # Add samples to Project
        for sample in self.sheet.samples:
            # Overwritten later if merged
            sample.merged = False
            self.add_sample(sample)		# Appends sample to self.samples.

        # Merge sample files (!) using merge table if provided:
        if hasattr(self.metadata, "merge_table"):
            if self.metadata.merge_table is not None:
                if _os.path.isfile(self.metadata.merge_table):
                    # read in merge table
                    name, extension = _os.path.splitext(self.metadata.merge_table)
                    if extension == ".tsv":
                        merge_table = _pd.read_csv(self.metadata.merge_table, sep='\t')
                    else:
                        merge_table = _pd.read_csv(self.metadata.merge_table)

                    if SAMPLE_NAME_COLNAME not in merge_table.columns:
                        raise KeyError(
                                "Merge table requires a column named '{}'.".
                                format(SAMPLE_NAME_COLNAME))

                    for sample in self.sheet.samples:
                        sample_indexer = \
                                merge_table[SAMPLE_NAME_COLNAME] == sample.name
                        merge_rows = merge_table[sample_indexer]

                        # Check if there are rows in the
                        # merge table for this sample:
                        if len(merge_rows) > 0:
                            # For each row in the merge table of this sample:
                            # 1) populate any derived columns
                            # 2) derived columns --> space-delimited strings
                            # 3) update the sample values with the merge table

                            # Keep track of merged cols,
                            # so we don't re-derive them later.
                            merged_cols = {
                                    key: "" for key in merge_rows.columns}
                            for row in merge_rows.index:
                                _LOGGER.debug(
                                    "New row: {}, {}".format(row, merge_rows))
                                # Update with derived columns
                                row_dict = merge_rows.ix[row].to_dict()
                                for col in merge_rows.columns:
                                    if col == SAMPLE_NAME_COLNAME or \
                                            col not in self.derived_columns:
                                        continue
                                    # Initialize key in parent dict.
                                    col_key = col + COL_KEY_SUFFIX
                                    merged_cols[col_key] = ""
                                    row_dict[col_key] = row_dict[col]
                                    row_dict[col] = sample.locate_data_source(
                                        col, row_dict[col], row_dict)  # 1)

                                # Also add in any derived cols present.
                                for col in self.derived_columns:
                                    if not hasattr(sample, col) or \
                                            col in row_dict:
                                        # Unproblematic
                                        continue
                                    _LOGGER.debug(
                                        "PROBLEM adding derived column: '%s'",
                                        str(col))
                                    col_key = col + COL_KEY_SUFFIX
                                    row_dict[col_key] = getattr(sample, col)
                                    row_dict[col] = sample.locate_data_source(
                                        col, getattr(sample,col), row_dict)
                                    _LOGGER.debug(
                                        "PROBLEM adding derived column: "
                                        "'%s', %s, %s",
                                        str(col), str(row_dict[col]),
                                        str(getattr(sample, col)))

                                # Since we are now jamming multiple (merged)
                                # entries into a single attribute, we have to
                                # join them into a space-delimited string
                                # and then set to sample attribute.
                                for key, val in row_dict.items():
                                    if key == SAMPLE_NAME_COLNAME or not val:
                                        continue
                                    _LOGGER.debug("merge: sample '%s'; %s=%s",
                                                  str(sample.name), 
                                                  str(key), str(val))
                                    if not key in merged_cols:
                                        new_val = str(val).rstrip()
                                    else:
                                        new_val = "{} {}".format(
                                            merged_cols[key], str(val)).strip()
                                    merged_cols[key] = new_val    # 2)

                            # Don't update sample_name.
                            merged_cols.pop(SAMPLE_NAME_COLNAME, None)

                            sample.update(merged_cols)    # 3)
                            sample.merged = True    # mark sample as merged
                            sample.merged_cols = merged_cols

        # With all samples, prepare file paths.
        for sample in self.sheet.samples:
            if hasattr(sample, "organism"):
                sample.get_genome_transcriptome()
            sample.set_file_paths()
            # Hack for backwards-compatibility
            # Pipelines should now use `data_source`)
            try:
                sample.data_path = sample.data_source
            except AttributeError:
                _LOGGER.debug("Sample '%s' lacks data source --> skipping "
                              "data path assignment", sample.sample_name)


    def add_sample(self, sample):
        """
        Adds a sample to the project's `samples`.
        """
        # Check sample is Sample object
        if not isinstance(sample, Sample):
            raise TypeError("Provided object is not a Sample object.")

        # Tie sample and project bilaterally
        sample.prj = self
        # Append
        self.samples.append(sample)



@copy
class SampleSheet(object):
    """
    Class to model a sample annotation sheet.

    :param path: Path to csv file.
    :type path: str
    :param dtype: Data type to read csv file as. Default is str.
    :type dtype: type

    :Example:

    .. code-block:: python

        from models import Project, SampleSheet
        prj = Project("config.yaml")
        sheet = SampleSheet("sheet.csv")
    """

    def __init__(self, path, dtype=str):
        super(SampleSheet, self).__init__()
        self.df = self.check_sheet(path, dtype)
        self.path = path
        self.samples = list()

    def __repr__(self):
        if hasattr(self, "prj"):
            return "SampleSheet for project '%s' with %i samples." % \
                   (self.prj, len(self.df))
        else:
            return "SampleSheet with %i samples." % len(self.df)


    @staticmethod
    def check_sheet(sample_file, dtype):
        """
        Check if csv file exists and has all required columns.
        
        :param str sample_file: path to sample annotations file.
        :param type dtype: data type for CSV read.
        :raises IOError: if given annotations file can't be read.
        :raises ValueError: if required column(s) is/are missing.
        """

        name, extension = _os.path.splitext(sample_file)
        if extension == ".tsv":
            df = _pd.read_csv(sample_file, sep='\t')
        else:
            df = _pd.read_csv(sample_file)

        req = [SAMPLE_NAME_COLNAME]
        missing = set(req) - set(df.columns)
        if len(missing) != 0:
            raise ValueError(
                "Annotation sheet ('{}') is missing column(s): {}".format(
                        sample_file, ", ".join(['{}'.format(missing_colname)
                                                for missing_colname in missing])))
        return df


    @staticmethod
    def alpha_cased(text, lower=False):
        """
        Filter text to just letters and homogenize case.
        
        :param str text: what to filter and homogenize.
        :param bool lower: whether to convert to lowercase; default uppercase.
        :return str: input filtered to just letters, with homogenized case.
        """
        text = "".join(filter(lambda c: c.isalpha(), text))
        return text.lower() if lower else text.upper()


    def make_samples(self):
        """
        Create samples from annotation sheet (considering library), 
        and them to the project.
        """

        found_pipelines = False
        try:
            import pipelines  # Use a pipelines package if installed.
        except ImportError:
            # pipelines_dir is optional.
            pipeline_dirpaths = getattr(
                    self.prj.metadata, "pipelines_dir", None)
            if pipeline_dirpaths:
                if isinstance(pipeline_dirpaths, str):
                    pipeline_dirpaths = [pipeline_dirpaths]
                sys.path.extend(pipeline_dirpaths)
                _LOGGER.debug(
                    "Added {} pipelines path(s) to sys.path: {}".
                        format(len(pipeline_dirpaths), pipeline_dirpaths))
            try:
                import pipelines
            except ImportError:
                pass
            else:
                found_pipelines = True
        else:
            found_pipelines = True

        if not found_pipelines:
            # Just return a basic Sample for each of the sheet's rows.
            def make_sample(data):
                return Sample(data)
        else:
            # Attempt creation of Sample subtype specific to protocol.

            # Get all pipelines package Sample subclasses.
            import inspect
            from utils import fetch_package_classes
            sample_types = fetch_package_classes(pipelines,
                    lambda maybe_class: inspect.isclass(maybe_class)
                                        and issubclass(maybe_class, Sample))

            # TODO: perhaps modify or alter handling of need for __library__.
            pairing = {self.alpha_cased(sample_class.__library__): sample_class
                       for sample_type, sample_class in sample_types}

            def make_sample(data):
                try:
                    return pairing[self.alpha_cased(data.library)](data)
                except (AttributeError, KeyError):
                    return Sample(data)

        for i in range(len(self.df)):
            self.samples.append(make_sample(self.df.ix[i].dropna()))


    def as_data_frame(self):
        """
        Returns a `pandas.DataFrame` representation of self.
        """
        return _pd.DataFrame([s.as_series() for s in self.samples])


    def to_csv(self, path):
        """
        Saves a csv annotation sheet from the samples.

        :param path: Path to csv file to be written.
        :type path: str

        :Example:

        .. code-block:: python

            from models import SampleSheet
            sheet = SampleSheet("/projects/example/sheet.csv")
            sheet.to_csv("~/projects/example/sheet2.csv")
        """
        df = self.as_data_frame()
        # TODO: decide which--if any--attributes to drop here.
        df.to_csv(path, index=False)



@copy
class Sample(object):
    """
    Class to model Samples based on a pandas Series.

    :Example:

    .. code-block:: python

        from models import Project, SampleSheet, Sample
        prj = Project("ngs")
        sheet = SampleSheet("~/projects/example/sheet.csv", prj)
        s1 = Sample(sheet.ix[0])
    """

    _FEATURE_ATTR_NAMES = ["read_length", "read_type", "paired"]

    # Originally, this object was inheriting from _pd.Series,
    # but complications with serializing and code maintenance
    # made me go back and implement it as a top-level object
    def __init__(self, series):
        """
        Instantiate `Sample` with data from given series.
        
        :param pandas.core.series.Series series: data for instance
        :raises ValueError: if data lacks required attribute(s)
        """
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

        # Default to no required paths
        self.required_paths = None

        # Sample dirs
        self.paths = Paths()
        # Only when sample is added to project, can paths be added -
        # This is because sample-specific files will be created in a
        # data root directory dependent on the project.
        # The SampleSheet object, after being added to a project, will
        # call Sample.set_file_paths().

    def __repr__(self):
        return "Sample '{}'".format(self.name)

    def __getitem__(self, item):
        """
        Provides dict-style access to attributes
        """
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)


    def update(self, newdata):
        """
        Update Sample object with attributes from a dict.
        """
        for key, value in newdata.items():
            setattr(self, key, value)


    def check_valid(self, required=None):
        """
        Check provided sample annotation is valid.

        It requires the field `sample_name` is existent and non-empty.
        """
        lacking = defaultdict(list)
        for attr in required or [SAMPLE_NAME_COLNAME]:
            if not hasattr(self, attr):
                lacking["missing"].append(attr)
            if attr == "nan":
                lacking["empty"].append(attr)
        return lacking


    def generate_name(self):
        """
        Generate name for the sample by joining some of its attribute strings.
        """
        raise NotImplementedError("Not implemented in new code base.")


    def as_series(self):
        """
        Returns a `pandas.Series` object with all the sample's attributes.

        :return pandas.core.series.Series: pandas Series representation 
            of this Sample, with its attributes.
        """
        return _pd.Series(self.__dict__)


    def to_yaml(self, path=None):
        """
        Serializes itself in YAML format.

        :param str path: A file path to write yaml to.
        """
        def obj2dict(obj, to_skip=("samples", "sheet", "sheet_attributes")):
            """
            Build representation of object as a dict, recursively
            for all objects that might be attributes of self.

            :param object obj: what to serialize to write to YAML.
            :param tuple[str] to_skip: names of attributes to ignore.
\            """
            if isinstance(obj, list):
                return [obj2dict(i) for i in obj]
            if isinstance(obj, AttributeDict):
                return {k: obj2dict(v) for k, v in obj.__dict__.items() if k not in to_skip and (k not in ATTRDICT_METADATA or v != ATTRDICT_METADATA[k])}
            elif isinstance(obj, Mapping):
                return {k: obj2dict(v)
                        for k, v in obj.items() if k not in to_skip}
            elif isinstance(obj, (Paths, Sample)):
                return {k: obj2dict(v)
                        for k, v in obj.__dict__.items() if k not in to_skip}
            elif hasattr(obj, 'dtype'):  # numpy data types
                # TODO: this fails with ValueError for multi-element array.
                return obj.item()
            elif _pd.isnull(obj):
                # Missing values as evaluated by pd.isnull().
                # This gets correctly written into yaml.
                return "NaN"
            else:
                return obj

        # If path is not specified, use default:
        # prj.metadata.submission_dir + sample_name + yaml
        yaml_file = path or _os.path.join(self.prj.metadata.submission_subdir,
                                          self.sample_name + ".yaml")
        serial = obj2dict(self)
        with open(yaml_file, 'w') as outfile:
            outfile.write(yaml.safe_dump(serial, default_flow_style=False))


    def locate_data_source(self, column_name=DATA_SOURCE_COLNAME,
                           source_key=None, extra_vars=None):
        """
        Uses the template path provided in the project config section 
        "data_sources" to piece together an actual path by substituting 
        variables (encoded by "{variable}"") with sample attributes.

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
            with variable substitions made
        """

        sources_section = "data_sources"

        if not source_key:
            try:
                source_key = getattr(self, column_name)
            except AttributeError:
                reason = "'{attr}': to locate sample's data source, provide " \
                         "the name of a key from '{sources}' or ensure " \
                         "sample has attribute '{attr}'".format(
                         attr=column_name, sources=sources_section)
                raise AttributeError(reason)

        try:
            regex = self.prj[sources_section][source_key]
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


    def get_genome_transcriptome(self):
        """
        Get genome and transcriptome, based on project config file.
        If not available (matching config), genome and transcriptome will be set to sample.organism.
        """
        try:
            self.genome = getattr(self.prj.genomes, self.organism)
        except AttributeError:
            _LOGGER.warn("Project config lacks genome mapping for "
                              "organism '%s'", str(self.organism))
        try:
            self.transcriptome = getattr(self.prj.transcriptomes, self.organism)
        except AttributeError:
            _LOGGER.warn("Project config lacks transcriptome mapping for "
                              "organism '%s'", str(self.organism))


    def set_file_paths(self):
        """
        Sets the paths of all files for this sample.
        """
        # Any columns specified as "derived" will be constructed
        # based on regex in the "data_sources" section of project config.

        for col in self.prj.derived_columns:
            # Only proceed if the specified column exists
            # and was not already merged or derived.
            if hasattr(self, col) and col not in self.merged_cols \
                    and col not in self.derived_cols_done:
                # Set a variable called {col}_key, so the
                # original source can also be retrieved.
                setattr(self, col + COL_KEY_SUFFIX, getattr(self, col))
                setattr(self, col, self.locate_data_source(col))
                self.derived_cols_done.append(col)

        self.infer_columns()

        # Parent
        self.results_subdir = self.prj.metadata.results_subdir
        self.paths.sample_root = _os.path.join(
                self.prj.metadata.results_subdir, self.sample_name)

        # Track url
        bigwig_filename = self.name + ".bigWig"
        try:
            # Project's public_html folder
            self.bigwig = _os.path.join(
                    self.prj.trackhubs.trackhub_dir, bigwig_filename)
            self.track_url = \
                    "{}/{}".format(self.prj.trackhubs.url, bigwig_filename)
        except:
            _LOGGER.debug("No trackhub/URL")
            pass


    def infer_columns(self):
        """
        Infer value for additional field(s) from other field(s).
        
        Add columns/fields to the sample based on values in those already-set 
        that the sample's project defines as indicative of implications for 
        additional data elements for the sample.
        
        :return None: this function mutates state and is strictly for effect
        """
        if not hasattr(self.prj, IMPLICATIONS_DECLARATION):
            return

        impliers = self.prj[IMPLICATIONS_DECLARATION]

        _LOGGER.debug(
                "Sample variable(s) that can imply others: %s", str(impliers))
        for implier_name, implied in impliers.items():
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


    def make_sample_dirs(self):
        """
        Creates sample directory structure if it doesn't exist.
        """
        for path in self.paths:
            if not _os.path.exists(path):
                _os.makedirs(path)


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

        _LOGGER.debug("Setting pipeline attributes for: '%s'",
                      str(pipeline_name))

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
            # NGS data inputs exit, so we can add attributes like
            # read_type, read_length, paired.
            self.ngs_inputs = self.get_attr_values("ngs_inputs_attr")
            self.set_read_type(permissive=permissive)

        # input_size
        if not self.all_inputs_attr:
            self.all_inputs_attr = self.required_inputs_attr

        # Convert attribute keys into values
        self.required_inputs = self.get_attr_values("required_inputs_attr")
        self.all_inputs = self.get_attr_values("all_inputs_attr")
        self.input_file_size = get_file_size(self.all_inputs)


    def confirm_required_inputs(self, permissive=False):
        # set_pipeline_attributes must be run first.

        _LOGGER.debug("Confirming required inputs")

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
                message = "Sample missing required input attribute '{}'".\
                    format(file_attribute)
                _LOGGER.warn(message)
                if not permissive:
                    raise IOError(message)
                else:
                    return False

        # Second, files
        missing_files = []
        for paths in self.required_inputs:
            _LOGGER.debug("Checking paths")
            # There can be multiple, space-separated values here.
            for path in paths.split(" "):
                _LOGGER.debug("Checking path: '{}'".format(path))
                if not _os.path.exists(path):
                    _LOGGER.debug("Missing: '{}'".format(path))
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

            if getattr(self, feature) is None:
                _LOGGER.warn("Not all input files agree on "
                             "feature '%s' for sample '%s'",
                             feature, self.name)



@copy
class PipelineInterface(object):
    """
    This class parses, holds, and returns information for a yaml file that
    specifies how to interact with each individual pipeline. This
    includes both resources to request for cluster job submission, as well as
    arguments to be passed from the sample annotation metadata to the pipeline
    """

    def __init__(self, config):
        """
        Create PipelineInterface from mapping or filepath.
        
        :param Mapping | str config: path to config file or parsed result
        """
        if isinstance(config, Mapping):
            self.pipe_iface_file = None
            self.pipe_iface_config = config
        else:
            _LOGGER.info("Creating %s from file '%s'",
                              self.__class__.__name__, config)
            self.pipe_iface_file = config
            with open(config, 'r') as f:
                self.pipe_iface_config = yaml.load(f)


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


    def get_pipeline_name(self, pipeline_name):
        """
        Translate a pipeline name (e.g., stripping file extension).
        
        :param pipeline_name: Name of pipeline.
        :type pipeline_name: str
        :return: translated pipeline name, as specified in config or by 
            stripping the pipeline's file extension
        :rtype: str: translated name for pipeline
        """
        config = self._select_pipeline(pipeline_name)
        try:
            return config["name"]
        except KeyError:
            return _os.path.splitext(pipeline_name)[0]


    def choose_resource_package(self, pipeline_name, file_size):
        """
        Given a pipeline name (pipeline_name) and a file size (size), 
        return the resource configuration specified by the config file.

        :param pipeline_name: Name of pipeline.
        :type pipeline_name: str
        :param file_size: Size of input data.
        :type file_size: float
        """
        config = self._select_pipeline(pipeline_name)

        if "resources" not in config:
            msg = "No resources found for '" + pipeline_name + "' in '" + self.pipe_iface_file + "'"
            # Should I just use defaults or force you to define this?
            raise IOError(msg)

        table = config['resources']
        current_pick = "default"

        for option in table:
            if table[option]['file_size'] == "0":
                continue
            if file_size < float(table[option]['file_size']):
                continue
            elif float(table[option]['file_size']) > float(table[current_pick]['file_size']):
                current_pick = option

        return table[current_pick]


    def get_attribute(self, pipeline_name, attribute_key):
        """
        Given a pipeline name and an attribute key, returns the value of that attribute.
        """
        config = self._select_pipeline(pipeline_name)

        if attribute_key in config:
            value = config[attribute_key]
        else:
            value = None

        # Make it a list if the file had a string.
        if type(value) is str:
            value = [value]

        return value


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

        args = config['arguments']

        for key, value in args.iteritems():
            _LOGGER.debug("Script argument: '%s', sample attribute: '%s'",
                          key, value)
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

            _LOGGER.debug("Adding '{}' for '{}'".format(arg, key))
            argstring += " " + str(key) + " " + str(arg)

        # Add optional arguments
        if 'optional_arguments' in config:
            args = config['optional_arguments']
            for key, value in args.iteritems():
                _LOGGER.debug("%s, %s (optional)", key, value)
                if value is None:
                    _LOGGER.debug("Null value for opt arg key '%s'",
                                       str(key))
                    continue
                try:
                    arg = getattr(sample, value)
                except AttributeError as e:
                    _LOGGER.warn(
                        "> Note (missing attribute): '%s' requests "
                        "sample attribute '%s' for "
                        "OPTIONAL argument '%s'",
                        pipeline_name, value, key)
                    continue

                argstring += " " + str(key) + " " + str(arg)

        _LOGGER.debug("Script args: '%s'", argstring)

        return argstring

    def _select_pipeline(self, pipeline_name):
        """
        Check to make sure that pipeline has an entry and if so, return it.

        :param pipeline_name: Name of pipeline.
        :type pipeline_name: str
        """
        if pipeline_name not in self.pipe_iface_config:
            _LOGGER.error(
                "Missing pipeline description: '%s' not found in '%s'",
                pipeline_name, self.pipe_iface_file)
            # Should I just use defaults or force you to define this?
            raise Exception("You need to teach looper about that pipeline")

        return self.pipe_iface_config[pipeline_name]



@copy
class InterfaceManager(object):
    """ Aggregate PipelineInterface and ProtocolMapper objects so that a
     Project can use pipelines distributed across multiple locations. """


    def __init__(self, pipeline_dirs):
        """
        Map protocol name to location to use for its pipeline(s).

        :param collections.Iterable[str] pipeline_dirs: locations containing
            pipelines and configuration information; specifically, a directory
            with a 'pipelines' folder and a 'config' folder, within which
            there is a pipeline interface file and a protocol mappings file
        """
        # Collect interface/mappings pairs by protocol name.
        interfaces_and_protocols = \
                [ProtocolInterfaces(pipedir) for pipedir in pipeline_dirs]
        self.ifproto_by_proto_name = defaultdict(list)
        for ifproto in interfaces_and_protocols:
            for proto_name in ifproto.protomap:
                self.ifproto_by_proto_name[proto_name].append(ifproto)


    def build_pipelines(self, protocol_name, priority=True):
        """
        Build up a sequence of scripts to execute for this protocol.

        :param str protocol_name: name for the protocol for which to build
            pipelines
        :param bool priority: should only the top priority mapping be used?
        :return list[str]: sequence of jobs (script paths) to execute for
            the given protocol
        """

        try:
            ifprotos = self.ifproto_by_proto_name[protocol_name]
        except KeyError:
            _LOGGER.warn("Unknown protocol: '{}'".format(protocol_name))
            return []

        jobs = []
        script_names_used = set()
        for ifproto in ifprotos:
            try:
                this_protocol_pipelines = \
                        ifproto.protomap.mappings[protocol_name]
            except KeyError:
                _LOGGER.debug("Protocol {} not in mappings file '{}'".
                              format(protocol_name, ifproto.protomaps_path))
            else:
                # TODO: update once dependency-encoding logic is in place.
                script_names = this_protocol_pipelines.replace(";", ",")\
                                                      .strip(" ()\n")\
                                                      .split(",")
                script_names = [sn.strip() for sn in script_names]
                already_mapped, new_scripts = \
                        partition(script_names,
                                  partial(_is_member, items=script_names_used))
                script_names_used |= set(script_names)

                if len(script_names) != (len(already_mapped) + len(new_scripts)):
                    _LOGGER.error("{} --> {} + {}".format(
                            script_names, already_mapped, new_scripts))

                    raise RuntimeError(
                            "Partitioned {} script names into allegedly "
                            "disjoint sets of {} and {} elements.".
                            format(len(script_names),
                                   len(already_mapped),
                                   len(new_scripts)))

                _LOGGER.debug("Skipping {} already-mapped script names: {}".
                              format(len(already_mapped),
                                     ", ".join(already_mapped)))
                _LOGGER.debug("{} new scripts for protocol {} from "
                              "pipelines warehouse '{}': {}".
                              format(len(new_scripts), protocol_name,
                                     ifproto.pipedir, ", ".join(new_scripts)))

                script_paths = [_os.path.join(ifproto.pipelines_path, script)
                                for script in script_names]
                jobs.append([(ifproto.interface, path)
                             for path in script_paths])

        if priority and len(jobs) > 1:
            return jobs[0]

        return list(itertools.chain(*jobs))



def _is_member(item, items):
    return item in items



# TODO: rename.
class ProtocolInterfaces:
    """ Pair of PipelineInterface and ProtocolMapper instances
    based on a single pipelines_dir location. Also stores path
    attributes to retain information about the location
    from which the interface and mapper came. """


    def __init__(self, pipedir):
        """
        The location at which to find pipeline interface and protocol
        mapping information defines the instance.

        :param str pipedir: path to location at which to find pipeline,
            pipeline interface, and protocol mapping information,
            nested within subfolders as required
        """

        if _os.path.isdir(pipedir):
            self.pipedir = pipedir
            self.config_path = _os.path.join(pipedir, "config")
            self.interface_path = _os.path.join(self.config_path,
                                                "pipeline_interface.yaml")
            self.protomaps_path = _os.path.join(self.config_path,
                                                "protocol_mappings.yaml")
            self.interface = PipelineInterface(self.interface_path)
            self.protomap = ProtocolMapper(self.protomaps_path)
            self.pipelines_path = _os.path.join(pipedir, "pipelines")
        elif _os.path.isfile(pipedir):
            # Secondary version that passes combined yaml file directly,
            # instead of relying on separate hard-coded config names as above
            self.pipedir = None
            self.interface_file = pipedir

            self.pipelines_path = _os.path.dirname(pipedir)

            with open(self.interface_file, 'r') as interface_file:
                iface = yaml.load(interface_file)
            try:
                if "protocol_mapping" in iface:
                    self.protomap = ProtocolMapper(iface["protocol_mapping"])
                else:
                    raise Exception("pipeline_interface file is missing "
                                    "a 'protocol_mapping' section.")
                if "pipelines" in iface:
                    self.interface = PipelineInterface(iface["pipelines"])
                else:
                    raise Exception("pipeline_interface file is missing "
                                    "a 'pipelines' section.")
            except Exception as e:
                _LOGGER.error(str(iface))
                raise e



@copy
class ProtocolMapper(object):
    """
    Map protocol/library name to pipeline(s). For example, "WGBS" --> wgbs.py.
    """

    def __init__(self, mappings_input):
        """
        Create ProtocolMapper from config file or parsed result.
        
        :param str | Mapping mappings_input: path to mappings file or 
            result of parsing one
        """
        if isinstance(mappings_input, Mapping):
            self.mappings_file = None
            mappings = mappings_input
        else:
            # mapping libraries to pipelines
            # input was a file, parse then populate
            self.mappings_file = mappings_input
            with open(self.mappings_file, 'r') as mapfile:
                mappings = yaml.load(mapfile)
        self.mappings = {k.upper(): v for k, v in mappings.items()}


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

    # TODO: incorporate into the InterfaceManager?
    def parse_parallel_jobs(self, job, dep):
        job = job.replace("(", "").replace(")", "")
        split_jobs = [x.strip() for x in job.split(',')]
        if len(split_jobs) > 1:
            for s in split_jobs:
                self.register_job(s, dep)
        else:
            self.register_job(job, dep)

    # TODO: incorporate into InterfaceManager?
    def register_job(self, job, dep):
        _LOGGER.info("Register Job Name: %s\tDep: %s", str(job), str(dep))


    def __getitem__(self, item):
        return self.mappings[item]

    def __iter__(self):
        return iter(self.mappings)

    def __len__(self):
        return len(self.mappings)

    def __repr__(self):
        return repr(self.__dict__)



class MetadataOperationException(Exception):
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
        super(MetadataOperationException, self).__init__(explanation)



class MissingMetadataException(Exception):
    """ Project needs certain metadata. """
    def __init__(self, missing_section, path_config_file=None):
        reason = "Project configuration lacks required metadata section {}".\
                format(missing_section)
        if path_config_file:
            reason += "; used config file '{}'".format(path_config_file)
        super(MissingMetadataException, self).__init__(reason)
