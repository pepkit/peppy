"""
Model a project with individual samples and associated data.

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
    prj.sample_table.write(os.path.join(prj.metadata.output_dir, "sample_annotation.csv"))

    # project options are read from the config file
    # but can be changed on the fly:
    prj = Project("test.yaml")
    # change options on the fly
    prj.config["merge_technical"] = False
    # annotation sheet not specified initially in config file
    prj.add_sample_sheet("sample_annotation.csv")

"""

from collections import Counter, namedtuple
import os
import sys
if sys.version_info < (3, 3):
    from collections import Iterable, Mapping
else:
    from collections.abc import Iterable, Mapping
import warnings

import pandas as pd
import yaml

from attmap import PathExAttMap
from divvy import DEFAULT_COMPUTE_RESOURCES_NAME, ComputingConfiguration
from .const import *
from .exceptions import *
from .sample import merge_sample, Sample
from .utils import \
    add_project_sample_constants, copy, fetch_samples, get_logger, \
    get_name_depr_msg, infer_delimiter, non_null_value, type_check_strict
from ubiquerg import is_url


MAX_PROJECT_SAMPLES_REPR = 20
NEW_PIPES_KEY = "pipeline_interfaces"
OLD_PIPES_KEY = "pipelines_dir"
OLD_ANNS_META_KEY = "sample_annotation"
OLD_SUBS_META_KEY = "sample_subannotation"

READ_CSV_KWARGS = {"engine": "python", "dtype": str, "index_col": False,
                   "keep_default_na": False, "na_values": [""]}

GENOMES_KEY = "genomes"
TRANSCRIPTOMES_KEY = "transcriptomes"
IDEALLY_IMPLIED = [GENOMES_KEY, TRANSCRIPTOMES_KEY]

_OLD_CONSTANTS_KEY = "constants"
_OLD_DERIVATIONS_KEY = "derived_columns"
_OLD_IMPLICATIONS_KEY = "implied_columns"

DEPRECATIONS = {_OLD_CONSTANTS_KEY: CONSTANTS_DECLARATION,
                _OLD_DERIVATIONS_KEY: DERIVATIONS_DECLARATION,
                _OLD_IMPLICATIONS_KEY: IMPLICATIONS_DECLARATION}

RESULTS_FOLDER_VALUE = "results_pipeline"
SUBMISSION_FOLDER_VALUE = "submission"

MAIN_INDEX_KEY = "main_index_cols"
SUBS_INDEX_KEY = "subs_index_cols"


_LOGGER = get_logger(__name__)


class ProjectContext(object):
    """ Wrap a Project to provide protocol-specific Sample selection. """

    def __init__(self, prj, selector_attribute=ASSAY_KEY,
                 selector_include=None, selector_exclude=None):
        """ Project and what to include/exclude defines the context. """
        if not isinstance(selector_attribute, str):
            raise TypeError(
                "Name of attribute for sample selection isn't a string: {} "
                "({})".format(selector_attribute, type(selector_attribute)))
        self.prj = prj
        self.include = selector_include
        self.exclude = selector_exclude
        self.attribute = selector_attribute

    def __getattr__(self, item):
        """ Samples are context-specific; other requests are handled
        locally or dispatched to Project. """
        if item == "samples":
            return fetch_samples(
                self.prj, selector_attribute=self.attribute,
                selector_include=self.include, selector_exclude=self.exclude)
        if item in ["prj", "include", "exclude"]:
            # Attributes requests that this context/wrapper handles
            return self.__dict__[item]
        else:
            # Dispatch attribute request to Project.
            return getattr(self.prj, item)

    def __getitem__(self, item):
        """ Provide the Mapping-like item access to the instance's Project. """
        return self.prj[item]

    def __enter__(self):
        """ References pass through this instance as needed, so the context
         provided is the instance itself. """
        return self

    def __exit__(self, *args):
        """ Context teardown. """
        pass


@copy
class Project(PathExAttMap):
    """
    A class to model a Project (collection of samples and metadata).

    :param str | Mapping cfg: Project config file (YAML), or appropriate
        key-value mapping of data to constitute project
    :param str subproject: Subproject to use within configuration file, optional
    :param bool dry: If dry mode is activated, no directories
        will be created upon project instantiation.
    :param bool permissive: Whether a error should be thrown if
        a sample input file(s) do not exist or cannot be open.
    :param bool file_checks: Whether sample input files should be checked
        for their  attributes (read type, read length)
        if this is not set in sample metadata.
    :param str compute_env_file: Environment configuration YAML file specifying
        compute settings.
    :param type no_environment_exception: type of exception to raise if environment
        settings can't be established, optional; if null (the default),
        a warning message will be logged, and no exception will be raised.
    :param type no_compute_exception: type of exception to raise if compute
        settings can't be established, optional; if null (the default),
        a warning message will be logged, and no exception will be raised.
    :param bool defer_sample_construction: whether to wait to build this Project's
        Sample objects until they're needed, optional; by default, the basic
        Sample is created during Project construction

    :Example:

    .. code-block:: python

        from models import Project
        prj = Project("config.yaml")

    """

    # Hook for Project's declaration of how it identifies samples.
    # Used for validation and for merge_sample (derived cols and such)
    SAMPLE_NAME_IDENTIFIER = SAMPLE_NAME_COLNAME

    DERIVED_ATTRIBUTES_DEFAULT = [DATA_SOURCE_COLNAME]

    def __init__(self, cfg, subproject=None, dry=False,
                 permissive=True, file_checks=False, compute_env_file=None,
                 no_environment_exception=None, no_compute_exception=None,
                 defer_sample_construction=False, **kwargs):

        _LOGGER.debug("Creating {}{}".format(
            self.__class__.__name__,
            " from file {}".format(cfg) if cfg else ""))
        super(Project, self).__init__()

        self.dcc = ComputingConfiguration(
            config_file=compute_env_file, no_env_error=no_environment_exception,
            no_compute_exception=no_compute_exception)
        self.permissive = permissive
        self.file_checks = file_checks

        self._subproject = None

        if isinstance(cfg, str):
            self.config_file = os.path.abspath(cfg)
            _LOGGER.debug("Parsing %s config file", self.__class__.__name__)
            sections = self.parse_config_file(subproject)
        else:
            self.config_file = None
            sections = cfg.keys()
        self._sections = set(DEPRECATIONS.get(n, n) for n in sections)

        if self.non_null("data_sources"):
            if self.config_file:
                cfgdir = os.path.dirname(self.config_file)
                getabs = lambda p: os.path.join(cfgdir, p)
            else:
                getabs = lambda p: p
            # Expand paths now, so that it's not done for every sample.
            for src_key, src_val in self.data_sources.items():
                src_val = os.path.expandvars(src_val)
                if not (os.path.isabs(src_val) or is_url(src_val)):
                    src_val = getabs(src_val)
                self.data_sources[src_key] = src_val
        else:
            # Ensure data_sources is at least set if it wasn't parsed.
            self["data_sources"] = None

        self.name = self.infer_name()

        # Set project's directory structure
        if not dry:
            _LOGGER.debug("Ensuring project directories exist")
            self.make_project_dirs()

        # Establish derived columns.
        try:
            # Do not duplicate derived column names.
            self.derived_attributes.extend(
                [colname for colname in self.DERIVED_ATTRIBUTES_DEFAULT
                 if colname not in self.derived_attributes])
        except AttributeError:
            self.derived_attributes = self.DERIVED_ATTRIBUTES_DEFAULT

        self.finalize_pipelines_directory()

        # Set labels by which to index annotation data frames.
        self["_" + MAIN_INDEX_KEY] = \
            kwargs.get(MAIN_INDEX_KEY, SAMPLE_NAME_COLNAME)
        self["_" + SUBS_INDEX_KEY] = \
            kwargs.get(SUBS_INDEX_KEY, (SAMPLE_NAME_COLNAME, "subsample_name"))

        self["_" + SAMPLE_SUBANNOTATIONS_KEY] = None
        path_anns_file = self[METADATA_KEY].get(NAME_TABLE_ATTR)
        self_table_attr = "_" + NAME_TABLE_ATTR
        self[self_table_attr] = None
        if path_anns_file:
            self[self_table_attr] = self.parse_sample_sheet(path_anns_file)
        else:
            _LOGGER.warning("No sample annotations sheet in config")

        # Basic sample maker will handle name uniqueness check.
        if defer_sample_construction or self._sample_table is None:
            self._samples = None
        else:
            self._set_basic_samples()

    def _index_main_table(self, t):
        """ Index column(s) of the subannotation table. """
        return None if t is None else t.set_index(self["_" + MAIN_INDEX_KEY], drop=False)

    def _index_subs_table(self, t):
        """ Index column(s) of the subannotation table. """
        if t is None:
            return
        ideal_labels = self["_" + SUBS_INDEX_KEY]
        ideal_labels = [ideal_labels] if isinstance(ideal_labels, str) else ideal_labels
        labels, missing = [], []
        for l in ideal_labels:
            (labels if l in t.columns else missing).append(l)
        if missing:
            _LOGGER.warning("Missing subtable index labels: {}".
                            format(", ".join(missing)))
        return t.set_index(labels, drop=False)

    def __repr__(self):
        """ Representation in interpreter. """
        if len(self) == 0:
            return "{}"
        msg = "Project ({})".format(self.config_file) \
            if self.config_file else "Project:"
        try:
            num_samples = len(self._samples)
        except (AttributeError, TypeError):
            _LOGGER.debug("No samples established on project")
            num_samples = 0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            msg = "{}\nSections: {}".format(msg, ", ".join(self._sections))
        if num_samples > 0:
            msg = "{}\n{} samples".format(msg, num_samples)
            names = list(self.sample_names)[:MAX_PROJECT_SAMPLES_REPR]
            context = " (showing first {})".format(len(names)) \
                if len(names) < num_samples else ""
            msg = "{}{}: {}".format(msg, context, ", ".join(names))
        subs = self.get(SUBPROJECTS_SECTION)
        return "{}\nSubprojects: {}".\
            format(msg, ", ".join(subs.keys())) if subs else msg

    def __setitem__(self, key, value):
        """
        Override here to handle deprecated special-meaning keys.

        :param str key: Key to map to given value
        :param object value: Arbitrary value to bind to given key
        """
        if key == _OLD_DERIVATIONS_KEY:
            warnings.warn(get_name_depr_msg(
                _OLD_DERIVATIONS_KEY, "derived_attributes", self.__class__),
                DeprecationWarning)
            key = DERIVATIONS_DECLARATION
        elif key == _OLD_IMPLICATIONS_KEY:
            warnings.warn(get_name_depr_msg(
                _OLD_IMPLICATIONS_KEY, "implied_attributes", self.__class__),
                DeprecationWarning)
            key = IMPLICATIONS_DECLARATION
        elif key == METADATA_KEY:
            value = _Metadata(value)
        super(Project, self).__setitem__(key, value)

    @property
    def constants(self):
        """
        Return key-value pairs of pan-Sample constants for this Project.

        :return Mapping: collection of KV pairs, each representing a pairing
            of attribute name and attribute value
        """
        from copy import deepcopy
        warnings.warn(get_name_depr_msg(
            _OLD_CONSTANTS_KEY, CONSTANTS_DECLARATION, self.__class__),
            DeprecationWarning)
        return deepcopy(self[CONSTANTS_DECLARATION])

    @property
    def derived_columns(self):
        """
        Collection of sample attributes for which value of each is derived from elsewhere

        :return list[str]: sample attribute names for which value is derived
        """
        msg = get_name_depr_msg(
            _OLD_DERIVATIONS_KEY, "derived_attributes", self.__class__)
        warnings.warn(msg, DeprecationWarning)
        try:
            return self.derived_attributes
        except AttributeError:
            return []

    @property
    def implied_columns(self):
        """
        Collection of sample attributes for which value of each is implied by other(s)

        :return list[str]: sample attribute names for which value is implied by other(s)
        """
        msg = get_name_depr_msg(
            _OLD_IMPLICATIONS_KEY, "implied_attributes", self.__class__)
        warnings.warn(msg, DeprecationWarning)
        try:
            return self.implied_attributes
        except AttributeError:
            return PathExAttMap()

    @property
    def num_samples(self):
        """
        Count the number of samples available in this Project.

        :return int: number of samples available in this Project.
        """
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
        :raise Exception: if this property is requested on a project that
            was not created from a config file and lacks output folder
            declaration in its metadata section
        """
        try:
            return self.metadata[OUTDIR_KEY]
        except KeyError:
            if not self.config_file:
                raise Exception("Project lacks both a config file and an "
                                "output folder in metadata; using ")
            return os.path.dirname(self.config_file)

    @property
    def project_folders(self):
        """
        Names of folders to nest within a project output directory.

        :return Mapping[str, str]: names of output-nested folders
        """
        return {
            RESULTS_FOLDER_KEY: RESULTS_FOLDER_VALUE,
            SUBMISSION_FOLDER_KEY: SUBMISSION_FOLDER_VALUE
        }
        #return ["results_subdir", "submission_subdir"]

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
                _LOGGER.debug("Sample '%s' lacks protocol", s.name)
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
        dt = getattr(self, NAME_TABLE_ATTR)
        try:
            return iter(self._get_sample_ids(dt))
        except KeyError:
            cols = list(dt.columns)
            _LOGGER.error("(For context) Table columns: {}".
                          format(", ".join(cols)))
            if 1 == len(cols):
                _LOGGER.error("Does delimiter used in the sample sheet match "
                              "file extension?")
            raise

    @property
    def samples(self):
        """
        Generic/base Sample instance for each of this Project's samples.

        :return Iterable[Sample]: Sample instance for each
            of this Project's samples
        """
        if self._samples:
            return self._samples
        if self.sample_table is None:
            _LOGGER.warning("No samples are defined")
            return []
        self._samples = self._prep_samples()
        return self._samples

    @property
    def sample_annotation(self):
        """
        Get the path to the project's sample annotations sheet.

        :return str: path to the project's sample annotations sheet
        """
        warnings.warn("{} is deprecated; please instead use {}".
                      format(OLD_ANNS_META_KEY, NAME_TABLE_ATTR),
                      DeprecationWarning)
        return getattr(self, NAME_TABLE_ATTR)

    @property
    def sample_subannotation(self):
        """
        Return the data table that stores metadata for subsamples/units.

        :return pandas.core.frame.DataFrame | NoneType: table of
            subsamples/units metadata
        """
        warnings.warn("{} is deprecated; use {}".
                      format(OLD_SUBS_META_KEY, SAMPLE_SUBANNOTATIONS_KEY),
                      DeprecationWarning)
        return getattr(self, SAMPLE_SUBANNOTATIONS_KEY)

    @property
    def sample_table(self):
        """
        Return (possibly first parsing/building) the table of samples.

        :return pandas.core.frame.DataFrame | NoneType: table of samples'
            metadata, if one is defined
        """
        return self._index_main_table(sample_table(self))

    @property
    def sheet(self):
        """
        Annotations/metadata sheet describing this Project's samples.

        :return pandas.core.frame.DataFrame: table of samples in this Project
        """
        warnings.warn("sheet is deprecated; instead use {}".
                      format(NAME_TABLE_ATTR), DeprecationWarning)
        return getattr(self, NAME_TABLE_ATTR)

    @property
    def subproject(self):
        """
        Return currently active subproject or None if none was activated

        :return str: name of currently active subproject
        """
        return self._subproject

    @property
    def subsample_table(self):
        """
        Return (possibly first parsing/building) the table of subsamples.

        :return pandas.core.frame.DataFrame | NoneType: table of subsamples'
            metadata, if the project defines such a table
        """
        return self._finalize_subsample_table(subsample_table(self))

    def _finalize_subsample_table(self, t):
        return self._index_subs_table(t)

    @property
    def templates_folder(self):
        """
        Path to folder with default submission templates.

        :return str: path to folder with default submission templates
        """
        return self.dcc.templates_folder

    def activate_subproject(self, subproject):
        """
        Update settings based on subproject-specific values.

        This method will update Project attributes, adding new values
        associated with the subproject indicated, and in case of collision with
        an existing key/attribute the subproject's value will be favored.

        :param str subproject: A string with a subproject name to be activated
        :return peppy.Project: Updated Project instance
        :raise TypeError: if argument to subroject parameter is null
        :raise NotImplementedError: if this call is made on a project not
            created from a config file
        """
        if subproject is None:
            raise TypeError(
                "The subproject argument can not be null. To deactivate a "
                "subproject use the deactivate_subproject method.")
        if not self.config_file:
            raise NotImplementedError(
                "Subproject activation isn't supported on a project not "
                "created from a config file")
        previous = [(k, v) for k, v in self.items() if not k.startswith("_")]
        conf_file = self.config_file
        self.__init__(conf_file, subproject)
        for k, v in previous:
            if k.startswith("_"):
                continue
            if k not in self or (self.is_null(k) and v is not None):
                _LOGGER.debug("Restoring {}: {}".format(k, v))
                self[k] = v
        self._subproject = subproject
        return self

    def build_sheet(self, *protocols):
        """
        Create table of subset of samples matching one of given protocols.

        :return pandas.core.frame.DataFrame: DataFrame with from base version
            of each of this Project's samples, for indicated protocol(s) if
            given, else all of this Project's samples
        """
        # Use all protocols if none are explicitly specified.
        known = set(protocols or self.protocols)
        selector_include = []
        skipped = []
        for s in self.samples:
            try:
                p = s.protocol
            except AttributeError:
                selector_include.append(s)
            else:
                if p in known:
                    selector_include.append(s)
                else:
                    skipped.append(s)
        if skipped:
            msg_data = "\n".join(["{} ({})".format(s, s.protocol)
                                  for s in skipped])
            _LOGGER.debug("Skipped %d sample(s) for protocol. Known: %s\n%s",
                          len(skipped), ", ".join(known), msg_data)
        return pd.DataFrame(selector_include)

    def deactivate_subproject(self):
        """
        Bring the original project settings back

        This method will bring the original project settings back after the subproject activation.

        :return peppy.Project: Updated Project instance
        :raise NotImplementedError: if this call is made on a project not
            created from a config file
        """
        if self.subproject is None:
            _LOGGER.warning("No subproject has been activated.")
        if not self.config_file:
            raise NotImplementedError(
                "Subproject deactivation isn't yet supported on a project that "
                "lacks a config file.")
        self.__init__(self.config_file)
        return self

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
        # Pass pipeline(s) dirpath(s) or use one already set.
        if not pipe_path:
            try:
                pipe_path = self.metadata[NEW_PIPES_KEY]
            except KeyError:
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
        self[METADATA_KEY][NEW_PIPES_KEY] = pipe_path

    def get_arg_string(self, pipeline_name, yield_precedence=None):
        """
        Build argstring from opts/args in project config file for given pipeline.

        :param str pipeline_name: identifier for the relevant pipeline
        :param Iterable[str] yield_precedence: collection of opts/args to
            yield to, i.e. to omit from the argstring (e.g., CLI-specified
            extra arguments that take priority over those in project config)
        """

        def make_optarg_text(opt, arg):
            """ Transform flag/option into CLI-ready text version. """
            if arg:
                try:
                    arg = os.path.expandvars(arg)
                except TypeError:
                    # Rely on direct string formatting of arg.
                    pass
                return "{} {}".format(opt, arg)
            else:
                return opt

        def create_argtext(name):
            """ Create command-line argstring text from config section. """
            try:
                optargs = getattr(self.pipeline_args, name)
            except AttributeError:
                return ""
            # NS using __dict__ will add in the metadata from AttrDict (doh!)
            _LOGGER.debug("optargs.items(): {}".format(optargs.items()))
            optargs_texts = [make_optarg_text(opt, arg)
                             for opt, arg in optargs.items() if opt not in (yield_precedence or set())]
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

    def get_sample(self, sample_name):
        """
        Get an individual sample object from the project.

        Will raise a ValueError if the sample is not found. In the case of multiple
        samples with the same name (which is not typically allowed), a warning is
        raised and the first sample is returned.

        :param str sample_name: The name of a sample to retrieve
        :return Sample: The requested Sample object
        """
        samples = self.get_samples([sample_name])
        if len(samples) > 1:
            _LOGGER.warning("More than one sample was detected; returning the first")
        try:
            return samples[0]
        except IndexError:
            raise ValueError("Project has no sample named {}.".format(sample_name))

    def get_samples(self, sample_names):
        """
        Returns a list of sample objects given a list of sample names

        :param list sample_names: A list of sample names to retrieve
        :return list[Sample]: A list of Sample objects
        """
        return [s for s in self.samples if s.name in sample_names]

    def get_subsample(self, sample_name, subsample_name):
        """
        From indicated sample get particular subsample.

        :param str sample_name: Name of Sample from which to get subsample
        :param str subsample_name: Name of Subsample to get
        :return peppy.Subsample: The Subsample of requested name from indicated
            sample matching given name
        """
        s = self.get_sample(sample_name)
        return s.get_subsample(subsample_name)

    def infer_name(self):
        """
        Infer project name from config file path.

        First assume the name is the folder in which the config file resides,
        unless that folder is named "metadata", in which case the project name
        is the parent of that folder.

        :return str: inferred name for project.
        :raise NotImplementedError: if the project lacks both a name and a
            configuration file (no basis, then, for inference)
        """
        if hasattr(self, "name"):
            return self.name
        if not self.config_file:
            raise NotImplementedError("Project name inference isn't supported "
                                      "on a project that lacks a config file.")
        config_folder = os.path.dirname(self.config_file)
        project_name = os.path.basename(config_folder)
        if project_name == METADATA_KEY:
            project_name = os.path.basename(os.path.dirname(config_folder))
        return project_name

    def make_project_dirs(self):
        """
        Creates project directory structure if it doesn't exist.
        """
        for folder_key, folder_val in self.project_folders.items():
            try:
                folder_path = self.metadata[folder_key]
            except KeyError:
                folder_path = os.path.join(self.output_dir, folder_val)
            _LOGGER.debug("Ensuring project dir exists: '%s'", folder_path)
            if not os.path.exists(folder_path):
                _LOGGER.debug("Attempting to create project folder: '%s'",
                              folder_path)
                try:
                    os.makedirs(folder_path)
                except OSError as e:
                    _LOGGER.warning("Could not create project folder: '%s'",
                                 str(e))

    @property
    def results_folder(self):
        return self._relpath(RESULTS_FOLDER_KEY)

    @property
    def submission_folder(self):
        return self._relpath(SUBMISSION_FOLDER_KEY)

    def _relpath(self, key):
        return os.path.join(
            self.output_dir, self.metadata.get(key, self.project_folders[key]))

    def parse_config_file(self, subproject=None):
        """
        Parse provided yaml config file and check required fields exist.

        :param str subproject: Name of subproject to activate, optional
        :raises KeyError: if config file lacks required section(s)
        """

        _LOGGER.debug("Setting %s data from '%s'",
                      self.__class__.__name__, self.config_file)
        with open(self.config_file, 'r') as conf_file:
            config = yaml.safe_load(conf_file)

        assert isinstance(config, Mapping), \
            "Config file parse did not yield a Mapping; got {} ({})".\
            format(config, type(config))

        for msg in suggest_implied_attributes(config):
            warnings.warn(msg, DeprecationWarning)

        _LOGGER.debug("Raw config data: {}".format(config))

        # Parse yaml into the project's attributes.
        _LOGGER.debug("Adding attributes: {}".format(", ".join(config)))
        try:
            _LOGGER.debug("Config metadata: {}".format(config[METADATA_KEY]))
        except KeyError:
            _LOGGER.warning("No metadata ('{}')".format(METADATA_KEY))
        self.add_entries(config)

        # Overwrite any config entries with entries in the subproject.
        if subproject:
            if non_null_value(SUBPROJECTS_SECTION, config):
                _LOGGER.debug("Adding entries for subproject '{}'".
                              format(subproject))
                try:
                    subproj_updates = config[SUBPROJECTS_SECTION][subproject]
                except KeyError:
                    raise MissingSubprojectError(subproject, config[SUBPROJECTS_SECTION])
                _LOGGER.debug("Updating with: {}".format(subproj_updates))
                self.add_entries(subproj_updates)
                self._subproject = subproject
                _LOGGER.info("Using subproject: '{}'".format(subproject))
            else:
                raise MissingSubprojectError(subproject)
        else:
            _LOGGER.debug("No subproject requested")

        self.setdefault(CONSTANTS_DECLARATION, {})

        # In looper 0.4, for simplicity the paths section was eliminated.
        # For backwards compatibility, mirror the paths section into metadata.
        if "paths" in config:
            _LOGGER.warning(
                "Paths section in project config is deprecated. "
                "Please move all paths attributes to metadata section. "
                "This option will be removed in future versions.")
            self.metadata.add_entries(self.paths)
            _LOGGER.debug("Metadata: %s", str(self.metadata))
            del self["paths"]

        # Ensure required absolute paths are present and absolute.
        for var in self.required_metadata:
            if var not in self.metadata:
                raise ValueError("Missing required metadata item: '{}'".format(var))
            self[METADATA_KEY][var] = os.path.expandvars(self.metadata.get(var))

        _LOGGER.debug("Project metadata: {}".format(self.metadata))

        # Variables which are relative to the config file
        # All variables in these sections should be relative to project config.
        relative_sections = [METADATA_KEY, "pipeline_config"]

        _LOGGER.debug("Parsing relative sections")
        for sect in relative_sections:
            try:
                relative_vars = self[sect]
            except KeyError:
                _LOGGER.whisper("Project lacks relative section '%s', skipping", sect)
                continue
            if not relative_vars:
                _LOGGER.whisper("No relative variables, continuing")
                continue
            for var in relative_vars.keys():
                relpath = relative_vars[var]
                if relpath is None:
                    continue
                _LOGGER.debug("Ensuring absolute path(s) for '%s'", var)
                # Parsed from YAML, so small space of possible datatypes.
                if isinstance(relpath, list):
                    absolute = [self._ensure_absolute(maybe_relpath)
                                for maybe_relpath in relpath]
                elif var in self.project_folders:
                    _LOGGER.whisper("Skipping absolute assurance for key: %s", var)
                    absolute = relpath
                else:
                    absolute = self._ensure_absolute(relpath)
                _LOGGER.debug("Setting '%s' to '%s'", var, absolute)
                relative_vars[var] = absolute

        if self.dcc.compute is None:
            _LOGGER.whisper("No compute, so no submission template")

        old_table_keys = [OLD_ANNS_META_KEY, OLD_SUBS_META_KEY]
        new_table_keys = [SAMPLE_ANNOTATIONS_KEY, SAMPLE_SUBANNOTATIONS_KEY]
        metadata = self[METADATA_KEY]
        for k_old, k_new in zip(old_table_keys, new_table_keys):
            try:
                v = metadata[k_old]
            except KeyError:
                continue
            metadata[k_new] = v
            del metadata[k_old]
        self[METADATA_KEY] = metadata

        if NAME_TABLE_ATTR not in self[METADATA_KEY]:
            self[METADATA_KEY][NAME_TABLE_ATTR] = None

        return set(config.keys())

    def parse_sample_sheet(self, sample_file):
        """
        Check if csv file exists and has all required columns.

        :param str sample_file: path to sample annotations file.
        :return pandas.core.frame.DataFrame: table populated by the project's
            sample annotations data
        :raises IOError: if given annotations file can't be read.
        :raises ValueError: if required column(s) is/are missing.
        """
        # Although no null value replacements or supplements are being passed,
        # toggling the keep_default_na value to False solved an issue with 'nan'
        # and/or 'None' as an argument for an option in the pipeline command
        # that's generated from a Sample's attributes.
        #
        # See https://github.com/pepkit/peppy/issues/159 for the original issue
        # and https://github.com/pepkit/peppy/pull/160 for the pull request
        # that resolved it.
        _LOGGER.info("Reading sample annotations sheet: '%s'", sample_file)
        sep = infer_delimiter(sample_file)
        _LOGGER.debug("Inferred delimiter: {}".format(sep))
        try:
            df = pd.read_csv(sample_file, sep=sep, **READ_CSV_KWARGS)
        except IOError:
            raise Project.MissingSampleSheetError(sample_file)
        else:
            _LOGGER.info("Setting sample sheet from file '%s'", sample_file)
            missing = self._missing_columns(set(df.columns))
            if len(missing) != 0:
                _LOGGER.warning(
                    "Annotation sheet ({f}) is missing {n} column(s): {miss}; "
                    "It has {ncol}: {has}".format(
                        f=sample_file, n=len(missing), miss=", ".join(missing),
                        ncol=len(df.columns), has=", ".join(list(df.columns))))
        return df

    def _missing_columns(self, cs):
        return {self.SAMPLE_NAME_IDENTIFIER} - set(cs)

    def _apply_parse_strat(self, filepath, spec):
        from copy import copy as cp
        kwds = cp(spec.kwargs)
        if spec.make_extra_kwargs:
            kwds.update(spec.make_extra_kwargs(filepath))
        return spec.get_parse_fun(self)(filepath, **kwds)

    def _check_subann_name_overlap(self, subs):
        """
        Check if all subannotations have a matching sample, and warn if not. """
        if subs is not None:
            sample_subann_names = self._get_sample_ids(subs).tolist()
            sample_names_list = list(self.sample_names)
            info = " matching sample name for subannotation '{}'"
            for n in sample_subann_names:
                if n not in sample_names_list:
                    _LOGGER.warning(("Couldn't find" + info).format(n))
                else:
                    _LOGGER.debug(("Found" + info).format(n))
        else:
            _LOGGER.debug("No sample subannotations found for this Project.")

    def _check_unique_samples(self):
        """ Handle scenario in which sample names are not unique. """
        # Defining this here but then calling out to the repeats counter has
        # a couple of advantages. We get an unbound, isolated method (the
        # Project-external repeat sample name counter), but we can still
        # do this check from the sample builder, yet have it be override-able.
        repeats = {name: n for name, n in Counter(
            s.name for s in self._samples).items() if n > 1}
        if repeats:
            hist_text = "\n".join(
                "{}: {}".format(name, n) for name, n in repeats.items())
            _LOGGER.warning("Non-unique sample names:\n{}".format(hist_text))

    @staticmethod
    def _get_sample_ids(df):
        """ Return the sample identifiers in the given table. """
        type_check_strict(df, pd.DataFrame)
        return df[SAMPLE_NAME_COLNAME]

    def _meta_from_file_set_if_needed(self, spec, attr=lambda k: "_" + k):
        """ Build attribute value if needed and return it. """
        from copy import copy as cp
        if not isinstance(spec, _MakeTableSpec):
            raise TypeError("Invalid specification type: {}".format(type(spec)))
        if hasattr(attr, "__call__"):
            attr = attr(spec.key)
        elif not isinstance(attr, str):
            raise TypeError("Attr name must be string or function to call on "
                            "key to make attr name; got {}".format(type(attr)))
        if self.get(attr) is None:
            filepath = self[METADATA_KEY].get(spec.key)
            if filepath is None:
                return None
            self[attr] = self._apply_parse_strat(filepath, spec)
        return cp(self[attr])

    def _prep_samples(self):
        """
        Merge this Project's Sample object and set file paths.

        :return list[Sample]: collection of this Project's Sample objects
        """

        samples = []

        for _, row in getattr(self, NAME_TABLE_ATTR).iterrows():
            sample = Sample(row.dropna(), prj=self)

            # Add values that are constant across this Project's samples.
            sample = add_project_sample_constants(sample, self)

            sample.set_genome(self.get("genomes"))
            sample.set_transcriptome(self.get("transcriptomes"))

            _LOGGER.debug("Merging sample '%s'", sample.name)
            sample.infer_attributes(self.get(IMPLICATIONS_DECLARATION))
            merge_sample(sample, self["_" + SAMPLE_SUBANNOTATIONS_KEY],
                         self.data_sources, self.derived_attributes,
                         sample_colname=self.SAMPLE_NAME_IDENTIFIER)
            _LOGGER.debug("Setting sample file paths")
            sample.set_file_paths(self)
            # Hack for backwards-compatibility
            # Pipelines should now use `data_source`)
            _LOGGER.debug("Setting sample data path")
            try:
                sample.data_path = sample.data_source
            except AttributeError:
                _LOGGER.whisper("Sample '%s' lacks data source; skipping data "
                                "path assignment", sample.name)
            else:
                _LOGGER.whisper("Path to sample data: '%s'", sample.data_source)
            samples.append(sample)

        return samples

    def _set_basic_samples(self):
        """ Build the base Sample objects from the annotations sheet data. """

        # This should be executed just once, establishing the Project's
        # base Sample objects if they don't already exist.
        sub_ann = None
        try:
            sub_ann = self.metadata[SAMPLE_SUBANNOTATIONS_KEY]
        except KeyError:
            try:
                # Backwards compatibility
                sub_ann = self.metadata["merge_table"]
            except KeyError:
                _LOGGER.debug("No sample subannotations")
            else:
                warnings.warn("merge_table is deprecated; please instead use {}".
                              format(SAMPLE_SUBANNOTATIONS_KEY), DeprecationWarning)

        if sub_ann and os.path.isfile(sub_ann):
            _LOGGER.info("Reading subannotations: %s", sub_ann)
            subann_table = self._apply_parse_strat(sub_ann, _SUBS_TABLE_SPEC)
            self["_" + SAMPLE_SUBANNOTATIONS_KEY] = subann_table
            _LOGGER.debug("Subannotations shape: {}".format(subann_table.shape))
            self._check_subann_name_overlap(subann_table)
        else:
            _LOGGER.debug("Alleged path to sample subannotations data is "
                          "not a file: '%s'", str(sub_ann))

        # Set samples and handle non-unique names situation.
        self._samples = self._prep_samples()
        self._check_unique_samples()

    def set_project_permissions(self):
        """ Make the project's public_html folder executable. """
        try:
            os.chmod(self.trackhubs.trackhub_dir, 0o0755)
        except OSError:
            # This currently does not fail now
            # ("cannot change folder's mode: %s" % d)
            pass

    def _ensure_absolute(self, maybe_relpath):
        """ Ensure that a possibly relative path is absolute. """

        if not isinstance(maybe_relpath, str):
            raise TypeError(
                "Attempting to ensure non-text value is absolute path: {} ({})".
                format(maybe_relpath, type(maybe_relpath)))
        _LOGGER.whisper("Ensuring absolute: '%s'", maybe_relpath)
        if os.path.isabs(maybe_relpath) or is_url(maybe_relpath):
            _LOGGER.whisper("Already absolute")
            return maybe_relpath
        # Maybe we have env vars that make the path absolute?
        expanded = os.path.expanduser(os.path.expandvars(maybe_relpath))
        _LOGGER.whisper("Expanded: '%s'", expanded)
        if os.path.isabs(expanded):
            _LOGGER.whisper("Expanded is absolute")
            return expanded
        _LOGGER.whisper("Making non-absolute path '%s' be absolute", maybe_relpath)
        
        # Set path to an absolute path, relative to project config.
        config_dirpath = os.path.dirname(self.config_file)
        _LOGGER.whisper("config_dirpath: %s", config_dirpath)
        abs_path = os.path.join(config_dirpath, maybe_relpath)
        return abs_path

    class MissingMetadataException(PeppyError):
        """ Project needs certain metadata. """
        def __init__(self, missing_section, path_config_file=None):
            reason = "Project configuration lacks required metadata section {}".\
                    format(missing_section)
            if path_config_file:
                reason += "; used config file '{}'".format(path_config_file)
            super(Project.MissingMetadataException, self).__init__(reason)

    class MissingSampleSheetError(PeppyError):
        """ Represent case in which sample sheet is specified but nonexistent. """
        def __init__(self, sheetfile):
            parent_folder = os.path.dirname(sheetfile)
            contents = os.listdir(parent_folder) \
                if os.path.isdir(parent_folder) else []
            msg = "Missing sample annotation sheet ({}); a project need not use " \
                  "a sample sheet, but if it does the file must exist.".\
                format(sheetfile)
            if contents:
                msg += " Contents of parent folder: {}".format(", ".join(contents))
            super(Project.MissingSampleSheetError, self).__init__(msg)

    def _excl_from_repr(self, k, cls):
        """
        Hook for exclusion of particular value from a representation

        :param hashable k: key to consider for omission
        :param type cls: data type on which to base the exclusion
        :return bool: whether the given key k should be omitted from
            text representation
        """
        exclusions_by_class = {
            "Project": [
                "samples", "_samples", "interfaces_by_protocol",
                "_" + SAMPLE_SUBANNOTATIONS_KEY, SAMPLE_SUBANNOTATIONS_KEY,
                NAME_TABLE_ATTR, "_" + NAME_TABLE_ATTR],
            "Subsample": [NAME_TABLE_ATTR, "sample", "merged_cols"],
            "Sample": [NAME_TABLE_ATTR, "prj", "merged_cols"]
        }
        return super(Project, self)._excl_from_repr(k, cls) or \
            k in exclusions_by_class.get(
                cls.__name__ if isinstance(cls, type) else cls, [])


def suggest_implied_attributes(prj):
    """
    If given project contains what could be implied attributes, suggest that.

    :param Iterable prj: Intent is a Project, but this could be any iterable
        of strings to check for suitability of declaration as implied attr
    :return list[str]: (likely empty) list of warning messages about project
        config keys that could be implied attributes
    """
    def suggest(key):
        return "To declare {}, consider using {}".format(
            key, IMPLICATIONS_DECLARATION)
    return [suggest(k) for k in prj if k in IDEALLY_IMPLIED]


class MissingSubprojectError(PeppyError):
    """ Error when project config lacks a requested subproject. """

    def __init__(self, sp, defined=None):
        """
        Create exception with missing subproj request.

        :param str sp: the requested (and missing) subproject
        :param Iterable[str] defined: collection of names of defined subprojects
        """
        msg = "Subproject '{}' not found".format(sp)
        if isinstance(defined, Iterable):
            ctx = "defined subproject(s): {}".format(", ".join(map(str, defined)))
            msg = "{}; {}".format(msg, ctx)
        super(MissingSubprojectError, self).__init__(msg)


class _Metadata(PathExAttMap):
    """ Project section with important information """

    def __getattr__(self, item, default=None, expand=True):
        """ Reference the new attribute and warn about deprecation. """
        if item == OLD_PIPES_KEY:
            _warn_pipes_deprecation()
            item = NEW_PIPES_KEY
        return super(_Metadata, self).__getattr__(item, default, expand)

    def __setitem__(self, key, value):
        """ Store the new key and warn about deprecation. """
        if key == OLD_PIPES_KEY:
            _warn_pipes_deprecation()
            key = NEW_PIPES_KEY
        return super(_Metadata, self).__setitem__(key, value)


def _warn_pipes_deprecation():
    """ Handle messaging regarding pipelines pointer deprecation. """
    msg = "Use of {} is deprecated; favor {}".\
        format(OLD_PIPES_KEY, NEW_PIPES_KEY)
    warnings.warn(msg, DeprecationWarning)


def sample_table(p):
    """
    Provide (building as needed) a Project's main samples (metadata) table.

    :param peppy.Project p: Project instance from which to get table
    :return pandas.core.frame.DataFrame: the Project's sample table
    """
    if not isinstance(p, Project):
        raise TypeError("Not a {}: {} ({})".format(Project.__name__, p, type(p)))
    return p._meta_from_file_set_if_needed(_MAIN_TABLE_SPEC)


def subsample_table(p):
    """
    Provide (building as needed) a Project's subsample (metadata) table.

    :param peppy.Project p: Project instance from which to get subsample table
    :return pandas.core.frame.DataFrame: the Project's subsample table
    """
    if not isinstance(p, Project):
        raise TypeError("Not a {}: {} ({})".format(Project.__name__, p, type(p)))
    return p._meta_from_file_set_if_needed(_SUBS_TABLE_SPEC)


_MakeTableSpec = namedtuple(
    "_MakeTableSpec", ["key", "get_parse_fun", "make_extra_kwargs", "kwargs"])
_MAIN_TABLE_SPEC = _MakeTableSpec(
    NAME_TABLE_ATTR, lambda p: p.parse_sample_sheet, None, {})
_SUBS_TABLE_SPEC = _MakeTableSpec(
    SAMPLE_SUBANNOTATIONS_KEY, lambda _: pd.read_csv,
    lambda f: {"sep": infer_delimiter(f)}, READ_CSV_KWARGS)
