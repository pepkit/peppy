# Looper

[![Documentation Status](http://readthedocs.org/projects/looper/badge/?version=latest)](http://looper.readthedocs.io/en/latest/?badge=latest)
[![Build Status](https://travis-ci.org/vreuter/looper.svg?branch=master)](https://travis-ci.org/vreuter/looper)

__`Looper`__ is a pipeline submission engine that parses sample inputs and submits pipelines for each sample. Looper was conceived to use [pypiper](https://github.com/epigen/pypiper/) pipelines, but does not require this.

You can download the latest version from the [releases page](https://github.com/epigen/looper/releases).



# Links

 * Public-facing permalink: http://databio.org/looper
 * Documentation: [Read the Docs](http://looper.readthedocs.org/)
 * Source code: http://github.com/epigen/looper


# Quick start
Instructions for installation, usage, tutorials, and advanced options are available in the [Read the Docs documentation](http://looper.readthedocs.org/), and that's the best place to start. To get running quickly, you can install the latest release and put the `looper` executable in your `$PATH`: 


```
pip install https://github.com/epigen/looper/zipball/master
export PATH=$PATH:~/.local/bin
```

Looper supports Python 2.7 only and has been tested only in Linux. To use looper with your project, you must define your project using [Looper’s standard project definition format](http://looper.readthedocs.io/en/latest/define-your-project.html), which is a `yaml` config file passed as an argument to looper:

```bash
looper run project_config.yaml
```

# Contributing
- After adding tests in `tests` for a new feature or a bug fix, please run the test suite.
- To do so, the only additional dependencies needed beyond those for the package can be 
installed with:

  ```pip install -r requirements/requirements-dev.txt```
  
- Once those are installed, the tests can be run with `pytest`. Alternatively, 
`python setup.py test` can be used.

