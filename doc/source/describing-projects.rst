Project description
=============================================

To use ``looper`` with your project is simple: you must define your project using Looper's standard project definition format. If you follow this format, then your project can be read not only by looper for submitting pipelines, but also for other tasks, like: summarizing pipeline output, analysis in R (using the ``project.init`` package), or building UCSC track hubs for your project.

The format is simple and modular, so you only need to define the components you plan to use. You need to define 2 files:

1. **Project config file** - a ``yaml`` file describing input and output file paths and other (optional) project settings
2. **Sample annotation sheet** - a ``csv`` file with 1 row per sample

In the simplest case, ``project_config.yaml`` is just a few lines of ``yaml``. Here's a inimal example **project_config.yaml**:


.. code-block:: yaml

	metadata:
	  sample_annotation: /path/to/sample_annotation.csv
	  output_dir: /path/to/output/folder
	  pipelines_dir: /path/to/pipelines/repository


The **output_dir** describes where you to save pipeline results, and **pipelines_dir** describes where your pipeline code is stored. You will also need a second file to describe samples, which is a comma-separated value (``csv``) file containing at least a unique identifier column named ``sample_name``, a column named ``library`` describing the sample type, and some way of specifying an input file. Here's a minimal example of **sample_annotation.csv**:


.. csv-table:: Minimal Sample Annotation Sheet
   :header: "sample_name", "library", "file"
   :widths: 30, 30, 30

   "frog_1", "RNA-seq", "frog1.fq.gz"
   "frog_2", "RNA-seq", "frog2.fq.gz"
   "frog_3", "RNA-seq", "frog3.fq.gz"
   "frog_4", "RNA-seq", "frog4.fq.gz"


With those two simple files, you could run looper, and that's fine for just running a quick test on a few files. In practice, you'll probably want to use some of the more advanced features of looper by adding additional information to your configuration ``yaml`` file and your sample annotation ``csv`` file.

For example, by default, your jobs will run serially on your local computer, where you're running ``looper``. If you want to submit to a cluster resource manager (like SLURM or SGE), you just need to specify a ``compute`` section.

Let's go through the more advanced details of both annotation sheets and project config files:

.. include:: sample-annotation-sheet.rst

.. include:: project-config.rst


