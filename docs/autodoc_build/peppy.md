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


### constants
Return key-value pairs of pan-Sample constants for this Project.
```python
def constants(self)
```

**Returns:**

`Mapping`:  collection of KV pairs, each representing a pairingof attribute name and attribute value




### derived\_columns
Collection of sample attributes for which value of each is derived from elsewhere
```python
def derived_columns(self)
```

**Returns:**

`list[str]`:  sample attribute names for which value is derived




### implied\_columns
Collection of sample attributes for which value of each is implied by other(s)
```python
def implied_columns(self)
```

**Returns:**

`list[str]`:  sample attribute names for which value is implied by other(s)




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




## Class MissingMetadataException
Project needs certain metadata.


## Class MissingSampleSheetError
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


### input\_file\_paths
List the sample's data source / input files
```python
def input_file_paths(self)
```

**Returns:**

`list[str]`:  paths to data sources / input file for this Sample.




### library
Backwards-compatible alias.
```python
def library(self)
```

**Returns:**

`str`:  The protocol / NGS library name for this Sample.




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



