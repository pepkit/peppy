# Package peppy Documentation

## Class Project
A class to model a Project (collection of samples and metadata).

**Parameters:**

- `config_file` -- `str`:  Project config file (YAML).
- `subproject` -- `str`:  Subproject to use within configuration file, optional
- `dry` -- `bool`:  If dry mode is activated, no directorieswill be created upon project instantiation.
- `permissive` -- `bool`:  Whether a error should be thrown ifa sample input file(s) do not exist or cannot be open.
- `file_checks` -- `bool`:  Whether sample input files should be checkedfor their  attributes (read type, read length) if this is not set in sample metadata.
- `compute_env_file` -- `str`:  Environment configuration YAML file specifyingcompute settings.
- `no_environment_exception` -- `type`:  type of exception to raise if environmentsettings can't be established, optional; if null (the default), a warning message will be logged, and no exception will be raised.
- `no_compute_exception` -- `type`:  type of exception to raise if computesettings can't be established, optional; if null (the default), a warning message will be logged, and no exception will be raised.
- `defer_sample_construction` -- `bool`:  whether to wait to build this Project'sSample objects until they're needed, optional; by default, the basic Sample is created during Project construction


**Example(s):**

```python
    from models import Project
    prj = Project("config.yaml")
```


### activate\_subproject
Update settings based on subproject-specific values.

This method will update Project attributes, adding new values
associated with the subproject indicated, and in case of collision with
an existing key/attribute the subproject's value will be favored.
```python
def activate_subproject(self, subproject)
```

**Parameters:**

- `subproject` -- `str`:  A string with a subproject name to be activated


**Returns:**

`peppy.Project`:  Updated Project instance




### build\_sheet
Create table of subset of samples matching one of given protocols.
```python
def build_sheet(self, *protocols)
```

**Returns:**

`pandas.core.frame.DataFrame`:  DataFrame with from base versionof each of this Project's samples, for indicated protocol(s) if given, else all of this Project's samples




### constants
Return key-value pairs of pan-Sample constants for this Project.
```python
def constants(self)
```

**Returns:**

`Mapping`:  collection of KV pairs, each representing a pairingof attribute name and attribute value




### copy
Copy self to a new object.
```python
def copy(self)
```




### deactivate\_subproject
Bring the original project settings back

This method will bring the original project settings back after the subproject activation.
```python
def deactivate_subproject(self)
```

**Returns:**

`peppy.Project`:  Updated Project instance




### derived\_columns
Collection of sample attributes for which value of each is derived from elsewhere
```python
def derived_columns(self)
```

**Returns:**

`list[str]`:  sample attribute names for which value is derived




### finalize\_pipelines\_directory
Finalize the establishment of a path to this project's pipelines.

With the passed argument, override anything already set.
Otherwise, prefer path provided in this project's config, then
local pipelines folder, then a location set in project environment.
```python
def finalize_pipelines_directory(self, pipe_path='')
```

**Parameters:**

- `pipe_path` -- `str`:  (absolute) path to pipelines


**Raises:**

- `PipelinesException`:  if (prioritized) search in attempt toconfirm or set pipelines directory failed
- `TypeError`:  if pipeline(s) path(s) argument is provided andcan't be interpreted as a single path or as a flat collection of path(s)




### get\_arg\_string
For this project, given a pipeline, return an argument string specified in the project config file.
```python
def get_arg_string(self, pipeline_name)
```




### get\_sample
Get an individual sample object from the project.

Will raise a ValueError if the sample is not found. In the case of multiple
samples with the same name (which is not typically allowed), a warning is
raised and the first sample is returned.
```python
def get_sample(self, sample_name)
```

**Parameters:**

- `sample_name` -- `str`:  The name of a sample to retrieve


**Returns:**

`Sample`:  The requested Sample object




### get\_samples
Returns a list of sample objects given a list of sample names
```python
def get_samples(self, sample_names)
```

**Parameters:**

- `sample_names` -- `list`:  A list of sample names to retrieve


**Returns:**

`list[Sample]`:  A list of Sample objects




### get\_subsample
From indicated sample get particular subsample.
```python
def get_subsample(self, sample_name, subsample_name)
```

**Parameters:**

- `sample_name` -- `str`:  Name of Sample from which to get subsample
- `subsample_name` -- `str`:  Name of Subsample to get


**Returns:**

`peppy.Subsample`:  The Subsample of requested name from indicatedsample matching given name




### implied\_columns
Collection of sample attributes for which value of each is implied by other(s)
```python
def implied_columns(self)
```

**Returns:**

`list[str]`:  sample attribute names for which value is implied by other(s)




### infer\_name
Infer project name from config file path.

First assume the name is the folder in which the config file resides,
unless that folder is named "metadata", in which case the project name
is the parent of that folder.
```python
def infer_name(self)
```

**Returns:**

`str`:  inferred name for project.




### make\_project\_dirs
Creates project directory structure if it doesn't exist.
```python
def make_project_dirs(self)
```




### num\_samples
Count the number of samples available in this Project.
```python
def num_samples(self)
```

**Returns:**

`int`:  number of samples available in this Project.




### output\_dir
Directory in which to place results and submissions folders.

By default, assume that the project's configuration file specifies
an output directory, and that this is therefore available within
the project metadata. If that assumption does not hold, though,
consider the folder in which the project configuration file lives
to be the project's output directory.
```python
def output_dir(self)
```

**Returns:**

`str`:  path to the project's output directory, either asspecified in the configuration file or the folder that contains the project's configuration file.




### parse\_config\_file
Parse provided yaml config file and check required fields exist.
```python
def parse_config_file(self, subproject=None)
```

**Parameters:**

- `subproject` -- `str`:  Name of subproject to activate, optional


**Raises:**

- `KeyError`:  if config file lacks required section(s)




### parse\_sample\_sheet
Check if csv file exists and has all required columns.
```python
def parse_sample_sheet(sample_file, dtype=<class 'str'>)
```

**Parameters:**

- `sample_file` -- `str`:  path to sample annotations file.
- `dtype` -- `type`:  data type for CSV read.


**Returns:**

`pandas.core.frame.DataFrame`:  table populated by the project'ssample annotations data


**Raises:**

- `IOError`:  if given annotations file can't be read.
- `ValueError`:  if required column(s) is/are missing.




### project\_folders
Names of folders to nest within a project output directory.
```python
def project_folders(self)
```

**Returns:**

`Iterable[str]`:  names of output-nested folders




### protocols
Determine this Project's unique protocol names.
```python
def protocols(self)
```

**Returns:**

`Set[str]`:  collection of this Project's unique protocol names




### required\_metadata
Names of metadata fields that must be present for a valid project.

Make a base project as unconstrained as possible by requiring no
specific metadata attributes. It's likely that some common-sense
requirements may arise in domain-specific client applications, in
which case this can be redefined in a subclass.
```python
def required_metadata(self)
```

**Returns:**

`Iterable[str]`:  names of metadata fields required by a project




### sample\_annotation
Get the path to the project's sample annotations sheet.
```python
def sample_annotation(self)
```

**Returns:**

`str`:  path to the project's sample annotations sheet




### sample\_names
Names of samples of which this Project is aware.
```python
def sample_names(self)
```




### sample\_subannotation
Return the data table that stores metadata for subsamples/units.
```python
def sample_subannotation(self)
```

**Returns:**

`pandas.core.frame.DataFrame | NoneType`:  table ofsubsamples/units metadata




### sample\_table
Return (possibly first parsing/building) the table of samples.
```python
def sample_table(self)
```

**Returns:**

`pandas.core.frame.DataFrame | NoneType`:  table of samples'metadata, if one is defined




### samples
Generic/base Sample instance for each of this Project's samples.
```python
def samples(self)
```

**Returns:**

`Iterable[Sample]`:  Sample instance for eachof this Project's samples




### set\_project\_permissions
Make the project's public_html folder executable.
```python
def set_project_permissions(self)
```




### sheet
Annotations/metadata sheet describing this Project's samples.
```python
def sheet(self)
```

**Returns:**

`pandas.core.frame.DataFrame`:  table of samples in this Project




### subproject
Return currently active subproject or None if none was activated
```python
def subproject(self)
```

**Returns:**

`str`:  name of currently active subproject




### subsample\_table
Return (possibly first parsing/building) the table of subsamples.
```python
def subsample_table(self)
```

**Returns:**

`pandas.core.frame.DataFrame | NoneType`:  table of subsamples'metadata, if the project defines such a table




### templates\_folder
Path to folder with default submission templates.
```python
def templates_folder(self)
```

**Returns:**

`str`:  path to folder with default submission templates




### Class MissingMetadataException
Project needs certain metadata.


### Class MissingSampleSheetError
Represent case in which sample sheet is specified but nonexistent.


## Class Sample
Class to model Samples based on a pandas Series.

**Parameters:**

- `series` -- `Mapping | pandas.core.series.Series`:  Sample's data.


**Example(s):**

```python
    from models import Project, SampleSheet, Sample
    prj = Project("ngs")
    sheet = SampleSheet("~/projects/example/sheet.csv", prj)
    s1 = Sample(sheet.iloc[0])
```


### as\_series
Returns a `pandas.Series` object with all the sample's attributes.
```python
def as_series(self)
```

**Returns:**

`pandas.core.series.Series`:  pandas Series representationof this Sample, with its attributes.




### check\_valid
Check provided sample annotation is valid.
```python
def check_valid(self, required=None)
```

**Parameters:**

- `required` -- `Iterable[str]`:  collection of required sample attributenames, optional; if unspecified, only a name is required.


**Returns:**

`(Exception | NoneType, str, str)`:  exception and messages aboutwhat's missing/empty; null with empty messages if there was nothing exceptional or required inputs are absent or not set




### copy
Copy self to a new object.
```python
def copy(self)
```




### determine\_missing\_requirements
Determine which of this Sample's required attributes/files are missing.
```python
def determine_missing_requirements(self)
```

**Returns:**

`(type, str)`:  hypothetical exception type along with messageabout what's missing; null and empty if nothing exceptional is detected




### generate\_filename
Create a name for file in which to represent this Sample.

This uses knowledge of the instance's subtype, sandwiching a delimiter
between the name of this Sample and the name of the subtype before the
extension. If the instance is a base Sample type, then the filename
is simply the sample name with an extension.
```python
def generate_filename(self, delimiter='_')
```

**Parameters:**

- `delimiter` -- `str`:  what to place between sample name and name ofsubtype; this is only relevant if the instance is of a subclass


**Returns:**

`str`:  name for file with which to represent this Sample on disk




### generate\_name
Generate name for the sample by joining some of its attribute strings.
```python
def generate_name(self)
```




### get\_attr\_values
Get value corresponding to each given attribute.
```python
def get_attr_values(self, attrlist)
```

**Parameters:**

- `attrlist` -- `str`:  name of an attribute storing a list of attr names


**Returns:**

`list | NoneType`:  value (or empty string) corresponding toeach named attribute; null if this Sample's value for the attribute given by the argument to the "attrlist" parameter is empty/null, or if this Sample lacks the indicated attribute




### get\_sheet\_dict
Create a K-V pairs for items originally passed in via the sample sheet.

This is useful for summarizing; it provides a representation of the
sample that excludes things like config files and derived entries.
```python
def get_sheet_dict(self)
```

**Returns:**

`OrderedDict`:  mapping from name to value for data elementsoriginally provided via the sample sheet (i.e., the a map-like representation of the instance, excluding derived items)




### get\_subsample
Retrieve a single subsample by name.
```python
def get_subsample(self, subsample_name)
```

**Parameters:**

- `subsample_name` -- `str`:  The name of the desired subsample. Shouldmatch the subsample_name column in the subannotation sheet.


**Returns:**

`peppy.Subsample`:  Requested Subsample object




### get\_subsamples
Retrieve subsamples assigned to this sample
```python
def get_subsamples(self, subsample_names)
```

**Parameters:**

- `subsample_names` -- `list[str]`:  List of names of subsamples to retrieve


**Returns:**

`list[peppy.Subsample]`:  List of subsamples




### infer\_attributes
Infer value for additional field(s) from other field(s).

Add columns/fields to the sample based on values in those already-set
that the sample's project defines as indicative of implications for
additional data elements for the sample.
```python
def infer_attributes(self, implications)
```

**Parameters:**

- `implications` -- `Mapping`:  Project's implied columns data


**Returns:**

`None`:  this function mutates state and is strictly for effect




### input\_file\_paths
List the sample's data source / input files
```python
def input_file_paths(self)
```

**Returns:**

`list[str]`:  paths to data sources / input file for this Sample.




### is\_dormant
Determine whether this Sample is inactive.

By default, a Sample is regarded as active. That is, if it lacks an
indication about activation status, it's assumed to be active. If,
however, and there's an indication of such status, it must be '1'
in order to be considered switched 'on.'
```python
def is_dormant(self)
```

**Returns:**

`bool`:  whether this Sample's been designated as dormant




### library
Backwards-compatible alias.
```python
def library(self)
```

**Returns:**

`str`:  The protocol / NGS library name for this Sample.




### locate\_data\_source
Uses the template path provided in the project config section "data_sources" to piece together an actual path by substituting variables (encoded by "{variable}"") with sample attributes.
```python
def locate_data_source(self, data_sources, column_name='data_source', source_key=None, extra_vars=None)
```

**Parameters:**

- `data_sources` -- `Mapping`:  mapping from key name (as a value ina cell of a tabular data structure) to, e.g., filepath
- `column_name` -- `str`:  Name of sample attribute(equivalently, sample sheet column) specifying a derived column.
- `source_key` -- `str`:  The key of the data_source,used to index into the project config data_sources section. By default, the source key will be taken as the value of the specified column (as a sample attribute). For cases where the sample doesn't have this attribute yet (e.g. in a merge table), you must specify the source key.
- `extra_vars` -- `dict`:  By default, this will look topopulate the template location using attributes found in the current sample; however, you may also provide a dict of extra variables that can also be used for variable replacement. These extra variables are given a higher priority.


**Returns:**

`str`:  regex expansion of data source specified in configuration,with variable substitutions made


**Raises:**

- `ValueError`:  if argument to data_sources parameter is null/empty




### make\_sample\_dirs
Creates sample directory structure if it doesn't exist.
```python
def make_sample_dirs(self)
```




### set\_file\_paths
Sets the paths of all files for this sample.
```python
def set_file_paths(self, project=None)
```

**Parameters:**

- `project` -- `attmap.PathExAttMap`:  object with pointers to data paths andsuch, either full Project or PathExAttMap with sufficient data




### set\_genome
Set the genome for this Sample.
```python
def set_genome(self, genomes)
```

**Parameters:**

- `genomes` -- `Mapping[str, str]`:  genome assembly by organism name




### set\_pipeline\_attributes
Set pipeline-specific sample attributes.

Some sample attributes are relative to a particular pipeline run,
like which files should be considered inputs, what is the total
input file size for the sample, etc. This function sets these
pipeline-specific sample attributes, provided via a PipelineInterface
object and the name of a pipeline to select from that interface.
```python
def set_pipeline_attributes(self, pipeline_interface, pipeline_name, permissive=True)
```

**Parameters:**

- `pipeline_interface` -- `PipelineInterface`:  A PipelineInterfaceobject that has the settings for this given pipeline.
- `pipeline_name` -- `str`:  Which pipeline to choose.
- `permissive` -- `bool`:  whether to simply log a warning or errormessage rather than raising an exception if sample file is not found or otherwise cannot be read, default True




### set\_read\_type
For a sample with attr `ngs_inputs` set, this sets the read type (single, paired) and read length of an input file.
```python
def set_read_type(self, rlen_sample_size=10, permissive=True)
```

**Parameters:**

- `rlen_sample_size` -- `int`:  Number of reads to sample to infer read type,default 10.
- `permissive` -- `bool`:  whether to simply log a warning or error messagerather than raising an exception if sample file is not found or otherwise cannot be read, default True.




### set\_transcriptome
Set the transcriptome for this Sample.
```python
def set_transcriptome(self, transcriptomes)
```

**Parameters:**

- `transcriptomes` -- `Mapping[str, str]`:  transcriptome assembly byorganism name




### to\_yaml
Serializes itself in YAML format.
```python
def to_yaml(self, path=None, subs_folder_path=None, delimiter='_')
```

**Parameters:**

- `path` -- `str`:  A file path to write yaml to; provide this orthe subs_folder_path
- `subs_folder_path` -- `str`:  path to folder in which to place filethat's being written; provide this or a full filepath
- `delimiter` -- `str`:  text to place between the sample name and thesuffix within the filename; irrelevant if there's no suffix


**Returns:**

`str`:  filepath used (same as input if given, otherwise thepath value that was inferred)


**Raises:**

- `ValueError`:  if neither full filepath nor path to extantparent directory is provided.




### update
Update Sample object with attributes from a dict.
```python
def update(self, newdata, **kwargs)
```




## Class PeppyError
Base error type for peppy custom errors.


## Class CommandChecker
Validate PATH availability of executables referenced by a config file.

**Parameters:**

- `path_conf_file` -- `str`:  path to configuration file withsections detailing executable tools to validate
- `sections_to_check` -- `Iterable[str]`:  names ofsections of the given configuration file that are relevant; optional, will default to all sections if not given, but some may be excluded via another optional parameter
- `sections_to_skip` -- `Iterable[str]`:  analogous tothe check names parameter, but for specific sections to skip.


### failed
Determine whether *every* command succeeded for *every* config file section that was validated during instance construction.
```python
def failed(self)
```

**Returns:**

`bool`:  conjunction of execution success test result values,obtained by testing each executable in every validated section




### fetch\_samples
Collect samples of particular protocol(s).

Protocols can't be both positively selected for and negatively
selected against. That is, it makes no sense and is not allowed to
specify both selector_include and selector_exclude protocols. On the other hand, if
neither is provided, all of the Project's Samples are returned.
If selector_include is specified, Samples without a protocol will be excluded,
but if selector_exclude is specified, protocol-less Samples will be included.
```python
def fetch_samples(proj, selector_attribute=None, selector_include=None, selector_exclude=None)
```

**Parameters:**

- `proj` -- `Project`:  the Project with Samples to fetch
- `str` -- `Project`:  the sample selector_attribute to select for
- `selector_include` -- `Iterable[str] | str`:  protocol(s) of interest;if specified, a Sample must
- `selector_exclude` -- `Iterable[str] | str`:  protocol(s) to include


**Returns:**

`list[Sample]`:  Collection of this Project's samples withprotocol that either matches one of those in selector_include, or either lacks a protocol or does not match one of those in selector_exclude


**Raises:**

- `TypeError`:  if both selector_include and selector_exclude protocols arespecified; TypeError since it's basically providing two arguments when only one is accepted, so remain consistent with vanilla Python2




### grab\_project\_data
From the given Project, grab Sample-independent data.

There are some aspects of a Project of which it's beneficial for a Sample
to be aware, particularly for post-hoc analysis. Since Sample objects
within a Project are mutually independent, though, each doesn't need to
know about any of the others. A Project manages its, Sample instances,
so for each Sample knowledge of Project data is limited. This method
facilitates adoption of that conceptual model.
```python
def grab_project_data(prj)
```

**Parameters:**

- `prj` -- `Project`:  Project from which to grab data


**Returns:**

`Mapping`:  Sample-independent data sections from given Project





**Version Information**: `peppy` v0.20, generated by `lucidoc` v0.3dev