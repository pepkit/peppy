# peppy

## Introduction

`peppy` is a Python package that provides an API for handling standardized project and sample metadata.
If you define your project in [Portable Encapsulated Project](http://pep.databio.org/en/2.0.0/) (PEP) format,
you can use the `peppy` package to instantiate an in-memory representation of your project and sample metadata.
You can then use `peppy` for interactive analysis, or to develop Python tools so you don't have to handle sample processing. `peppy` is useful to tool developers and data analysts who want a standard way of representing sample-intensive research project metadata.

## What is a PEP?

A [PEP](http://pep.databio.org/en/2.0.0/) is a collection of metadata files conforming to a standardized structure.
These files are written using the simple **YAML** and **TSV/CSV** formats,
and they can be read by a variety of tools in the pep toolkit, including `peppy`.  If you don't already understand why the PEP concept is useful to you,
start by reading the [PEP specification](http://pep.databio.org/en/2.0.0/),
where you can also find example projects.

## Why use `peppy`?

`peppy` provides an API with which to interact from Python with PEP metadata. 
This is often useful on its own, but the big wins include:

- *Portability* between computing environments
- *Reusability* among different tools and project stages
- *Durability* with respect to data movement

## Who should use `peppy`?

There are **two main kinds of user** that may have interest:

- A tool *developer*
- A data *analyst*

If you neither of those describes you, you may be interested in [`pepr`](http://code.databio.org/pepr) (R package),
which provides an R interface to PEP objects, or [looper](http://github.com/pepkit/looper) (command-line application),
which lets you run any command-line tool or pipeline on samples in a project.

**Developer**

As a tool developer, you should `import peppy` in your Python tool and read PEP projects as its input. 

This will simplify use of your tool, because users may already have PEP-formatted projects for other tools.

**Analyst**

`peppy` provides an easy way to read project metadata into Python.
You will have access to an API to access samples and their attributes, facilitating downstream analysis.
