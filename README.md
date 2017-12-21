# peppy python package

[![Documentation Status](http://readthedocs.org/projects/pep/badge/?version=latest)](http://peppy.readthedocs.io/en/latest/?badge=latest) [![Build Status](https://travis-ci.org/pepkit/pep.svg?branch=master)](https://travis-ci.org/pepkit/peppy)

`peppy` is the official python package for handling **Portable Encapsulated Projects** or **PEP**s. **PEP** is a standardized format for describing sample-intensive project metadata. `peppy` provides a python API for this format to load **PEP**-formatted metadata into python.

Complete documentation and API for the `peppy` python package is at [pep.readthedocs.io](http://peppy.readthedocs.io/).

Reference documentation for standard **PEP** format is at [pepkit.github.io](https://pepkit.github.io/).

# peppy and looper

The `peppy` package was originally developed in conjuction with [`looper`](http://github.com/pepkit/looper), a pipeline submission engine. The two projects have now been divided so that `peppy` can be used independently of `looper`. `looper` imports `peppy` to handle its project metadata loading and is therefore compatible with standard **PEP** format.

# Contributing

Contributions are welcome! For bug reports, feature requests, or questions, please use the [GitHub issue tracker](https://github.com/pepkit/peppy/issues). Please submit pull requests to the `dev` branch on the primary repository at http://github.com/pepkit/peppy.
