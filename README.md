# pep python package

[![Documentation Status](http://readthedocs.org/projects/pep/badge/?version=latest)](http://pep.readthedocs.io/en/latest/?badge=latest) [![Build Status](https://travis-ci.org/pepkit/pep.svg?branch=master)](https://travis-ci.org/pepkit/pep)

`pep` is the official python package for handling **Portable Encapsulated Projects** or **PEP**s. **PEP** is a standardized format for describing sample-intensive project metadata. `pep` provides a python API for this format to load **PEP**-formatted metadata into python.

Complete documentation and API for the `pep` python package is at [pep.readthedocs.io](http://pep.readthedocs.io/).

Reference documentation for standard **PEP** format is at [pepkit.github.io](https://pepkit.github.io/).

# pep and looper

The `pep` package was originally developed in conjuction with [`looper`](http://github.com/pepkit/looper), a pipeline submission engine. The two projects have now been divided so that `pep` can be used independently of `looper`. `looper` imports `pep` to handle its project metadata loading and is therefore compatible with standard **PEP** format.

# Contributing

Contributions are welcome! For bug reports, feature requests, or questions, please use the [GitHub issue tracker](https://github.com/pepkit/pep/issues). Please submit pull requests to the `dev` branch on the primary repository at http://github.com/pepkit/pep.
