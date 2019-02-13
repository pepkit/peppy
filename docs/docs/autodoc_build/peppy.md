# Package peppy Documentation

Project configuration, particularly for logging.

Project-scope constants may reside here, but more importantly, some setup here
will provide a logging infrastructure for all of the project's modules.
Individual modules and classes may provide separate configuration on a more
local level, but this will at least provide a foundation.


## Class Project
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
['### \\_\\_init\\_\\_', '```py\n', 'def __init__(self, config_file, subproject=None, default_compute=None, dry=False, permissive=True, file_checks=False, compute_env_file=None, no_environment_exception=None, no_compute_exception=None, defer_sample_construction=False)\n', '```\n', '\n']
['### activate\\_subproject', '```py\n', 'def activate_subproject(self, subproject)\n', '```\n', '\n', "Activate a subproject.\n\nThis method will update Project attributes, adding new values\nassociated with the subproject indicated, and in case of collision with\nan existing key/attribute the subproject's value will be favored.\n\n:param str subproject: A string with a subproject name to be activated\n:return Project: A Project with the selected subproject activated", '\n']
['### add\\_entries', '```py\n', 'def add_entries(self, entries)\n', '```\n', '\n', 'Update this instance with provided key-value pairs.\n\n:param Iterable[(object, object)] | Mapping | pandas.Series entries:\n    collection of pairs of keys and values', '\n']
['### build\\_sheet', '```py\n', 'def build_sheet(self, *protocols)\n', '```\n', '\n', "Create all Sample object for this project for the given protocol(s).\n\n:return pandas.core.frame.DataFrame: DataFrame with from base version\n    of each of this Project's samples, for indicated protocol(s) if\n    given, else all of this Project's samples", '\n']
['### clear', '```py\n', 'def clear(self)\n', '```\n', '\n', 'D.clear() -> None.  Remove all items from D.', '\n']
['### copy', '```py\n', 'def copy(self)\n', '```\n', '\n', 'Copy self to a new object.', '\n']
['### finalize\\_pipelines\\_directory', '```py\n', "def finalize_pipelines_directory(self, pipe_path='')\n", '```\n', '\n', "Finalize the establishment of a path to this project's pipelines.\n\nWith the passed argument, override anything already set.\nOtherwise, prefer path provided in this project's config, then\nlocal pipelines folder, then a location set in project environment.\n\n:param str pipe_path: (absolute) path to pipelines\n:raises PipelinesException: if (prioritized) search in attempt to\n    confirm or set pipelines directory failed\n:raises TypeError: if pipeline(s) path(s) argument is provided and\n    can't be interpreted as a single path or as a flat collection\n    of path(s)", '\n']
['### get', '```py\n', 'def get(self, key, default=None)\n', '```\n', '\n', 'D.get(k[,d]) -> D[k] if k in D, else d.  d defaults to None.', '\n']
['### get\\_arg\\_string', '```py\n', 'def get_arg_string(self, pipeline_name)\n', '```\n', '\n', 'For this project, given a pipeline, return an argument string\nspecified in the project config file.', '\n']
['### get\\_sample', '```py\n', 'def get_sample(self, sample_name)\n', '```\n', '\n', 'Get an individual sample object from the project.\n\nWill raise a ValueError if the sample is not found. In the case of multiple\nsamples with the same name (which is not typically allowed), a warning is\nraised and the first sample is returned.\n\n:param str sample_name: The name of a sample to retrieve\n:return Sample: The requested Sample object', '\n']
['### get\\_samples', '```py\n', 'def get_samples(self, sample_names)\n', '```\n', '\n', 'Returns a list of sample objects given a list of sample names\n\n:param list sample_names: A list of sample names to retrieve\n:return list[Sample]: A list of Sample objects', '\n']
['### get\\_subsample', '```py\n', 'def get_subsample(self, sample_name, subsample_name)\n', '```\n', '\n']
['### infer\\_name', '```py\n', 'def infer_name(self)\n', '```\n', '\n', 'Infer project name from config file path.\n\nFirst assume the name is the folder in which the config file resides,\nunless that folder is named "metadata", in which case the project name\nis the parent of that folder.\n\n:param str path_config_file: path to the project\'s config file.\n:return str: inferred name for project.', '\n']
['### is\\_null', '```py\n', 'def is_null(self, item)\n', '```\n', '\n', 'Conjunction of presence in underlying mapping and value being None\n\n:param object item: Key to check for presence and null value\n:return bool: True iff the item is present and has null value', '\n']
['### items', '```py\n', 'def items(self)\n', '```\n', '\n', "D.items() -> list of D's (key, value) pairs, as 2-tuples", '\n']
['### iteritems', '```py\n', 'def iteritems(self)\n', '```\n', '\n', 'D.iteritems() -> an iterator over the (key, value) items of D', '\n']
['### iterkeys', '```py\n', 'def iterkeys(self)\n', '```\n', '\n', 'D.iterkeys() -> an iterator over the keys of D', '\n']
['### itervalues', '```py\n', 'def itervalues(self)\n', '```\n', '\n', 'D.itervalues() -> an iterator over the values of D', '\n']
['### keys', '```py\n', 'def keys(self)\n', '```\n', '\n', "D.keys() -> list of D's keys", '\n']
['### make\\_project\\_dirs', '```py\n', 'def make_project_dirs(self)\n', '```\n', '\n', "Creates project directory structure if it doesn't exist.", '\n']
['### non\\_null', '```py\n', 'def non_null(self, item)\n', '```\n', '\n', 'Conjunction of presence in underlying mapping and value not being None\n\n:param object item: Key to check for presence and non-null value\n:return bool: True iff the item is present and has non-null value', '\n']
['### parse\\_config\\_file', '```py\n', 'def parse_config_file(self, subproject=None)\n', '```\n', '\n', 'Parse provided yaml config file and check required fields exist.\n\n:param str subproject: Name of subproject to activate, optional\n:raises KeyError: if config file lacks required section(s)', '\n']
['### pop', '```py\n', 'def pop(self, key, default=<object object at 0x7f476beab030>)\n', '```\n', '\n', 'D.pop(k[,d]) -> v, remove specified key and return the corresponding value.\nIf key is not found, d is returned if given, otherwise KeyError is raised.', '\n']
['### popitem', '```py\n', 'def popitem(self)\n', '```\n', '\n', 'D.popitem() -> (k, v), remove and return some (key, value) pair\nas a 2-tuple; but raise KeyError if D is empty.', '\n']
['### set\\_compute', '```py\n', 'def set_compute(self, setting)\n', '```\n', '\n', 'Set the compute attributes according to the\nspecified settings in the environment file.\n\n:param str setting:     name for non-resource compute bundle, the name of\n    a subsection in an environment configuration file\n:return bool: success flag for attempt to establish compute settings', '\n']
['### set\\_project\\_permissions', '```py\n', 'def set_project_permissions(self)\n', '```\n', '\n', "Make the project's public_html folder executable. ", '\n']
['### setdefault', '```py\n', 'def setdefault(self, key, default=None)\n', '```\n', '\n', 'D.setdefault(k[,d]) -> D.get(k,d), also set D[k]=d if k not in D', '\n']
['### update', '```py\n', 'def update(*args, **kwds)\n', '```\n', '\n', 'D.update([E, ]**F) -> None.  Update D from mapping/iterable E and F.\nIf E present and has a .keys() method, does:     for k in E: D[k] = E[k]\nIf E present and lacks .keys() method, does:     for (k, v) in E: D[k] = v\nIn either case, this is followed by: for k, v in F.items(): D[k] = v', '\n']
['### update\\_environment', '```py\n', 'def update_environment(self, env_settings_file)\n', '```\n', '\n', 'Parse data from environment configuration file.\n\n:param str env_settings_file: path to file with\n    new environment configuration data', '\n']
['### values', '```py\n', 'def values(self)\n', '```\n', '\n', "D.values() -> list of D's values", '\n']
['## Class MissingMetadataException', 'Project needs certain metadata. ', ['### \\_\\_init\\_\\_', '```py\n', 'def __init__(self, missing_section, path_config_file=None)\n', '```\n', '\n']]
['## Class MissingSampleSheetError', 'Represent case in which sample sheet is specified but nonexistent. ', ['### \\_\\_init\\_\\_', '```py\n', 'def __init__(self, sheetfile)\n', '```\n', '\n']]
## Class Sample
Class to model Samples based on a pandas Series.

:param series: Sample's data.
:type series: Mapping | pandas.core.series.Series

:Example:

.. code-block:: python

    from models import Project, SampleSheet, Sample
    prj = Project("ngs")
    sheet = SampleSheet("~/projects/example/sheet.csv", prj)
    s1 = Sample(sheet.iloc[0])
['### \\_\\_init\\_\\_', '```py\n', 'def __init__(self, series, prj=None)\n', '```\n', '\n']
['### add\\_entries', '```py\n', 'def add_entries(self, entries)\n', '```\n', '\n', 'Update this instance with provided key-value pairs.\n\n:param Iterable[(object, object)] | Mapping | pandas.Series entries:\n    collection of pairs of keys and values', '\n']
['### as\\_series', '```py\n', 'def as_series(self)\n', '```\n', '\n', "Returns a `pandas.Series` object with all the sample's attributes.\n\n:return pandas.core.series.Series: pandas Series representation\n    of this Sample, with its attributes.", '\n']
['### check\\_valid', '```py\n', 'def check_valid(self, required=None)\n', '```\n', '\n', "Check provided sample annotation is valid.\n\n:param Iterable[str] required: collection of required sample attribute\n    names, optional; if unspecified, only a name is required.\n:return (Exception | NoneType, str, str): exception and messages about\n    what's missing/empty; null with empty messages if there was nothing\n    exceptional or required inputs are absent or not set", '\n']
['### clear', '```py\n', 'def clear(self)\n', '```\n', '\n', 'D.clear() -> None.  Remove all items from D.', '\n']
['### copy', '```py\n', 'def copy(self)\n', '```\n', '\n', 'Copy self to a new object.', '\n']
['### determine\\_missing\\_requirements', '```py\n', 'def determine_missing_requirements(self)\n', '```\n', '\n', "Determine which of this Sample's required attributes/files are missing.\n\n:return (type, str): hypothetical exception type along with message\n    about what's missing; null and empty if nothing exceptional\n    is detected", '\n']
['### generate\\_filename', '```py\n', "def generate_filename(self, delimiter='_')\n", '```\n', '\n', "Create a name for file in which to represent this Sample.\n\nThis uses knowledge of the instance's subtype, sandwiching a delimiter\nbetween the name of this Sample and the name of the subtype before the\nextension. If the instance is a base Sample type, then the filename\nis simply the sample name with an extension.\n\n:param str delimiter: what to place between sample name and name of\n    subtype; this is only relevant if the instance is of a subclass\n:return str: name for file with which to represent this Sample on disk", '\n']
['### generate\\_name', '```py\n', 'def generate_name(self)\n', '```\n', '\n', 'Generate name for the sample by joining some of its attribute strings.', '\n']
['### get', '```py\n', 'def get(self, key, default=None)\n', '```\n', '\n', 'D.get(k[,d]) -> D[k] if k in D, else d.  d defaults to None.', '\n']
['### get\\_attr\\_values', '```py\n', 'def get_attr_values(self, attrlist)\n', '```\n', '\n', 'Get value corresponding to each given attribute.\n\n:param str attrlist: name of an attribute storing a list of attr names\n:return list | NoneType: value (or empty string) corresponding to\n    each named attribute; null if this Sample\'s value for the\n    attribute given by the argument to the "attrlist" parameter is\n    empty/null, or if this Sample lacks the indicated attribute', '\n']
['### get\\_sheet\\_dict', '```py\n', 'def get_sheet_dict(self)\n', '```\n', '\n', 'Create a K-V pairs for items originally passed in via the sample sheet.\n\nThis is useful for summarizing; it provides a representation of the\nsample that excludes things like config files and derived entries.\n\n:return OrderedDict: mapping from name to value for data elements\n    originally provided via the sample sheet (i.e., the a map-like\n    representation of the instance, excluding derived items)', '\n']
['### get\\_subsample', '```py\n', 'def get_subsample(self, subsample_name)\n', '```\n', '\n', 'Retrieve a single subsample by name.\n\n:param str subsample_name: The name of the desired subsample. Should \n    match the subsample_name column in the subannotation sheet.\n:return Subsample: Requested Subsample object', '\n']
['### get\\_subsamples', '```py\n', 'def get_subsamples(self, subsample_names)\n', '```\n', '\n', 'Retrieve subsamples assigned to this sample\n\n:param list subsample_names: List of names of subsamples to retrieve\n:return list: List of subsamples', '\n']
['### infer\\_attributes', '```py\n', 'def infer_attributes(self, implications)\n', '```\n', '\n', "Infer value for additional field(s) from other field(s).\n\nAdd columns/fields to the sample based on values in those already-set\nthat the sample's project defines as indicative of implications for\nadditional data elements for the sample.\n\n:param Mapping implications: Project's implied columns data\n:return None: this function mutates state and is strictly for effect", '\n']
['### is\\_dormant', '```py\n', 'def is_dormant(self)\n', '```\n', '\n', "Determine whether this Sample is inactive.\n\nBy default, a Sample is regarded as active. That is, if it lacks an\nindication about activation status, it's assumed to be active. If,\nhowever, and there's an indication of such status, it must be '1'\nin order to be considered switched 'on.'\n\n:return bool: whether this Sample's been designated as dormant", '\n']
['### is\\_null', '```py\n', 'def is_null(self, item)\n', '```\n', '\n', 'Conjunction of presence in underlying mapping and value being None\n\n:param object item: Key to check for presence and null value\n:return bool: True iff the item is present and has null value', '\n']
['### items', '```py\n', 'def items(self)\n', '```\n', '\n', "D.items() -> list of D's (key, value) pairs, as 2-tuples", '\n']
['### iteritems', '```py\n', 'def iteritems(self)\n', '```\n', '\n', 'D.iteritems() -> an iterator over the (key, value) items of D', '\n']
['### iterkeys', '```py\n', 'def iterkeys(self)\n', '```\n', '\n', 'D.iterkeys() -> an iterator over the keys of D', '\n']
['### itervalues', '```py\n', 'def itervalues(self)\n', '```\n', '\n', 'D.itervalues() -> an iterator over the values of D', '\n']
['### keys', '```py\n', 'def keys(self)\n', '```\n', '\n', "D.keys() -> list of D's keys", '\n']
['### locate\\_data\\_source', '```py\n', "def locate_data_source(self, data_sources, column_name='data_source', source_key=None, extra_vars=None)\n", '```\n', '\n', 'Uses the template path provided in the project config section\n"data_sources" to piece together an actual path by substituting\nvariables (encoded by "{variable}"") with sample attributes.\n\n:param Mapping data_sources: mapping from key name (as a value in\n    a cell of a tabular data structure) to, e.g., filepath\n:param str column_name: Name of sample attribute\n    (equivalently, sample sheet column) specifying a derived column.\n:param str source_key: The key of the data_source,\n    used to index into the project config data_sources section.\n    By default, the source key will be taken as the value of\n    the specified column (as a sample attribute).\n    For cases where the sample doesn\'t have this attribute yet\n    (e.g. in a merge table), you must specify the source key.\n:param dict extra_vars: By default, this will look to\n    populate the template location using attributes found in the\n    current sample; however, you may also provide a dict of extra\n    variables that can also be used for variable replacement.\n    These extra variables are given a higher priority.\n:return str: regex expansion of data source specified in configuration,\n    with variable substitutions made\n:raises ValueError: if argument to data_sources parameter is null/empty', '\n']
['### make\\_sample\\_dirs', '```py\n', 'def make_sample_dirs(self)\n', '```\n', '\n', "Creates sample directory structure if it doesn't exist.", '\n']
['### non\\_null', '```py\n', 'def non_null(self, item)\n', '```\n', '\n', 'Conjunction of presence in underlying mapping and value not being None\n\n:param object item: Key to check for presence and non-null value\n:return bool: True iff the item is present and has non-null value', '\n']
['### pop', '```py\n', 'def pop(self, key, default=<object object at 0x7f476beab030>)\n', '```\n', '\n', 'D.pop(k[,d]) -> v, remove specified key and return the corresponding value.\nIf key is not found, d is returned if given, otherwise KeyError is raised.', '\n']
['### popitem', '```py\n', 'def popitem(self)\n', '```\n', '\n', 'D.popitem() -> (k, v), remove and return some (key, value) pair\nas a 2-tuple; but raise KeyError if D is empty.', '\n']
['### set\\_file\\_paths', '```py\n', 'def set_file_paths(self, project=None)\n', '```\n', '\n', 'Sets the paths of all files for this sample.\n\n:param AttMap project: object with pointers to data paths and\n    such, either full Project or AttMap with sufficient data', '\n']
['### set\\_genome', '```py\n', 'def set_genome(self, genomes)\n', '```\n', '\n', 'Set the genome for this Sample.\n\n:param Mapping[str, str] genomes: genome assembly by organism name', '\n']
['### set\\_pipeline\\_attributes', '```py\n', 'def set_pipeline_attributes(self, pipeline_interface, pipeline_name, permissive=True)\n', '```\n', '\n', 'Set pipeline-specific sample attributes.\n\nSome sample attributes are relative to a particular pipeline run,\nlike which files should be considered inputs, what is the total\ninput file size for the sample, etc. This function sets these\npipeline-specific sample attributes, provided via a PipelineInterface\nobject and the name of a pipeline to select from that interface.\n\n:param PipelineInterface pipeline_interface: A PipelineInterface\n    object that has the settings for this given pipeline.\n:param str pipeline_name: Which pipeline to choose.\n:param bool permissive: whether to simply log a warning or error \n    message rather than raising an exception if sample file is not \n    found or otherwise cannot be read, default True', '\n']
['### set\\_read\\_type', '```py\n', 'def set_read_type(self, rlen_sample_size=10, permissive=True)\n', '```\n', '\n', 'For a sample with attr `ngs_inputs` set, this sets the \nread type (single, paired) and read length of an input file.\n\n:param rlen_sample_size: Number of reads to sample to infer read type,\n    default 10.\n:type rlen_sample_size: int\n:param permissive: whether to simply log a warning or error message \n    rather than raising an exception if sample file is not found or \n    otherwise cannot be read, default True.\n:type permissive: bool', '\n']
['### set\\_transcriptome', '```py\n', 'def set_transcriptome(self, transcriptomes)\n', '```\n', '\n', 'Set the transcriptome for this Sample.\n\n:param Mapping[str, str] transcriptomes: transcriptome assembly by\n    organism name', '\n']
['### setdefault', '```py\n', 'def setdefault(self, key, default=None)\n', '```\n', '\n', 'D.setdefault(k[,d]) -> D.get(k,d), also set D[k]=d if k not in D', '\n']
['### to\\_yaml', '```py\n', "def to_yaml(self, path=None, subs_folder_path=None, delimiter='_')\n", '```\n', '\n', "Serializes itself in YAML format.\n\n:param str path: A file path to write yaml to; provide this or\n    the subs_folder_path\n:param str subs_folder_path: path to folder in which to place file\n    that's being written; provide this or a full filepath\n:param str delimiter: text to place between the sample name and the\n    suffix within the filename; irrelevant if there's no suffix\n:return str: filepath used (same as input if given, otherwise the\n    path value that was inferred)\n:raises ValueError: if neither full filepath nor path to extant\n    parent directory is provided.", '\n']
['### update', '```py\n', 'def update(self, newdata, **kwargs)\n', '```\n', '\n', 'Update Sample object with attributes from a dict.', '\n']
['### values', '```py\n', 'def values(self)\n', '```\n', '\n', "D.values() -> list of D's values", '\n']
## Class PeppyError
Base error type for peppy custom errors. 
['### \\_\\_init\\_\\_', '```py\n', 'def __init__(self, msg)\n', '```\n', '\n']

