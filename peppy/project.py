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

from collections import Counter
import logging
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
from divvy import ComputingConfiguration
from .const import *
from .exceptions import PeppyError
from .sample import merge_sample, Sample
from .utils import \
    add_project_sample_constants, copy, fetch_samples, infer_delimiter, is_url, \
    non_null_value, warn_derived_cols, warn_implied_cols


MAX_PROJECT_SAMPLES_REPR = 12
NEW_PIPES_KEY = "pipeline_interfaces"
OLD_PIPES_KEY = "pipelines_dir"
OLD_ANNS_META_KEY = "sample_annotation"
OLD_SUBS_META_KEY = "sample_subannotation"

READ_CSV_KWARGS = {"engine": "python", "dtype": str, "index_col": False,
                   "keep_default_na": False}

GENOMES_KEY = "genomes"
TRANSCRIPTOMES_KEY = "transcriptomes"
IDEALLY_IMPLIED = [GENOMES_KEY, TRANSCRIPTOMES_KEY]


_LOGGER = logging.getLogger(__name__)


class ProjectContext(object):
    """ Wrap a Project to provide protocol-specific Sample selection. """

    def __init__(self, prj, selector_attribute=ASSAY_KEY,
                 selector_include=None, selector_exclude=None):
        """ Project and what to include/exclude defines the context. """
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

    :param str config_file: Project config file (YAML).
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

    DERIVED_ATTRIBUTES_DEFAULT = [DATA_SOURCE_COLNAME]

    def __init__(self, config_file, subproject=None, dry=False,
                 permissive=True, file_checks=False, compute_env_file=None,
                 no_environment_exception=None, no_compute_exception=None,
                 defer_sample_construction=False):

        _LOGGER.debug("Creating %s from file: '%s'",
                      self.__class__.__name__, config_file)
        super(Project, self).__init__()

        self.dcc = ComputingConfiguration(
            config_file=compute_env_file, no_env_error=no_environment_exception,
            no_compute_exception=no_compute_exception)
        self.permissive = permissive
        self.file_checks = file_checks

        self._subproject = None

        # Include the path to the config file.
        self.config_file = os.path.abspath(config_file)

        # Parse config file
        _LOGGER.debug("Parsing %s config file", self.__class__.__name__)
        self.parse_config_file(subproject)

        if self.non_null("data_sources"):
            # Expand paths now, so that it's not done for every sample.
            for src_key, src_val in self.data_sources.items():
                src_val = os.path.expandvars(src_val)
                if not (os.path.isabs(src_val) or is_url(src_val)):
                    src_val = os.path.join(os.path.dirname(self.config_file), src_val)
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

        self["_" + SAMPLE_SUBANNOTATIONS_KEY] = None
        path_anns_file = self[METADATA_KEY].get(NAME_TABLE_ATTR)
        self_table_attr = "_" + NAME_TABLE_ATTR
        self[self_table_attr] = None
        if path_anns_file:
            _LOGGER.debug("Reading sample annotations sheet: '%s'", path_anns_file)
            self[self_table_attr] = self.parse_sample_sheet(path_anns_file)
        else:
            _LOGGER.warning("No sample annotations sheet in config")

        # Basic sample maker will handle name uniqueness check.
        if defer_sample_construction or self._sample_table is None:
            self._samples = None
        else:
            self._set_basic_samples()

    def __repr__(self):
        """ Representation in interpreter. """
        if len(self) == 0:
            return "{}"
        samples_message = "{} (from '{}')". \
            format(self.__class__.__name__, self.config_file)
        try:
            num_samples = len(self._samples)
        except (AttributeError, TypeError):
            pass
        else:
            samples_message += " with {} sample(s)".format(num_samples)
            if num_samples <= MAX_PROJECT_SAMPLES_REPR:
                samples_message += ": {}".format(repr(self._samples))
        meta_text = super(Project, self).__repr__()
        return "{} -- {}".format(samples_message, meta_text)

    def __setitem__(self, key, value):
        """
        Override here to handle deprecated special-meaning keys.

        :param str key: Key to map to given value
        :param object value: Arbitrary value to bind to given key
        """
        if key == "derived_columns":
            warn_derived_cols()
            key = DERIVATIONS_DECLARATION
        elif key == "implied_columns":
            warn_implied_cols()
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
        return self._constants

    @property
    def derived_columns(self):
        """
        Collection of sample attributes for which value of each is derived from elsewhere

        :return list[str]: sample attribute names for which value is derived
        """
        warn_derived_cols()
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
        warn_implied_cols()
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
        """
        try:
            return self.metadata.output_dir
        except AttributeError:
            return os.path.dirname(self.config_file)

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
        dt = getattr(self, NAME_TABLE_ATTR)
        try:
            return iter(dt[SAMPLE_NAME_COLNAME])
        except KeyError:
            cols = list(dt.columns)
            print("Table columns: {}".format(", ".join(cols)))
            if 1 == len(cols):
                print("Does delimiter used in the sample sheet match file extension?")
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
        from copy import copy as cp
        key = NAME_TABLE_ATTR
        attr = "_" + key
        if self.get(attr) is None:
            sheetfile = self[METADATA_KEY].get(key)
            if sheetfile is None:
                return None
            self[attr] = self.parse_sample_sheet(sheetfile)
        return cp(self[attr])

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
        from copy import copy as cp
        key = SAMPLE_SUBANNOTATIONS_KEY
        attr = "_" + key
        if self.get(attr) is None:
            sheetfile = self[METADATA_KEY].get(key)
            if sheetfile is None:
                return None
            self[attr] = pd.read_csv(sheetfile,
                sep=infer_delimiter(sheetfile), **READ_CSV_KWARGS)
        return cp(self[attr])

    @property
    def templates_folder(self):
        """
        Path to folder with default submission templates.

        :return str: path to folder with default submission templates
        """
        return self.dcc.templates_folder

    def infer_name(self):
        """
        Infer project name from config file path.
        
        First assume the name is the folder in which the config file resides,
        unless that folder is named "metadata", in which case the project name
        is the parent of that folder.
        
        :return str: inferred name for project.
        """
        if hasattr(self, "name"):
            return self.name
        config_folder = os.path.dirname(self.config_file)
        project_name = os.path.basename(config_folder)
        if project_name == METADATA_KEY:
            project_name = os.path.basename(os.path.dirname(config_folder))
        return project_name

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

    def deactivate_subproject(self):
        """
        Bring the original project settings back

        This method will bring the original project settings back after the subproject activation.

        :return peppy.Project: Updated Project instance
        """
        if self.subproject is None:
            _LOGGER.warning("No subproject has been activated.")
        self.__init__(self.config_file)
        return self

    def activate_subproject(self, subproject):
        """
        Update settings based on subproject-specific values.

        This method will update Project attributes, adding new values
        associated with the subproject indicated, and in case of collision with
        an existing key/attribute the subproject's value will be favored.

        :param str subproject: A string with a subproject name to be activated
        :return peppy.Project: Updated Project instance
        """
        if subproject is None:
            raise TypeError("The subproject argument can not be NoneType."
                            " To deactivate a subproject use the deactivate_subproject method.")
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

    def get_samples(self, sample_names):
        """
        Returns a list of sample objects given a list of sample names

        :param list sample_names: A list of sample names to retrieve
        :return list[Sample]: A list of Sample objects
        """
        return [s for s in self.samples if s.name in sample_names]

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

    def get_arg_string(self, pipeline_name):
        """
        For this project, given a pipeline, return an argument string
        specified in the project config file.
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
            if not os.path.exists(folder_path):
                _LOGGER.debug("Attempting to create project folder: '%s'",
                              folder_path)
                try:
                    os.makedirs(folder_path)
                except OSError as e:
                    _LOGGER.warning("Could not create project folder: '%s'",
                                 str(e))

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
            subann_table = pd.read_csv(sub_ann,
                sep=infer_delimiter(sub_ann), **READ_CSV_KWARGS)
            self["_" + SAMPLE_SUBANNOTATIONS_KEY] = subann_table
            _LOGGER.debug("Subannotations shape: {}".format(subann_table.shape))
        else:
            _LOGGER.debug("Alleged path to sample subannotations data is "
                          "not a file: '%s'", str(sub_ann))

        # Set samples and handle non-unique names situation.
        self._check_subann_name_overlap()
        self._samples = self._prep_samples()
        self._check_unique_samples()

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
            merge_sample(sample, getattr(self, SAMPLE_SUBANNOTATIONS_KEY),
                         self.data_sources, self.derived_attributes)
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

    def _check_subann_name_overlap(self):
        """
        Check if all subannotations have a matching sample, and warn if not

        :raises warning: if any fo the subannotations sample_names does not have a corresponding Project.sample_name
        """
        subs = getattr(self, SAMPLE_SUBANNOTATIONS_KEY)
        if subs is not None:
            sample_subann_names = subs.sample_name.tolist()
            sample_names_list = list(self.sample_names)
            info = " matching sample name for subannotation '{}'"
            for n in sample_subann_names:
                _LOGGER.warning(("Couldn't find" + info).format(n)) if n not in sample_names_list\
                    else _LOGGER.debug(("Found" + info).format(n))
        else:
            _LOGGER.debug("No sample subannotations found for this Project.")

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

        _LOGGER.debug("{} config data: {}".format(
            self.__class__.__name__, config))

        # Parse yaml into the project's attributes.
        _LOGGER.debug("Adding attributes for {}: {}".format(
            self.__class__.__name__, config.keys()))
        _LOGGER.debug("Config metadata: {}".format(config[METADATA_KEY]))
        self.add_entries(config)
        _LOGGER.debug("{} now has {} keys: {}".format(
            self.__class__.__name__, len(self.keys()), self.keys()))

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

        # In looper 0.4, for simplicity the paths section was eliminated.
        # For backwards compatibility, mirror the paths section into metadata.
        if "paths" in config:
            _LOGGER.warning(
                "Paths section in project config is deprecated. "
                "Please move all paths attributes to metadata section. "
                "This option will be removed in future versions.")
            self.metadata.add_entries(self.paths)
            _LOGGER.debug("Metadata: %s", str(self.metadata))
            delattr(self, "paths")

        self._constants = config.get("constants", dict())

        # Ensure required absolute paths are present and absolute.
        for var in self.required_metadata:
            if var not in self.metadata:
                raise ValueError("Missing required metadata item: '{}'".format(var))
            self[METADATA_KEY][var] = os.path.expandvars(self.metadata.get(var))

        _LOGGER.debug("{} metadata: {}".format(self.__class__.__name__,
                                               self.metadata))

        # Some metadata attributes are considered relative to the output_dir
        # Here we make these absolute, so they won't be incorrectly made
        # relative to the config file.
        # These are optional because there are defaults
        config_vars = {
            # Defaults = {"variable": "default"}, relative to output_dir.
            "results_subdir": "results_pipeline",
            "submission_subdir": "submission"
        }

        for key, value in config_vars.items():
            if key in self.metadata:
                if not os.path.isabs(self.metadata[key]):
                    self.metadata[key] = \
                        os.path.join(self.output_dir, self.metadata[key])
            else:
                self.metadata[key] = os.path.join(self.output_dir, value)

        # Variables which are relative to the config file
        # All variables in these sections should be relative to project config.
        relative_sections = [METADATA_KEY, "pipeline_config"]

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

        if self.dcc.compute is None:
            _LOGGER.log(5, "No compute, no submission template")

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
        _LOGGER.log(5, "Ensuring absolute: '%s'", maybe_relpath)
        if os.path.isabs(maybe_relpath) or is_url(maybe_relpath):
            _LOGGER.log(5, "Already absolute")
            return maybe_relpath
        # Maybe we have env vars that make the path absolute?
        expanded = os.path.expanduser(os.path.expandvars(maybe_relpath))
        _LOGGER.log(5, "Expanded: '%s'", expanded)
        if os.path.isabs(expanded):
            _LOGGER.log(5, "Expanded is absolute")
            return expanded
        _LOGGER.log(5, "Making non-absolute path '%s' be absolute",
                    maybe_relpath)
        
        # Set path to an absolute path, relative to project config.
        config_dirpath = os.path.dirname(self.config_file)
        _LOGGER.log(5, "config_dirpath: %s", config_dirpath)
        abs_path = os.path.join(config_dirpath, maybe_relpath)
        return abs_path

    @staticmethod
    def parse_sample_sheet(sample_file, dtype=str):
        """
        Check if csv file exists and has all required columns.

        :param str sample_file: path to sample annotations file.
        :param type dtype: data type for CSV read.
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
        sep = infer_delimiter(sample_file)
        try:
            df = pd.read_csv(sample_file, sep=sep, **READ_CSV_KWARGS)
        except IOError:
            raise Project.MissingSampleSheetError(sample_file)
        else:
            _LOGGER.info("Setting sample sheet from file '%s'", sample_file)
            missing = {SAMPLE_NAME_COLNAME} - set(df.columns)
            if len(missing) != 0:
                _LOGGER.warning(
                    "Annotation sheet ('{}') is missing column(s):\n{}\n"
                    "It has: {}".format(sample_file, "\n".join(missing),
                                        ", ".join(list(df.columns))))
        return df

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

    @staticmethod
    def _omit_from_repr(k, cls):
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
        return k in exclusions_by_class.get(
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

    def __getattr__(self, item, default=None):
        """ Reference the new attribute and warn about deprecation. """
        if item == OLD_PIPES_KEY:
            _warn_pipes_deprecation()
            item = NEW_PIPES_KEY
        return super(_Metadata, self).__getattr__(item, default=None)

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
