# Package peppy Documentation

## Class Project
A class to model a Project (collection of samples and metadata).
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
def activate_subproject(self, subproject):
```

**Parameters:**

- `subproject` -- `str`:  A string with a subproject name to be activated




### add\_entries
Update this instance with provided key-value pairs.
```python
def add_entries(self, entries):
```




### build\_sheet
Create table of subset of samples matching one of given protocols.
```python
def build_sheet(self, *protocols):
```




### clear
D.clear() -> None.  Remove all items from D.
```python
def clear(self):
```




### copy
Copy self to a new object.
```python
def copy(self):
```




### deactivate\_subproject
Bring the original project settings back

This method will bring the original project settings back after the subproject activation.
```python
def deactivate_subproject(self):
```




### finalize\_pipelines\_directory
Finalize the establishment of a path to this project's pipelines.

With the passed argument, override anything already set.
Otherwise, prefer path provided in this project's config, then
local pipelines folder, then a location set in project environment.
```python
def finalize_pipelines_directory(self, pipe_path=''):
```

**Parameters:**

- `pipe_path` -- `str`:  (absolute) path to pipelines


**Raises:**

- `PipelinesException`:  if (prioritized) search in attempt toconfirm or set pipelines directory failed




### get
D.get(k[,d]) -> D[k] if k in D, else d.  d defaults to None.
```python
def get(self, key, default=None):
```




### get\_arg\_string
For this project, given a pipeline, return an argument string

specified in the project config file.
```python
def get_arg_string(self, pipeline_name):
```




### get\_sample
Get an individual sample object from the project.

Will raise a ValueError if the sample is not found. In the case of multiple
samples with the same name (which is not typically allowed), a warning is
raised and the first sample is returned.
```python
def get_sample(self, sample_name):
```

**Parameters:**

- `sample_name` -- `str`:  The name of a sample to retrieve




### get\_samples
Returns a list of sample objects given a list of sample names
```python
def get_samples(self, sample_names):
```

**Parameters:**

- `sample_names` -- `list`:  A list of sample names to retrieve




### get\_subsample
From indicated sample get particular subsample.
```python
def get_subsample(self, sample_name, subsample_name):
```

**Parameters:**

- `sample_name` -- `str`:  Name of Sample from which to get subsample
- `subsample_name` -- `str`:  Name of Subsample to get




### infer\_name
Infer project name from config file path.

First assume the name is the folder in which the config file resides,
unless that folder is named "metadata", in which case the project name
is the parent of that folder.
```python
def infer_name(self):
```




### is\_null
Conjunction of presence in underlying mapping and value being None
```python
def is_null(self, item):
```

**Parameters:**

- `item` -- `object`:  Key to check for presence and null value




### items
D.items() -> list of D's (key, value) pairs, as 2-tuples
```python
def items(self):
```




### iteritems
D.iteritems() -> an iterator over the (key, value) items of D
```python
def iteritems(self):
```




### iterkeys
D.iterkeys() -> an iterator over the keys of D
```python
def iterkeys(self):
```




### itervalues
D.itervalues() -> an iterator over the values of D
```python
def itervalues(self):
```




### keys
D.keys() -> list of D's keys
```python
def keys(self):
```




### make\_project\_dirs
Creates project directory structure if it doesn't exist.
```python
def make_project_dirs(self):
```




### non\_null
Conjunction of presence in underlying mapping and value not being None
```python
def non_null(self, item):
```

**Parameters:**

- `item` -- `object`:  Key to check for presence and non-null value




### parse\_config\_file
Parse provided yaml config file and check required fields exist.
```python
def parse_config_file(self, subproject=None):
```

**Parameters:**

- `subproject` -- `str`:  Name of subproject to activate, optional




### pop
D.pop(k[,d]) -> v, remove specified key and return the corresponding value.

If key is not found, d is returned if given, otherwise KeyError is raised.
```python
def pop(self, key, default=<object object at 0x7f3de4253030>):
```




### popitem
D.popitem() -> (k, v), remove and return some (key, value) pair

as a 2-tuple; but raise KeyError if D is empty.
```python
def popitem(self):
```




### set\_project\_permissions
Make the project's public_html folder executable. 
```python
def set_project_permissions(self):
```




### setdefault
D.setdefault(k[,d]) -> D.get(k,d), also set D[k]=d if k not in D
```python
def setdefault(self, key, default=None):
```




### update
D.update([E, ]**F) -> None.  Update D from mapping/iterable E and F.

If E present and has a .keys() method, does:     for k in E: D[k] = E[k]
If E present and lacks .keys() method, does:     for (k, v) in E: D[k] = v
In either case, this is followed by: for k, v in F.items(): D[k] = v
```python
def update(*args, **kwds):
```




### values
D.values() -> list of D's values
```python
def values(self):
```




## Class MissingMetadataException
Project needs certain metadata. 
Project needs certain metadata. 


## Class MissingSampleSheetError
Represent case in which sample sheet is specified but nonexistent. 
Represent case in which sample sheet is specified but nonexistent. 


## Class Sample
Class to model Samples based on a pandas Series.
Class to model Samples based on a pandas Series.

**Example(s):**

```python
from models import Project, SampleSheet, Sample
prj = Project("ngs")
sheet = SampleSheet("~/projects/example/sheet.csv", prj)
s1 = Sample(sheet.iloc[0])
```


### add\_entries
Update this instance with provided key-value pairs.
```python
def add_entries(self, entries):
```




### as\_series
Returns a `pandas.Series` object with all the sample's attributes.
```python
def as_series(self):
```




### check\_valid
Check provided sample annotation is valid.
```python
def check_valid(self, required=None):
```

**Parameters:**

- `required` -- `Iterable[str]`:  collection of required sample attributenames, optional; if unspecified, only a name is required.




### clear
D.clear() -> None.  Remove all items from D.
```python
def clear(self):
```




### copy
Copy self to a new object.
```python
def copy(self):
```




### determine\_missing\_requirements
Determine which of this Sample's required attributes/files are missing.
```python
def determine_missing_requirements(self):
```




### generate\_filename
Create a name for file in which to represent this Sample.

This uses knowledge of the instance's subtype, sandwiching a delimiter
between the name of this Sample and the name of the subtype before the
extension. If the instance is a base Sample type, then the filename
is simply the sample name with an extension.
```python
def generate_filename(self, delimiter='_'):
```

**Parameters:**

- `delimiter` -- `str`:  what to place between sample name and name ofsubtype; this is only relevant if the instance is of a subclass




### generate\_name
Generate name for the sample by joining some of its attribute strings.
```python
def generate_name(self):
```




### get
D.get(k[,d]) -> D[k] if k in D, else d.  d defaults to None.
```python
def get(self, key, default=None):
```




### get\_attr\_values
Get value corresponding to each given attribute.
```python
def get_attr_values(self, attrlist):
```

**Parameters:**

- `attrlist` -- `str`:  name of an attribute storing a list of attr names




### get\_sheet\_dict
Create a K-V pairs for items originally passed in via the sample sheet.

This is useful for summarizing; it provides a representation of the
sample that excludes things like config files and derived entries.
```python
def get_sheet_dict(self):
```




### get\_subsample
Retrieve a single subsample by name.
```python
def get_subsample(self, subsample_name):
```

**Parameters:**

- `subsample_name` -- `str`:  The name of the desired subsample. Shouldmatch the subsample_name column in the subannotation sheet.




### get\_subsamples
Retrieve subsamples assigned to this sample
```python
def get_subsamples(self, subsample_names):
```

**Parameters:**

- `subsample_names` -- `list[str]`:  List of names of subsamples to retrieve




### infer\_attributes
Infer value for additional field(s) from other field(s).

Add columns/fields to the sample based on values in those already-set
that the sample's project defines as indicative of implications for
additional data elements for the sample.
```python
def infer_attributes(self, implications):
```

**Parameters:**

- `implications` -- `Mapping`:  Project's implied columns data




### is\_dormant
Determine whether this Sample is inactive.

By default, a Sample is regarded as active. That is, if it lacks an
indication about activation status, it's assumed to be active. If,
however, and there's an indication of such status, it must be '1'
in order to be considered switched 'on.'
```python
def is_dormant(self):
```




### is\_null
Conjunction of presence in underlying mapping and value being None
```python
def is_null(self, item):
```

**Parameters:**

- `item` -- `object`:  Key to check for presence and null value




### items
D.items() -> list of D's (key, value) pairs, as 2-tuples
```python
def items(self):
```




### iteritems
D.iteritems() -> an iterator over the (key, value) items of D
```python
def iteritems(self):
```




### iterkeys
D.iterkeys() -> an iterator over the keys of D
```python
def iterkeys(self):
```




### itervalues
D.itervalues() -> an iterator over the values of D
```python
def itervalues(self):
```




### keys
D.keys() -> list of D's keys
```python
def keys(self):
```




### locate\_data\_source
Uses the template path provided in the project config section

"data_sources" to piece together an actual path by substituting
variables (encoded by "{variable}"") with sample attributes.
```python
def locate_data_source(self, data_sources, column_name='data_source', source_key=None, extra_vars=None):
```

**Parameters:**

- `data_sources` -- `Mapping`:  mapping from key name (as a value ina cell of a tabular data structure) to, e.g., filepath
- `column_name` -- `str`:  Name of sample attribute(equivalently, sample sheet column) specifying a derived column.
- `source_key` -- `str`:  The key of the data_source,used to index into the project config data_sources section. By default, the source key will be taken as the value of the specified column (as a sample attribute). For cases where the sample doesn't have this attribute yet (e.g. in a merge table), you must specify the source key.
- `extra_vars` -- `dict`:  By default, this will look topopulate the template location using attributes found in the current sample; however, you may also provide a dict of extra variables that can also be used for variable replacement. These extra variables are given a higher priority.


**Returns:**

`str`:  regex expansion of data source specified in configuration,with variable substitutions made




### make\_sample\_dirs
Creates sample directory structure if it doesn't exist.
```python
def make_sample_dirs(self):
```




### non\_null
Conjunction of presence in underlying mapping and value not being None
```python
def non_null(self, item):
```

**Parameters:**

- `item` -- `object`:  Key to check for presence and non-null value




### pop
D.pop(k[,d]) -> v, remove specified key and return the corresponding value.

If key is not found, d is returned if given, otherwise KeyError is raised.
```python
def pop(self, key, default=<object object at 0x7f3de4253030>):
```




### popitem
D.popitem() -> (k, v), remove and return some (key, value) pair

as a 2-tuple; but raise KeyError if D is empty.
```python
def popitem(self):
```




### set\_file\_paths
Sets the paths of all files for this sample.
```python
def set_file_paths(self, project=None):
```




### set\_genome
Set the genome for this Sample.
```python
def set_genome(self, genomes):
```




### set\_pipeline\_attributes
Set pipeline-specific sample attributes.

Some sample attributes are relative to a particular pipeline run,
like which files should be considered inputs, what is the total
input file size for the sample, etc. This function sets these
pipeline-specific sample attributes, provided via a PipelineInterface
object and the name of a pipeline to select from that interface.
```python
def set_pipeline_attributes(self, pipeline_interface, pipeline_name, permissive=True):
```

**Parameters:**

- `pipeline_interface` -- `PipelineInterface`:  A PipelineInterfaceobject that has the settings for this given pipeline.
- `pipeline_name` -- `str`:  Which pipeline to choose.




### set\_read\_type
For a sample with attr `ngs_inputs` set, this sets the 

read type (single, paired) and read length of an input file.
```python
def set_read_type(self, rlen_sample_size=10, permissive=True):
```

**Parameters:**

- `rlen_sample_size` -- `int`:  Number of reads to sample to infer read type,default 10.




### set\_transcriptome
Set the transcriptome for this Sample.
```python
def set_transcriptome(self, transcriptomes):
```




### setdefault
D.setdefault(k[,d]) -> D.get(k,d), also set D[k]=d if k not in D
```python
def setdefault(self, key, default=None):
```




### to\_yaml
Serializes itself in YAML format.
```python
def to_yaml(self, path=None, subs_folder_path=None, delimiter='_'):
```

**Parameters:**

- `path` -- `str`:  A file path to write yaml to; provide this orthe subs_folder_path
- `subs_folder_path` -- `str`:  path to folder in which to place filethat's being written; provide this or a full filepath
- `delimiter` -- `str`:  text to place between the sample name and thesuffix within the filename; irrelevant if there's no suffix


**Returns:**

`str`:  filepath used (same as input if given, otherwise thepath value that was inferred)




### update
Update Sample object with attributes from a dict.
```python
def update(self, newdata, **kwargs):
```




### values
D.values() -> list of D's values
```python
def values(self):
```




## Class PeppyError
Base error type for peppy custom errors. 
Base error type for peppy custom errors. 


## Class CommandChecker
Validate PATH availability of executables referenced by a config file.
Validate PATH availability of executables referenced by a config file.

**Parameters:**

- `path_conf_file` -- `str`:  path to configuration file withsections detailing executable tools to validate
- `sections_to_check` -- `Iterable[str]`:  names ofsections of the given configuration file that are relevant; optional, will default to all sections if not given, but some may be excluded via another optional parameter


### fetch\_samples
Collect samples of particular protocol(s).

Protocols can't be both positively selected for and negatively
selected against. That is, it makes no sense and is not allowed to
specify both selector_include and selector_exclude protocols. On the other hand, if
neither is provided, all of the Project's Samples are returned.
If selector_include is specified, Samples without a protocol will be excluded,
but if selector_exclude is specified, protocol-less Samples will be included.
```python
def fetch_samples(proj, selector_attribute=None, selector_include=None, selector_exclude=None):
```

**Parameters:**

- `proj` -- `Project`:  the Project with Samples to fetch
- `str` -- `Project`:  the sample selector_attribute to select for
- `selector_include` -- `Iterable[str] | str`:  protocol(s) of interest;if specified, a Sample must
- `selector_exclude` -- `Iterable[str] | str`:  protocol(s) to include


**Returns:**

`list[Sample]`:  Collection of this Project's samples withprotocol that either matches one of those in selector_include, or either lacks a protocol or does not match one of those in selector_exclude




### grab\_project\_data
From the given Project, grab Sample-independent data.

There are some aspects of a Project of which it's beneficial for a Sample
to be aware, particularly for post-hoc analysis. Since Sample objects
within a Project are mutually independent, though, each doesn't need to
know about any of the others. A Project manages its, Sample instances,
so for each Sample knowledge of Project data is limited. This method
facilitates adoption of that conceptual model.
```python
def grab_project_data(prj):
```

**Parameters:**

- `prj` -- `Project`:  Project from which to grab data



