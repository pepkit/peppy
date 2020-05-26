# Installation and Hello, World!

## Installation

With `pip` you can install the [latest release from PyPI](https://pypi.python.org/pypi/peppy):

```bash
pip install --user peppy
```

Update `peppy` with `pip`:

```bash
pip install --user --upgrade peppy
```

Releases and development versions may also be installed from the [GitHub releases](https://github.com/pepkit/peppy/releases):

```bash
pip install --user https://github.com/pepkit/peppy/zipball/master
```


## Hello world!

Now, to test `peppy`, let's grab an clone an example project that follows PEP format. 
We've produced a bunch of example PEPs in the [`example_peps` repository](https://github.com/pepkit/example_peps). 
Let's clone it:

```bash
git clone https://github.com/pepkit/example_peps.git
```

Then, from within the `example_peps` folder, enter the following commands in a Python session:

```python
import peppy

project = peppy.Project("example_basic/project_config.yaml") # instantiate in-memory Project representation
samples = project.samples # grab the list of Sample objects defined in this Project

# Find the input file for the first sample in the project
samples[0].file
```

That's it! You've got `peppy` running on an example project. 
Now you can play around with project metadata from within python. 
