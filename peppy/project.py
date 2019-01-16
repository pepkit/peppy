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
    prj.sheet.write(os.path.join(prj.metadata.output_dir, "sample_annotation.csv"))

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

from .attribute_dict import AttributeDict
from .const import \
    COMPUTE_SETTINGS_VARNAME, DATA_SOURCE_COLNAME, \
    DEFAULT_COMPUTE_RESOURCES_NAME, IMPLICATIONS_DECLARATION, \
    SAMPLE_ANNOTATIONS_KEY, SAMPLE_NAME_COLNAME
from .exceptions import PeppyError
from .sample import merge_sample, Sample
from .utils import \
    add_project_sample_constants, alpha_cased, copy, fetch_samples, is_url, \
    non_null_value, warn_derived_cols, warn_implied_cols


MAX_PROJECT_SAMPLES_REPR = 12
GENOMES_KEY = "genomes"
TRANSCRIPTOMES_KEY = "transcriptomes"
IDEALLY_IMPLIED = [GENOMES_KEY, TRANSCRIPTOMES_KEY]

_LOGGER = logging.getLogger(__name__)



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
class Project(AttributeDict):
    """
    A class to model a Project (collection of samples and metadata).

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

    DERIVED_ATTRIBUTES_DEFAULT = [DATA_SOURCE_COLNAME]


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
        compute_env_file = compute_env_file or os.getenv(self.compute_env_var)
        if compute_env_file:
            if os.path.isfile(compute_env_file):
                self.update_environment(compute_env_file)
            else:
                _LOGGER.warning("Compute env path isn't a file: {}".
                             format(compute_env_file))
        else:
            _LOGGER.info("No compute env file was provided and {} is unset; "
                         "using default".format(self.compute_env_var))

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
                _LOGGER.warning(message)
        else:
            _LOGGER.debug("Compute: %s", str(self.compute))

        # Optional behavioral parameters
        self.permissive = permissive
        self.file_checks = file_checks

        # Include the path to the config file.
        self.config_file = os.path.abspath(config_file)

        # Parse config file
        _LOGGER.debug("Parsing %s config file", self.__class__.__name__)
        if subproject:
            _LOGGER.info("Using subproject: '{}'".format(subproject))
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

        # SampleSheet creation populates project's samples, adds the
        # sheet itself, and adds any derived columns.
        _LOGGER.debug("Processing {} pipeline location(s): {}".
                      format(len(self.metadata.pipelines_dir),
                             self.metadata.pipelines_dir))

        path_anns_file = self.metadata.sample_annotation
        if path_anns_file:
            _LOGGER.debug("Reading sample annotations sheet: '%s'", path_anns_file)
            _LOGGER.info("Setting sample sheet from file '%s'", path_anns_file)
            self._sheet = self.parse_sample_sheet(path_anns_file)
        else:
            _LOGGER.warning("No sample annotations sheet in config")
            self._sheet = None

        self.sample_subannotation = None

        # Basic sample maker will handle name uniqueness check.
        if defer_sample_construction or self._sheet is None:
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


    @property
    def compute_env_var(self):
        """
        Environment variable through which to access compute settings.

        :return str: name of the environment variable to pointing to
            compute settings
        """
        return COMPUTE_SETTINGS_VARNAME


    @property
    def constants(self):
        """
        Return key-value pairs of pan-Sample constants for this Project.

        :return Mapping: collection of KV pairs, each representing a pairing
            of attribute name and attribute value
        """
        return self._constants


    @property
    def default_compute_envfile(self):
        """
        Path to default compute environment settings file.

        :return str: Path to this project's default compute env config file.
        """
        return os.path.join(
            self.templates_folder, "default_compute_settings.yaml")


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
            return AttributeDict()


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
        return iter(self.sheet[SAMPLE_NAME_COLNAME])


    @property
    def samples(self):
        """
        Generic/base Sample instance for each of this Project's samples.

        :return Iterable[Sample]: Sample instance for each
            of this Project's samples
        """
        return self._samples


    @property
    def sheet(self):
        """
        Annotations/metadata sheet describing this Project's samples.

        :return pandas.core.frame.DataFrame: table of samples in this Project
        """
        from copy import copy as cp
        if self._sheet is None:
            self._sheet = self.parse_sample_sheet(self.metadata.sample_annotation)
        return cp(self._sheet)


    @property
    def templates_folder(self):
        """
        Path to folder with default submission templates.

        :return str: path to folder with default submission templates
        """
        return os.path.join(os.path.dirname(__file__), "submit_templates")


    def infer_name(self):
        """
        Infer project name from config file path.
        
        First assume the name is the folder in which the config file resides,
        unless that folder is named "metadata", in which case the project name
        is the parent of that folder.
        
        :param str path_config_file: path to the project's config file.
        :return str: inferred name for project.
        """
        if hasattr(self, "name"):
            return(self.name)
        
        config_folder = os.path.dirname(self.config_file)
        project_name = os.path.basename(config_folder)
        
        if project_name == "metadata":
            project_name = os.path.basename(os.path.dirname(config_folder))

        return project_name


    def get_subsample(self, sample_name, subsample_name):

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

        if len(samples) == 0:
            raise ValueError("Project has no sample named {name}.".format(name=sample_name))

        return samples[0]


    def activate_subproject(self, subproject):
        """
        Activate a subproject.

        This method will update Project attributes, adding new values
        associated with the subproject indicated, and in case of collision with
        an existing key/attribute the subproject's value will be favored.

        :param str subproject: A string with a subproject name to be activated
        :return Project: A Project with the selected subproject activated
        """
        conf_file = self.config_file
        self.clear()
        self.__init__(conf_file, subproject)
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
        return pd.DataFrame(include_samples)


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
            sub_ann = self.metadata["sample_subannotation"]
        except KeyError:
            try:
                # Backwards compatibility
                sub_ann = self.metadata["merge_table"]
            except KeyError:
                _LOGGER.debug("No sample subannotations")
            else:
                _LOGGER.warning("'merge_table' attribute is deprecated. Please use "
                    "'sample_subannotation' instead.")

        if self.sample_subannotation is None:
            if sub_ann and os.path.isfile(sub_ann):
                _LOGGER.info("Reading subannotations: %s", sub_ann)
                self.sample_subannotation = pd.read_csv(
                        sub_ann, sep=None, engine="python")
                _LOGGER.debug("Subannotations shape: {}".
                              format(self.sample_subannotation.shape))
            else:
                _LOGGER.debug("Alleged path to sample subannotations data is "
                              "not a file: '%s'", str(sub_ann))
        else:
            _LOGGER.debug("Already parsed sample subannotations")

        # Set samples and handle non-unique names situation.
        self._samples = self._prep_samples()
        self._check_unique_samples()


    def _prep_samples(self):
        """
        Merge this Project's Sample object and set file paths.

        :return list[Sample]: collection of this Project's Sample objects
        """

        samples = []

        for _, row in self.sheet.iterrows():
            sample = Sample(row.dropna(), prj=self)

            # Add values that are constant across this Project's samples.
            sample = add_project_sample_constants(sample, self)

            sample.set_genome(self.get("genomes"))
            sample.set_transcriptome(self.get("transcriptomes"))

            _LOGGER.debug("Merging sample '%s'", sample.name)
            sample.infer_attributes(self.get(IMPLICATIONS_DECLARATION))
            merge_sample(sample, self.sample_subannotation,
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

        for msg in suggest_implied_attributes(config):
            warnings.warn(msg, DeprecationWarning)

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
        if non_null_value("subprojects", config) and subproject:
            _LOGGER.debug("Adding entries for subproject '{}'".
                          format(subproject))
            try:
                subproj_updates = config['subprojects'][subproject]
            except KeyError:
                raise Exception(
                    "Unknown subproject ({}); defined subprojects: {}".format(
                    subproject, ", ".join([sp for sp in config["subprojects"]])))
            _LOGGER.debug("Updating with: {}".format(subproj_updates))
            self.add_entries(subproj_updates)
        elif subproject:
            _LOGGER.warning("Subproject {} requested but no subprojects "
                         "are defined".format(subproject))
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

        # In looper 0.6, we added pipeline_interfaces to metadata
        # For backwards compatibility, merge it with pipelines_dir

        if "metadata" in config:
            if "pipelines_dir" in self.metadata:
                _LOGGER.warning("Looper v0.6 suggests "
                                "switching from pipelines_dir to "
                                "pipeline_interfaces. See docs for details: "
                                "https://pepkit.github.io/docs/home/")
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

        self._constants = config.get("constants", dict())

        # Ensure required absolute paths are present and absolute.
        for var in self.required_metadata:
            if var not in self.metadata:
                raise ValueError("Missing required metadata item: '%s'")
            setattr(self.metadata, var,
                    os.path.expandvars(getattr(self.metadata, var)))

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
            if hasattr(self.metadata, key):
                if not os.path.isabs(getattr(self.metadata, key)):
                    setattr(self.metadata, key,
                            os.path.join(self.output_dir,
                                          getattr(self.metadata, key)))
            else:
                outpath = os.path.join(self.output_dir, value)
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
        elif not os.path.isabs(self.compute.submission_template):
            # Relative to environment config file.
            self.compute.submission_template = os.path.join(
                os.path.dirname(self.environment_file),
                self.compute.submission_template)

        # Required variables check
        if not hasattr(self.metadata, SAMPLE_ANNOTATIONS_KEY):
            self.metadata.sample_annotation = None


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
            if not os.path.isabs(self.compute.submission_template):
                try:
                    self.compute.submission_template = os.path.join(
                        os.path.dirname(self.environment_file),
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
            # both present--but don't evaluate to True--is fairly harmless.
            _LOGGER.debug("Environment = {}".format(self.environment))

        return False


    def set_project_permissions(self):
        """ Make the project's public_html folder executable. """
        try:
            os.chmod(self.trackhubs.trackhub_dir, 0o0755)
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
                            if not os.path.isabs(y[key][key2]):
                                y[key][key2] = os.path.join(
                                    os.path.dirname(env_settings_file),
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


    def _handle_missing_env_attrs(self, env_settings_file, when_missing):
        """ Default environment settings aren't required; warn, though. """
        missing_env_attrs = \
            [attr for attr in ["environment", "environment_file"]
             if not hasattr(self, attr) or getattr(self, attr) is None]
        if not missing_env_attrs:
            return
        message = "'{}' lacks environment attributes: {}". \
            format(env_settings_file, missing_env_attrs)
        if when_missing is None:
            _LOGGER.warning(message)
        else:
            when_missing(message)


    @staticmethod
    def parse_sample_sheet(sample_file, dtype=str):
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
        # See https://github.com/pepkit/peppy/issues/159 for the original issue
        # and https://github.com/pepkit/peppy/pull/160 for the pull request
        # that resolved it.
        try:
            df = pd.read_csv(sample_file, sep=None, dtype=dtype, index_col=False,
                             engine="python", keep_default_na=False)
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
            super(Project.MissingSampleSheetError, self).__init__(
                "Missing sample annotation sheet ({}); a project need not use "
                "a sample sheet, but if it does the file must exist."
                .format(sheetfile))



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
