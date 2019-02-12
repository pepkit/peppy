# Introduction

### *What* are portable encapsulated projects?

A [Portable Encapsulated Project](http://pepkit.github.io) (or "PEP"), 
is a collection of metadata files conforming to a standardized structure. 
These files are written using the simple **YAML** and **TSV/CSV** formats, 
and they can be read by a variety of tools in the pep toolkit, including `peppy`. 

If you don't already understand why the PEP concept is useful to you, 
you may begin by reading the [`pepkit website](http://pepkit.github.io), 
where you can also find example projects. 

### *Why* use `peppy`?

`peppy` parses a PEP and provides and API with which to interact from Python with PEP metadata.

### *Who* should use `peppy`?

There are two key users that will be interested in `peppy`  
  - A tool *developer*
  - A data *analyst* 

If you don't fit into one of those, you may be interested in the `pepr` R package, 
which provides an R interface to PEP objects, or the `looper` tool, 
which lets you run any command-line tool or pipeline on all your samples in your project. 
Read more about those and other tools on the [`pepkit` website](http://pepkit.github.io).

**Developer**

As a tool developer, you should import `peppy` in your python tool and read PEP projects as its input. 
This will simplify use of your tool, because users may already have PEP-formatted projects for other tools.

**Analyst**

`peppy` provides an easy way to read project metadata into python. 
You will have access to an API to access samples and their attributes, facilitating downstream analysis.
 