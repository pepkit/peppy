
Introduction
=====================================

Overview
******************************
Looper is a job submitting engine. If you have a pipeline and a bunch of samples you want to run through it, looper can help you organize the inputs and outputs. It creates and submits jobs either to cluster resource managers (like SLURM, SGE, or LFS) or to local compute power sequentially.

Here's the idea: You create a single configuration file (in yaml format) that describes your project. This file includes: 
  - the output folder
  - filename for a csv file listing samples to process
  - the input filenames (optionally) 
  - any specific pipeline arguments for this project
  - anything else you want to save with the project.

We essentially provide a format specification (:doc:`project-config-file`) to describe what this file can contain.

You pass this file as input to ``Looper``. ``Looper`` parses your file and follows the pointers to your sample list, processes that list, maps the samples to the appropriate pipelines they require, and creates and submits scripts for each sample.

You have complete control. ``Looper`` handles the mundane project organization tasks that you don't want to worry about.



Installing
******************************

You can install directly from GitHub using pip:

.. code-block:: bash

	pip install --user https://github.com/epigen/looper/zipball/master


Update with:

.. code-block:: bash

	pip install --user --upgrade https://github.com/epigen/looper/zipball/master


Support
******************************
Please use the issue tracker at GitHub to file bug reports or feature requests: https://github.com/epigen/looper/issues.


