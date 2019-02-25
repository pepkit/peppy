# Package peppy Documentation

Project configuration, particularly for logging.

Project-scope constants may reside here, but more importantly, some setup here
will provide a logging infrastructure for all of the project's modules.
Individual modules and classes may provide separate configuration on a more
local level, but this will at least provide a foundation.


## Class Project
```python
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
```
### activate\_subproject
```py

def activate_subproject(self, subproject)

```



```python
Update settings based on subproject-specific values.

This method will update Project attributes, adding new values
associated with the subproject indicated, and in case of collision with
an existing key/attribute the subproject's value will be favored.

:param str subproject: A string with a subproject name to be activated
:return peppy.Project: Updated Project instance
```


### add\_entries
```py

def add_entries(self, entries)

```



```python
Update this instance with provided key-value pairs.

:param Iterable[(object, object)] | Mapping | pandas.Series entries:
    collection of pairs of keys and values
```


### build\_sheet
```py

def build_sheet(self, *protocols)

```



```python
Create table of subset of samples matching one of given protocols.

:return pandas.core.frame.DataFrame: DataFrame with from base version
    of each of this Project's samples, for indicated protocol(s) if
    given, else all of this Project's samples
```


### clear
```py

def clear(self)

```



```python
D.clear() -> None.  Remove all items from D.
```


### copy
```py

def copy(self)

```



```python
Copy self to a new object.
```


### finalize\_pipelines\_directory
```py

def finalize_pipelines_directory(self, pipe_path='')

```



```python
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
```


### get
```py

def get(self, key, default=None)

```



```python
D.get(k[,d]) -> D[k] if k in D, else d.  d defaults to None.
```


### get\_arg\_string
```py

def get_arg_string(self, pipeline_name)

```



```python
For this project, given a pipeline, return an argument string
specified in the project config file.
```


### get\_sample
```py

def get_sample(self, sample_name)

```



```python
Get an individual sample object from the project.

Will raise a ValueError if the sample is not found. In the case of multiple
samples with the same name (which is not typically allowed), a warning is
raised and the first sample is returned.

:param str sample_name: The name of a sample to retrieve
:return Sample: The requested Sample object
```


### get\_samples
```py

def get_samples(self, sample_names)

```



```python
Returns a list of sample objects given a list of sample names

:param list sample_names: A list of sample names to retrieve
:return list[Sample]: A list of Sample objects
```


### get\_subsample
```py

def get_subsample(self, sample_name, subsample_name)

```



```python
From indicated sample get particular subsample.

:param str sample_name: Name of Sample from which to get subsample
:param str subsample_name: Name of Subsample to get
:return peppy.Subsample: The Subsample of requested name from indicated
    sample matching given name
```


### infer\_name
```py

def infer_name(self)

```



```python
Infer project name from config file path.

First assume the name is the folder in which the config file resides,
unless that folder is named "metadata", in which case the project name
is the parent of that folder.

:return str: inferred name for project.
```


### is\_null
```py

def is_null(self, item)

```



```python
Conjunction of presence in underlying mapping and value being None

:param object item: Key to check for presence and null value
:return bool: True iff the item is present and has null value
```


### items
```py

def items(self)

```



```python
D.items() -> list of D's (key, value) pairs, as 2-tuples
```


### iteritems
```py

def iteritems(self)

```



```python
D.iteritems() -> an iterator over the (key, value) items of D
```


### iterkeys
```py

def iterkeys(self)

```



```python
D.iterkeys() -> an iterator over the keys of D
```


### itervalues
```py

def itervalues(self)

```



```python
D.itervalues() -> an iterator over the values of D
```


### keys
```py

def keys(self)

```



```python
D.keys() -> list of D's keys
```


### make\_project\_dirs
```py

def make_project_dirs(self)

```



```python
Creates project directory structure if it doesn't exist.
```


### non\_null
```py

def non_null(self, item)

```



```python
Conjunction of presence in underlying mapping and value not being None

:param object item: Key to check for presence and non-null value
:return bool: True iff the item is present and has non-null value
```


### parse\_config\_file
```py

def parse_config_file(self, subproject=None)

```



```python
Parse provided yaml config file and check required fields exist.

:param str subproject: Name of subproject to activate, optional
:raises KeyError: if config file lacks required section(s)
```


### pop
```py

def pop(self, key, default=<object object at 0x7f89863fb030>)

```



```python
D.pop(k[,d]) -> v, remove specified key and return the corresponding value.
If key is not found, d is returned if given, otherwise KeyError is raised.
```


### popitem
```py

def popitem(self)

```



```python
D.popitem() -> (k, v), remove and return some (key, value) pair
as a 2-tuple; but raise KeyError if D is empty.
```


### set\_project\_permissions
```py

def set_project_permissions(self)

```



```python
Make the project's public_html folder executable. 
```


### setdefault
```py

def setdefault(self, key, default=None)

```



```python
D.setdefault(k[,d]) -> D.get(k,d), also set D[k]=d if k not in D
```


### update
```py

def update(*args, **kwds)

```



```python
D.update([E, ]**F) -> None.  Update D from mapping/iterable E and F.
If E present and has a .keys() method, does:     for k in E: D[k] = E[k]
If E present and lacks .keys() method, does:     for (k, v) in E: D[k] = v
In either case, this is followed by: for k, v in F.items(): D[k] = v
```


### values
```py

def values(self)

```



```python
D.values() -> list of D's values
```


## Class MissingMetadataException
```python
Project needs certain metadata. 
```
## Class MissingSampleSheetError
```python
Represent case in which sample sheet is specified but nonexistent. 
```
## Class Sample
```python
Class to model Samples based on a pandas Series.

:param series: Sample's data.
:type series: Mapping | pandas.core.series.Series

:Example:

.. code-block:: python

    from models import Project, SampleSheet, Sample
    prj = Project("ngs")
    sheet = SampleSheet("~/projects/example/sheet.csv", prj)
    s1 = Sample(sheet.iloc[0])
```
### add\_entries
```py

def add_entries(self, entries)

```



```python
Update this instance with provided key-value pairs.

:param Iterable[(object, object)] | Mapping | pandas.Series entries:
    collection of pairs of keys and values
```


### as\_series
```py

def as_series(self)

```



```python
Returns a `pandas.Series` object with all the sample's attributes.

:return pandas.core.series.Series: pandas Series representation
    of this Sample, with its attributes.
```


### check\_valid
```py

def check_valid(self, required=None)

```



```python
Check provided sample annotation is valid.

:param Iterable[str] required: collection of required sample attribute
    names, optional; if unspecified, only a name is required.
:return (Exception | NoneType, str, str): exception and messages about
    what's missing/empty; null with empty messages if there was nothing
    exceptional or required inputs are absent or not set
```


### clear
```py

def clear(self)

```



```python
D.clear() -> None.  Remove all items from D.
```


### copy
```py

def copy(self)

```



```python
Copy self to a new object.
```


### determine\_missing\_requirements
```py

def determine_missing_requirements(self)

```



```python
Determine which of this Sample's required attributes/files are missing.

:return (type, str): hypothetical exception type along with message
    about what's missing; null and empty if nothing exceptional
    is detected
```


### generate\_filename
```py

def generate_filename(self, delimiter='_')

```



```python
Create a name for file in which to represent this Sample.

This uses knowledge of the instance's subtype, sandwiching a delimiter
between the name of this Sample and the name of the subtype before the
extension. If the instance is a base Sample type, then the filename
is simply the sample name with an extension.

:param str delimiter: what to place between sample name and name of
    subtype; this is only relevant if the instance is of a subclass
:return str: name for file with which to represent this Sample on disk
```


### generate\_name
```py

def generate_name(self)

```



```python
Generate name for the sample by joining some of its attribute strings.
```


### get
```py

def get(self, key, default=None)

```



```python
D.get(k[,d]) -> D[k] if k in D, else d.  d defaults to None.
```


### get\_attr\_values
```py

def get_attr_values(self, attrlist)

```



```python
Get value corresponding to each given attribute.

:param str attrlist: name of an attribute storing a list of attr names
:return list | NoneType: value (or empty string) corresponding to
    each named attribute; null if this Sample's value for the
    attribute given by the argument to the "attrlist" parameter is
    empty/null, or if this Sample lacks the indicated attribute
```


### get\_sheet\_dict
```py

def get_sheet_dict(self)

```



```python
Create a K-V pairs for items originally passed in via the sample sheet.

This is useful for summarizing; it provides a representation of the
sample that excludes things like config files and derived entries.

:return OrderedDict: mapping from name to value for data elements
    originally provided via the sample sheet (i.e., the a map-like
    representation of the instance, excluding derived items)
```


### get\_subsample
```py

def get_subsample(self, subsample_name)

```



```python
Retrieve a single subsample by name.

:param str subsample_name: The name of the desired subsample. Should 
    match the subsample_name column in the subannotation sheet.
:return peppy.Subsample: Requested Subsample object
```


### get\_subsamples
```py

def get_subsamples(self, subsample_names)

```



```python
Retrieve subsamples assigned to this sample

:param list[str] subsample_names: List of names of subsamples to retrieve
:return list[peppy.Subsample]: List of subsamples
```


### infer\_attributes
```py

def infer_attributes(self, implications)

```



```python
Infer value for additional field(s) from other field(s).

Add columns/fields to the sample based on values in those already-set
that the sample's project defines as indicative of implications for
additional data elements for the sample.

:param Mapping implications: Project's implied columns data
:return None: this function mutates state and is strictly for effect
```


### is\_dormant
```py

def is_dormant(self)

```



```python
Determine whether this Sample is inactive.

By default, a Sample is regarded as active. That is, if it lacks an
indication about activation status, it's assumed to be active. If,
however, and there's an indication of such status, it must be '1'
in order to be considered switched 'on.'

:return bool: whether this Sample's been designated as dormant
```


### is\_null
```py

def is_null(self, item)

```



```python
Conjunction of presence in underlying mapping and value being None

:param object item: Key to check for presence and null value
:return bool: True iff the item is present and has null value
```


### items
```py

def items(self)

```



```python
D.items() -> list of D's (key, value) pairs, as 2-tuples
```


### iteritems
```py

def iteritems(self)

```



```python
D.iteritems() -> an iterator over the (key, value) items of D
```


### iterkeys
```py

def iterkeys(self)

```



```python
D.iterkeys() -> an iterator over the keys of D
```


### itervalues
```py

def itervalues(self)

```



```python
D.itervalues() -> an iterator over the values of D
```


### keys
```py

def keys(self)

```



```python
D.keys() -> list of D's keys
```


### locate\_data\_source
```py

def locate_data_source(self, data_sources, column_name='data_source', source_key=None, extra_vars=None)

```



```python
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
```


### make\_sample\_dirs
```py

def make_sample_dirs(self)

```



```python
Creates sample directory structure if it doesn't exist.
```


### non\_null
```py

def non_null(self, item)

```



```python
Conjunction of presence in underlying mapping and value not being None

:param object item: Key to check for presence and non-null value
:return bool: True iff the item is present and has non-null value
```


### pop
```py

def pop(self, key, default=<object object at 0x7f89863fb030>)

```



```python
D.pop(k[,d]) -> v, remove specified key and return the corresponding value.
If key is not found, d is returned if given, otherwise KeyError is raised.
```


### popitem
```py

def popitem(self)

```



```python
D.popitem() -> (k, v), remove and return some (key, value) pair
as a 2-tuple; but raise KeyError if D is empty.
```


### set\_file\_paths
```py

def set_file_paths(self, project=None)

```



```python
Sets the paths of all files for this sample.

:param AttMap project: object with pointers to data paths and
    such, either full Project or AttMap with sufficient data
```


### set\_genome
```py

def set_genome(self, genomes)

```



```python
Set the genome for this Sample.

:param Mapping[str, str] genomes: genome assembly by organism name
```


### set\_pipeline\_attributes
```py

def set_pipeline_attributes(self, pipeline_interface, pipeline_name, permissive=True)

```



```python
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
```


### set\_read\_type
```py

def set_read_type(self, rlen_sample_size=10, permissive=True)

```



```python
For a sample with attr `ngs_inputs` set, this sets the 
read type (single, paired) and read length of an input file.

:param rlen_sample_size: Number of reads to sample to infer read type,
    default 10.
:type rlen_sample_size: int
:param permissive: whether to simply log a warning or error message 
    rather than raising an exception if sample file is not found or 
    otherwise cannot be read, default True.
:type permissive: bool
```


### set\_transcriptome
```py

def set_transcriptome(self, transcriptomes)

```



```python
Set the transcriptome for this Sample.

:param Mapping[str, str] transcriptomes: transcriptome assembly by
    organism name
```


### setdefault
```py

def setdefault(self, key, default=None)

```



```python
D.setdefault(k[,d]) -> D.get(k,d), also set D[k]=d if k not in D
```


### to\_yaml
```py

def to_yaml(self, path=None, subs_folder_path=None, delimiter='_')

```



```python
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
```


### update
```py

def update(self, newdata, **kwargs)

```



```python
Update Sample object with attributes from a dict.
```


### values
```py

def values(self)

```



```python
D.values() -> list of D's values
```


## Class PeppyError
```python
Base error type for peppy custom errors. 
```