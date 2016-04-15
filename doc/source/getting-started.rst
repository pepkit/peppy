
Getting started
=========================

Create a project
--------------------


You define a project by creating a *project config file*, which is a yaml file with certain defined parameters. You describe locations for where to find data, provide an annotation of all samples included in the project, and make sure you record how to connect a sample type to the pipeline that should process it.


1. Produce a csv file with the metadata for your samples (see :doc:`Sample annotation sheet <sample-annotation-sheet>`).
2. Fill in a configuration file with information pertaining to this Project (see how here :doc:`Config Files <config-files>`).
3. Either get the source code or install ``pipelines`` (as described here: :doc:`How to use <index>`).

You can now run Looper for this project by running if you cloned the repository::

    python ~/repo/pipelines/looper.py -c metadata/config.txt

or like this if you installed the package::

    looper -c metadata/config.txt

To run a set of pipelines covering many types of NGS data, use the microtest data and the prebuilt sample annotation sheet and project config file in ``examples``.

To run a single pipeline with a sample, refer to the documentation of each individual pipeline in :doc:`Pipelines <pipelines>`.
