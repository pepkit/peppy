.. _project-config-file:

Defining a project
=============================================

To use ``looper`` with your project, you must define your project using Looper's standard project definition format. If you follow this format, then your project can be read not only by looper for submitting pipelines, but also for other tasks, like: summarizing pipeline output, analysis in R (using the ``project.init`` package), or building UCSC track hubs.

The format is simple and modular, so you only need to define the components you plan to use. You need to supply 2 files:

1. **Project config file** - a ``yaml`` file describing input and output file paths and other (optional) project settings
2. **Sample annotation sheet** - a ``csv`` file with 1 row per sample

The first file (**project config**) is just a few lines of ``yaml`` in the simplest case. Here's a minimal example **project_config.yaml**:


.. code-block:: yaml

	metadata:
	  sample_annotation: /path/to/sample_annotation.csv
	  output_dir: /path/to/output/folder
	  pipelines_dir: /path/to/pipelines/repository


The **output_dir** describes where you want to save pipeline results, and **pipelines_dir** describes where your pipeline code is stored.

The second file (**sample annotation sheet**) is where you list your samples, which is a comma-separated value (``csv``) file containing at least a few defined columns: a unique identifier column named ``sample_name``; a column named ``library`` describing the sample type (e.g. RNA-seq); and some way of specifying an input file. Here's a minimal example of **sample_annotation.csv**:


.. csv-table:: Minimal Sample Annotation Sheet
   :header: "sample_name", "library", "file"
   :widths: 30, 30, 30

   "frog_1", "RNA-seq", "frog1.fq.gz"
   "frog_2", "RNA-seq", "frog2.fq.gz"
   "frog_3", "RNA-seq", "frog3.fq.gz"
   "frog_4", "RNA-seq", "frog4.fq.gz"


With those two simple files, you could run looper, and that's fine for just running a quick test on a few files. You just type: ``looper run path/to/project_config.yaml`` and it will run all your samples through the appropriate pipeline. In practice, you'll probably want to use some of the more advanced features of looper by adding additional information to your configuration ``yaml`` file and your sample annotation ``csv`` file. These advanced options are detailed below.

Now, let's go through the more advanced details of both annotation sheets and project config files:

.. include:: sample-annotation-sheet.rst

.. include:: project-config.rst


