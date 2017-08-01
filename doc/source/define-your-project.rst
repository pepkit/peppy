.. _project-config-file:

How to define a project
=============================================

To use ``looper`` with your project, you must define your project using Looper's standard project definition format. If you follow this format, then your project can be read not only by looper for submitting pipelines, but also for other tasks, like: summarizing pipeline output, analysis in R (using the ``project.init`` package), or building UCSC track hubs.

The format is simple and modular, so you only need to define the components you plan to use. You need to supply 2 files:

1. **Project config file** - a ``yaml`` file describing input and output file paths and other (optional) project settings
2. **Sample annotation sheet** - a ``csv`` file with 1 row per sample

**Quick example**: In the simplest case, ``project_config.yaml`` is just a few lines of ``yaml``. Here's a minimal example **project_config.yaml**:


.. code-block:: yaml

   metadata:
     sample_annotation: /path/to/sample_annotation.csv
     output_dir: /path/to/output/folder
     pipeline_interfaces: path/to/pipeline_interface.yaml


The **output_dir** key specifies where to save results. The **pipeline_interfaces** key points to your looper-compatible pipelines (described in :doc:`linking the pipeline interface <pipeline-interface>`). The **sample_annotation** key points to another file, which is a comma-separated value (``csv``) file describing samples in the project. Here's a small example of **sample_annotation.csv**:


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

.. include:: sample-annotation-sheet.rst.inc

.. include:: project-config.rst.inc


