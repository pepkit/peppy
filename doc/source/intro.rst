
Introduction
=====================================


What are portable encapsulated projects?
^^^^^^^^

A `Portable Encapsulated Project <http://pepkit.github.io/>`_ (or PEP), is a dataset that subscribes to a standardized structure for  organizing metadata. It is written using a simple **yaml + tsv** format that can be read by a variety of tools in the pep toolkit, including *peppy*. If you don't already understand why the PEP concept is useful to you, you should start by reading the explanations on the `pepkit website <http://pepkit.github.io/>`_, where you can also find examples of PEP-formatted projects -- 

What does peppy do?
^^^^^^^^

*peppy*'s job is not to create a PEP for you, but to read it into python and give you an API to interface with that metadata from within python.


Who should use peppy?
^^^^^^^^

There are two key users that will be interested in ``peppy``: the python tool developer, and the python data analyst. 

**Python tool developer**. As a tool developer, you should import ``peppy`` in your python tool and make it so that your tool reads PEP projects as its input. This will make it easy for users to use your tool, because they will already have PEP-formatted projects for other tools.

**Python data analyst**. ``peppy`` provides you an easy way to read your project metadata into python. You'll immediately have access to a nice API to interface with your samples and all their attributes, setting the stage for your downstream analysis.
 
If you don't fit into one of those, you may be interested in the ``pepr`` R package, which provides an R interface to PEP objects, or the ``looper`` tool, which lets you run any command-line tool or pipeline on all your samples in your project. Read more about these and other tools at the `pepkit website <http://pepkit.github.io/>`_.

