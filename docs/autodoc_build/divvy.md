# Package divvy Documentation

## Class ComputingConfiguration
Represents computing configuration objects.

The ComputingConfiguration class provides a computing configuration object
that is an *in memory* representation of a `divvy` computing configuration
file. This object has various functions to allow a user to activate, modify,
and retrieve computing configuration files, and use these values to populate
job submission script templates.

**Parameters:**

- `config_file` -- `str`:  YAML file specifying computing package data (The`DIVCFG` file).
- `no_env_error` -- `type`:  type of exception to raise if divvysettings can't be established, optional; if null (the default), a warning message will be logged, and no exception will be raised.
- `no_compute_exception` -- `type`:  type of exception to raise if computesettings can't be established, optional; if null (the default), a warning message will be logged, and no exception will be raised.


### activate\_package
Activates a compute package.

This copies the computing attributes from the configuration file into
the `compute` attribute, where the class stores current compute
settings.
```python
def activate_package(self, package_name):
```

**Parameters:**

- `package_name` -- `str`:  name for non-resource compute bundle,the name of a subsection in an environment configuration file


**Returns:**

`bool`:  success flag for attempt to establish compute settings




### clean\_start
Clear current active settings and then activate the given package.
```python
def clean_start(self, package_name):
```

**Parameters:**

- `package_name` -- `str`:  name of the resource package to activate


**Returns:**

`bool`:  success flag




### compute\_env\_var
Environment variable through which to access compute settings.
```python
def compute_env_var:
```

**Returns:**

`str`:  name of the environment variable to pointing tocompute settings




### default\_config\_file
Path to default compute environment settings file.
```python
def default_config_file:
```

**Returns:**

`str`:  Path to default compute settings file




### get\_active\_package
Returns settings for the currently active compute package
```python
def get_active_package(self):
```

**Returns:**

`AttMap`:  data defining the active compute package




### list\_compute\_packages
Returns a list of available compute packages.
```python
def list_compute_packages(self):
```

**Returns:**

`set[str]`:  names of available compute packages




### reset\_active\_settings
Clear out current compute settings.
```python
def reset_active_settings(self):
```

**Returns:**

`bool`:  success flag




### template
Get the currently active submission template.
```python
def template:
```

**Returns:**

`str`:  submission script content template for current state




### templates\_folder
Path to folder with default submission templates.
```python
def templates_folder:
```

**Returns:**

`str`:  path to folder with default submission templates




### update\_packages
Parse data from divvy configuration file.

Given a divvy configuration file, this function will update (not
overwrite) existing compute packages with existing values. It does not
affect any currently active settings.
```python
def update_packages(self, config_file):
```

**Parameters:**

- `config_file` -- `str`:  path to file withnew divvy configuration data




### write\_script
Given currently active settings, populate the active template to write a submission script.
```python
def write_script(self, output_path, extra_vars=None):
```

**Parameters:**

- `output_path` -- `str`:  Path to file to write as submission script
- `extra_vars` -- `Mapping`:  A list of Dict objects with key-value pairswith which to populate template fields. These will override any values in the currently active compute package.


**Returns:**

`str`:  Path to the submission script file




### write\_submit\_script
Write a submission script by populating a template with data.
```python
def write_submit_script(fp, content, data):
```

**Parameters:**

- `fp` -- `str`:  Path to the file to which to create/write submissions script.
- `content` -- `str`:  Template for submission script, defining keys thatwill be filled by given data
- `data` -- `Mapping`:  a "pool" from which values are available to replacekeys in the template


**Returns:**

`str`:  Path to the submission script



