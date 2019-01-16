# peppy python package

[![Documentation Status](http://readthedocs.org/projects/pep/badge/?version=latest)](http://peppy.readthedocs.io/en/latest/?badge=latest) [![Build Status](https://travis-ci.org/pepkit/peppy.svg?branch=master)](https://travis-ci.org/pepkit/peppy) [![PEP compatible](http://pepkit.github.io/img/PEP-compatible-green.svg)](http://pepkit.github.io)

`peppy` is the official python package for reading **Portable Encapsulated Projects** or **PEP**s in `python`. 

Links to complete documentation:

* Complete documentation and API for the `peppy` python package is at [peppy.readthedocs.io](http://peppy.readthedocs.io/).
* Reference documentation for standard **PEP** format is at [pepkit.github.io](https://pepkit.github.io/).
* Example PEPs for testing `peppy` are in the [example_peps repository](https://github.com/pepkit/example_peps).

# peppy and looper

The `peppy` package was originally developed in conjuction with [looper](http://github.com/pepkit/looper), a pipeline submission engine. The two projects have now been divided so that `peppy` can be used independently of `looper`. `looper` imports `peppy` to handle its project metadata loading and is therefore compatible with standard **PEP** format.

# Contributing

Contributions are welcome! For bug reports, feature requests, or questions, please use the [GitHub issue tracker](https://github.com/pepkit/peppy/issues). Please submit pull requests to the `dev` branch on the primary repository at http://github.com/pepkit/peppy.
