
Configuration files
=========================

There are few different YAML files and it can get confusing. Here's an explanation:

Looper and Pypiper use `YAML <http://www.yaml.com/>`_ configuration files (config files for short) to describe how a project is going to be run.

There are three types of config files (all yaml format) that are used by ``pipelines``:

-   :ref:`project-config-file`: This file is specific to each project and contains information about the project's metadata, where the processed sample files are going to exist and other variables that allow to configure the pipeline runs for this project.
-   :ref:`pipeline-config-file`: These files are specific to each pipeline and describe variables, options and paths that the pipeline needs to know to run.
-   :ref:`looper-config-files`: These are and tell the Looper which pipelines exist, how to map each sample to each pipeline and how to manage resources needed to run each sample.

.. note::
	A user of the pipelines will only have to deal with the :ref:`project-config-file`.

