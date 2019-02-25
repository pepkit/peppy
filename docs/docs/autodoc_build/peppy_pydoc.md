
# peppy
Project configuration, particularly for logging.

Project-scope constants may reside here, but more importantly, some setup here
will provide a logging infrastructure for all of the project's modules.
Individual modules and classes may provide separate configuration on a more
local level, but this will at least provide a foundation.



# peppy.project

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



## ProjectContext
```python
ProjectContext(self, prj, selector_attribute='protocol', selector_include=None, selector_exclude=None)
```
Wrap a Project to provide protocol-specific Sample selection.

## Project
```python
Project(self, config_file, subproject=None, dry=False, permissive=True, file_checks=False, compute_env_file=None, no_environment_exception=None, no_compute_exception=None, defer_sample_construction=False)
```

A class to model a Project (collection of samples and metadata).

:param config_file: Project config file (YAML).
:type config_file: str
:param subproject: Subproject to use within configuration file, optional
:type subproject: str
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



### constants

Return key-value pairs of pan-Sample constants for this Project.

:return Mapping: collection of KV pairs, each representing a pairing
    of attribute name and attribute value


### DERIVED_ATTRIBUTES_DEFAULT
list() -> new empty list
list(iterable) -> new list initialized from iterable's items

### derived_columns

Collection of sample attributes for which value of each is derived from elsewhere

:return list[str]: sample attribute names for which value is derived


### implied_columns

Collection of sample attributes for which value of each is implied by other(s)

:return list[str]: sample attribute names for which value is implied by other(s)


### num_samples

Count the number of samples available in this Project.

:return int: number of samples available in this Project.


### output_dir

Directory in which to place results and submissions folders.

By default, assume that the project's configuration file specifies
an output directory, and that this is therefore available within
the project metadata. If that assumption does not hold, though,
consider the folder in which the project configuration file lives
to be the project's output directory.

:return str: path to the project's output directory, either as
    specified in the configuration file or the folder that contains
    the project's configuration file.


### project_folders

Names of folders to nest within a project output directory.

:return Iterable[str]: names of output-nested folders


### protocols

Determine this Project's unique protocol names.

:return Set[str]: collection of this Project's unique protocol names


### required_metadata

Names of metadata fields that must be present for a valid project.

Make a base project as unconstrained as possible by requiring no
specific metadata attributes. It's likely that some common-sense
requirements may arise in domain-specific client applications, in
which case this can be redefined in a subclass.

:return Iterable[str]: names of metadata fields required by a project


### sample_names
Names of samples of which this Project is aware.

### samples

Generic/base Sample instance for each of this Project's samples.

:return Iterable[Sample]: Sample instance for each
    of this Project's samples


### sheet

Annotations/metadata sheet describing this Project's samples.

:return pandas.core.frame.DataFrame: table of samples in this Project


### subproject

Return currently active subproject or None if none was activated

:return: currently active subproject
:rtype: str


### templates_folder

Path to folder with default submission templates.

:return str: path to folder with default submission templates


### copy
```python
Project.copy(self)
```

Copy self to a new object.


### infer_name
```python
Project.infer_name(self)
```

Infer project name from config file path.

First assume the name is the folder in which the config file resides,
unless that folder is named "metadata", in which case the project name
is the parent of that folder.

:return str: inferred name for project.


### get_subsample
```python
Project.get_subsample(self, sample_name, subsample_name)
```

From indicated sample get particular subsample.

:param str sample_name: Name of Sample from which to get subsample
:param str subsample_name: Name of Subsample to get
:return peppy.Subsample: The Subsample of requested name from indicated
    sample matching given name


### get_sample
```python
Project.get_sample(self, sample_name)
```

Get an individual sample object from the project.

Will raise a ValueError if the sample is not found. In the case of multiple
samples with the same name (which is not typically allowed), a warning is
raised and the first sample is returned.

:param str sample_name: The name of a sample to retrieve
:return Sample: The requested Sample object


### activate_subproject
```python
Project.activate_subproject(self, subproject)
```

Update settings based on subproject-specific values.

This method will update Project attributes, adding new values
associated with the subproject indicated, and in case of collision with
an existing key/attribute the subproject's value will be favored.

:param str subproject: A string with a subproject name to be activated
:return peppy.Project: Updated Project instance


### get_samples
```python
Project.get_samples(self, sample_names)
```

Returns a list of sample objects given a list of sample names

:param list sample_names: A list of sample names to retrieve
:return list[Sample]: A list of Sample objects


### build_sheet
```python
Project.build_sheet(self, *protocols)
```

Create table of subset of samples matching one of given protocols.

:return pandas.core.frame.DataFrame: DataFrame with from base version
    of each of this Project's samples, for indicated protocol(s) if
    given, else all of this Project's samples


### finalize_pipelines_directory
```python
Project.finalize_pipelines_directory(self, pipe_path='')
```

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


### get_arg_string
```python
Project.get_arg_string(self, pipeline_name)
```

For this project, given a pipeline, return an argument string
specified in the project config file.


### make_project_dirs
```python
Project.make_project_dirs(self)
```

Creates project directory structure if it doesn't exist.


### parse_config_file
```python
Project.parse_config_file(self, subproject=None)
```

Parse provided yaml config file and check required fields exist.

:param str subproject: Name of subproject to activate, optional
:raises KeyError: if config file lacks required section(s)


### set_project_permissions
```python
Project.set_project_permissions(self)
```
Make the project's public_html folder executable.

### parse_sample_sheet

Check if csv file exists and has all required columns.

:param str sample_file: path to sample annotations file.
:param type dtype: data type for CSV read.
:raises IOError: if given annotations file can't be read.
:raises ValueError: if required column(s) is/are missing.


### MissingMetadataException
```python
Project.MissingMetadataException(self, missing_section, path_config_file=None)
```
Project needs certain metadata.

### MissingSampleSheetError
```python
Project.MissingSampleSheetError(self, sheetfile)
```
Represent case in which sample sheet is specified but nonexistent.

## suggest_implied_attributes
```python
suggest_implied_attributes(prj)
```

If given project contains what could be implied attributes, suggest that.

:param Iterable prj: Intent is a Project, but this could be any iterable
    of strings to check for suitability of declaration as implied attr
:return list[str]: (likely empty) list of warning messages about project
    config keys that could be implied attributes


# peppy.sample
Modeling individual samples to process or otherwise use.

## Subsample
```python
Subsample(self, series, sample=None)
```

Class to model Subsamples.

A Subsample is a component of a sample. They are typically used for samples
that have multiple input files of the same type, and are specified in the
PEP by a subannotation table. Each row in the subannotation (or unit) table
corresponds to a Subsample object.

:param series: Subsample data
:type series: Mapping | pandas.core.series.Series


### copy
```python
Subsample.copy(self)
```

Copy self to a new object.


## Sample
```python
Sample(self, series, prj=None)
```

Class to model Samples based on a pandas Series.

:param series: Sample's data.
:type series: Mapping | pandas.core.series.Series

:Example:

.. code-block:: python

    from models import Project, SampleSheet, Sample
    prj = Project("ngs")
    sheet = SampleSheet("~/projects/example/sheet.csv", prj)
    s1 = Sample(sheet.iloc[0])


### input_file_paths

List the sample's data source / input files

:return list[str]: paths to data sources / input file for this Sample.


### library

Backwards-compatible alias.

:return str: The protocol / NGS library name for this Sample.


### copy
```python
Sample.copy(self)
```

Copy self to a new object.


### as_series
```python
Sample.as_series(self)
```

Returns a `pandas.Series` object with all the sample's attributes.

:return pandas.core.series.Series: pandas Series representation
    of this Sample, with its attributes.


### check_valid
```python
Sample.check_valid(self, required=None)
```

Check provided sample annotation is valid.

:param Iterable[str] required: collection of required sample attribute
    names, optional; if unspecified, only a name is required.
:return (Exception | NoneType, str, str): exception and messages about
    what's missing/empty; null with empty messages if there was nothing
    exceptional or required inputs are absent or not set


### determine_missing_requirements
```python
Sample.determine_missing_requirements(self)
```

Determine which of this Sample's required attributes/files are missing.

:return (type, str): hypothetical exception type along with message
    about what's missing; null and empty if nothing exceptional
    is detected


### generate_filename
```python
Sample.generate_filename(self, delimiter='_')
```

Create a name for file in which to represent this Sample.

This uses knowledge of the instance's subtype, sandwiching a delimiter
between the name of this Sample and the name of the subtype before the
extension. If the instance is a base Sample type, then the filename
is simply the sample name with an extension.

:param str delimiter: what to place between sample name and name of
    subtype; this is only relevant if the instance is of a subclass
:return str: name for file with which to represent this Sample on disk


### generate_name
```python
Sample.generate_name(self)
```

Generate name for the sample by joining some of its attribute strings.


### get_attr_values
```python
Sample.get_attr_values(self, attrlist)
```

Get value corresponding to each given attribute.

:param str attrlist: name of an attribute storing a list of attr names
:return list | NoneType: value (or empty string) corresponding to
    each named attribute; null if this Sample's value for the
    attribute given by the argument to the "attrlist" parameter is
    empty/null, or if this Sample lacks the indicated attribute


### get_sheet_dict
```python
Sample.get_sheet_dict(self)
```

Create a K-V pairs for items originally passed in via the sample sheet.

This is useful for summarizing; it provides a representation of the
sample that excludes things like config files and derived entries.

:return OrderedDict: mapping from name to value for data elements
    originally provided via the sample sheet (i.e., the a map-like
    representation of the instance, excluding derived items)


### infer_attributes
```python
Sample.infer_attributes(self, implications)
```

Infer value for additional field(s) from other field(s).

Add columns/fields to the sample based on values in those already-set
that the sample's project defines as indicative of implications for
additional data elements for the sample.

:param Mapping implications: Project's implied columns data
:return None: this function mutates state and is strictly for effect


### is_dormant
```python
Sample.is_dormant(self)
```

Determine whether this Sample is inactive.

By default, a Sample is regarded as active. That is, if it lacks an
indication about activation status, it's assumed to be active. If,
however, and there's an indication of such status, it must be '1'
in order to be considered switched 'on.'

:return bool: whether this Sample's been designated as dormant


### get_subsample
```python
Sample.get_subsample(self, subsample_name)
```

Retrieve a single subsample by name.

:param str subsample_name: The name of the desired subsample. Should
    match the subsample_name column in the subannotation sheet.
:return peppy.Subsample: Requested Subsample object


### get_subsamples
```python
Sample.get_subsamples(self, subsample_names)
```

Retrieve subsamples assigned to this sample

:param list[str] subsample_names: List of names of subsamples to retrieve
:return list[peppy.Subsample]: List of subsamples


### locate_data_source
```python
Sample.locate_data_source(self, data_sources, column_name='data_source', source_key=None, extra_vars=None)
```

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


### make_sample_dirs
```python
Sample.make_sample_dirs(self)
```

Creates sample directory structure if it doesn't exist.


### set_file_paths
```python
Sample.set_file_paths(self, project=None)
```

Sets the paths of all files for this sample.

:param AttMap project: object with pointers to data paths and
    such, either full Project or AttMap with sufficient data


### set_genome
```python
Sample.set_genome(self, genomes)
```

Set the genome for this Sample.

:param Mapping[str, str] genomes: genome assembly by organism name


### set_transcriptome
```python
Sample.set_transcriptome(self, transcriptomes)
```

Set the transcriptome for this Sample.

:param Mapping[str, str] transcriptomes: transcriptome assembly by
    organism name


### set_pipeline_attributes
```python
Sample.set_pipeline_attributes(self, pipeline_interface, pipeline_name, permissive=True)
```

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


### set_read_type
```python
Sample.set_read_type(self, rlen_sample_size=10, permissive=True)
```

For a sample with attr `ngs_inputs` set, this sets the
read type (single, paired) and read length of an input file.

:param rlen_sample_size: Number of reads to sample to infer read type,
    default 10.
:type rlen_sample_size: int
:param permissive: whether to simply log a warning or error message
    rather than raising an exception if sample file is not found or
    otherwise cannot be read, default True.
:type permissive: bool


### to_yaml
```python
Sample.to_yaml(self, path=None, subs_folder_path=None, delimiter='_')
```

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


### update
```python
Sample.update(self, newdata, **kwargs)
```

Update Sample object with attributes from a dict.


## merge_sample
```python
merge_sample(sample, sample_subann, data_sources=None, derived_attributes=None)
```

Use merge table (subannotation) data to augment/modify Sample.

:param Sample sample: sample to modify via merge table data
:param sample_subann: data with which to alter Sample
:param Mapping data_sources: collection of named paths to data locations,
    optional
:param Iterable[str] derived_attributes: names of attributes for which
    corresponding Sample attribute's value is data-derived, optional
:return Set[str]: names of columns/attributes that were merged


## Paths
```python
Paths(self)
```
A class to hold paths as attributes.

### copy
```python
Paths.copy(self)
```

Copy self to a new object.


# peppy.utils
Helpers without an obvious logical home.

## add_project_sample_constants
```python
add_project_sample_constants(sample, project)
```

Update a Sample with constants declared by a Project.

:param Sample sample: sample instance for which to update constants
    based on Project
:param Project project: Project with which to update Sample; it
    may or may not declare constants. If not, no update occurs.
:return Sample: Updates Sample instance, according to any and all
    constants declared by the Project.


## check_bam
```python
check_bam(bam, o)
```

Check reads in BAM file for read type and lengths.

:param str bam: BAM file path.
:param int o: Number of reads to look at for estimation.


## check_sample_sheet_row_count
```python
check_sample_sheet_row_count(sheet, filepath)
```

Quick-and-dirt proxy for Sample count validation.

Check that that the number of rows in a DataFrame (representing the
Sample annotations sheet) seems correct given the number of lines in
the file from which it was parsed/built.

:param pandas.core.frame.DataFrame sheet: the sample annotations sheet
:param str filepath: the path from which the sheet was built
:return bool: flag indicating whether Sample (row) count seems correct


## standard_stream_redirector
```python
standard_stream_redirector(*args, **kwds)
```

Temporarily redirect stdout and stderr to another stream.

This can be useful for capturing messages for easier inspection, or
for rerouting and essentially ignoring them, with the destination as
something like an opened os.devnull.

:param FileIO[str] stream: temporary proxy for standard streams


## coll_like
```python
coll_like(c)
```

Determine whether an object is collection-like.

:param object c: Object to test as collection
:return bool: Whether the argument is a (non-string) collection


## expandpath
```python
expandpath(path)
```

Expand a filesystem path that may or may not contain user/env vars.

:param str path: path to expand
:return str: expanded version of input path


## get_file_size
```python
get_file_size(filename)
```

Get size of all files in gigabytes (Gb).

:param str | collections.Iterable[str] filename: A space-separated
    string or list of space-separated strings of absolute file paths.
:return float: size of file(s), in gigabytes.


## fetch_samples
```python
fetch_samples(proj, selector_attribute=None, selector_include=None, selector_exclude=None)
```

Collect samples of particular protocol(s).

Protocols can't be both positively selected for and negatively
selected against. That is, it makes no sense and is not allowed to
specify both selector_include and selector_exclude protocols. On the other hand, if
neither is provided, all of the Project's Samples are returned.
If selector_include is specified, Samples without a protocol will be excluded,
but if selector_exclude is specified, protocol-less Samples will be included.

:param Project proj: the Project with Samples to fetch
:param Project str: the sample selector_attribute to select for
:param Iterable[str] | str selector_include: protocol(s) of interest;
    if specified, a Sample must
:param Iterable[str] | str selector_exclude: protocol(s) to include
:return list[Sample]: Collection of this Project's samples with
    protocol that either matches one of those in selector_include, or either
    lacks a protocol or does not match one of those in selector_exclude
:raise TypeError: if both selector_include and selector_exclude protocols are
    specified; TypeError since it's basically providing two arguments
    when only one is accepted, so remain consistent with vanilla Python2


## grab_project_data
```python
grab_project_data(prj)
```

From the given Project, grab Sample-independent data.

There are some aspects of a Project of which it's beneficial for a Sample
to be aware, particularly for post-hoc analysis. Since Sample objects
within a Project are mutually independent, though, each doesn't need to
know about any of the others. A Project manages its, Sample instances,
so for each Sample knowledge of Project data is limited. This method
facilitates adoption of that conceptual model.

:param Project prj: Project from which to grab data
:return Mapping: Sample-independent data sections from given Project


## has_null_value
```python
has_null_value(k, m)
```

Determine whether a mapping has a null value for a given key.

:param Hashable k: Key to test for null value
:param Mapping m: Mapping to test for null value for given key
:return bool: Whether given mapping contains given key with null value


## import_from_source
```python
import_from_source(module_filepath)
```

Import a module from a particular filesystem location.

:param str module_filepath: path to the file that constitutes the module
    to import
:return module: module imported from the given location, named as indicated
:raises ValueError: if path provided does not point to an extant file


## is_null_like
```python
is_null_like(x)
```

Determine whether an object is effectively null.

:param object x: Object for which null likeness is to be determined.
:return bool: Whether given object is effectively "null."


## is_url
```python
is_url(maybe_url)
```

Determine whether a path is a URL.

:param str maybe_url: path to investigate as URL
:return bool: whether path appears to be a URL


## non_null_value
```python
non_null_value(k, m)
```

Determine whether a mapping has a non-null value for a given key.

:param Hashable k: Key to test for non-null value
:param Mapping m: Mapping to test for non-null value for given key
:return bool: Whether given mapping contains given key with non-null value


## parse_ftype
```python
parse_ftype(input_file)
```

Checks determine filetype from extension.

:param str input_file: String to check.
:return str: filetype (extension without dot prefix)
:raises TypeError: if file does not appear of a supported type


## parse_text_data
```python
parse_text_data(lines_or_path, delimiter='\n')
```

Interpret input argument as lines of data. This is intended to support
multiple input argument types to core model constructors.

:param str | collections.Iterable lines_or_path:
:param str delimiter: line separator used when parsing a raw string that's
    not a file
:return collections.Iterable: lines of text data
:raises ValueError: if primary data argument is neither a string nor
    another iterable


## sample_folder
```python
sample_folder(prj, sample)
```

Get the path to this Project's root folder for the given Sample.

:param attmap.AttMap | Project prj: project with which sample is associated
:param Mapping sample: Sample or sample data for which to get root output
    folder path.
:return str: this Project's root folder for the given Sample


## warn_derived_cols
```python
warn_derived_cols()
```
Produce deprecation warning about derived columns.

## warn_implied_cols
```python
warn_implied_cols()
```
Produce deprecation warning about implied columns.

## CommandChecker
```python
CommandChecker(self, path_conf_file, sections_to_check=None, sections_to_skip=None)
```

Validate PATH availability of executables referenced by a config file.

:param path_conf_file: path to configuration file with
    sections detailing executable tools to validate
:type path_conf_file: str
:param sections_to_check: names of
    sections of the given configuration file that are relevant;
    optional, will default to all sections if not given, but some
    may be excluded via another optional parameter
:type sections_to_check: Iterable[str]
:param sections_to_skip: analogous to
    the check names parameter, but for specific sections to skip.
:type sections_to_skip: Iterable[str]



### failed

Determine whether *every* command succeeded for *every* config file
section that was validated during instance construction.

:return bool: conjunction of execution success test result values,
    obtained by testing each executable in every validated section


## is_command_callable
```python
is_command_callable(command, name='')
```

Check if command can be called.

:param str command: actual command to call
:param str name: nickname/alias by which to reference the command, optional
:return bool: whether given command's call succeeded

