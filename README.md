# pep python package

[![Documentation Status](http://readthedocs.org/projects/peppy/badge/?version=latest)](http://peppy.readthedocs.io/en/latest/?badge=latest) [![Build Status](https://travis-ci.org/pepkit/peppy.svg?branch=master)](https://travis-ci.org/pepkit/pep)

`pep` is the official python package for handling **Portable Encapsulated Projects** or **PEP**s, which is a standardized format for describing sample-intensive project metadata. `pep` provides a python interface to this format, allowing you to load your project metadata into an interactive python session.

The complete documentation and API for the `pep` python package can be found at [peppy.readthedocs.io](http://peppy.readthedocs.io/).

For reference documentation regarding the standard PEP format, please visit [pepkit.github.io](https://pepkit.github.io/).

# pep and looper

The `pep` package was originally developed in conjuction with [looper](http://github.com/pepkit/looper), a pipeline submission engine. The two projects have now been divided so that `pep` can be used independently of `looper`. `looper` imports `pep` to handle its project metadata loading and is therefore compatible with standard **PEP** format.

