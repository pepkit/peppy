
Introduction
=====================================

Overview
******************************
Looper is a job submitting engine. If you have a pipeline and a bunch of samples you want to run through it, looper can help you organize the inputs and outputs. By defeault, it will just run your jobs sequentially on the local computer, but with a small configuration change, it will create and submit jobs to any cluster resource manager (like SLURM, SGE, or LFS).

Here's the idea: We essentially provide a format specification (the :ref:`project config file <project-config-file>`), which you use to describe your project. You create this single configuration file (in `yaml format <http://www.yaml.org/>`_), which includes: 

  - the output folder
  - filename for a csv file listing samples to process
  - an expression describing the input file locations (optional)
  - various other optional project-specific settings
  - anything else you want to save with the project

You pass this file as input to ``Looper``. ``Looper`` parses it and reads your sample annotation list, maps each sample to the appropriate pipeline, and creates and runs (or submits) job scripts. 

Looper is modular and totally configurable, so it scales as your needs grow. We provide sensible defaults so that you can get started quickly, but you can customize just about whatever you want by adding options to a configuration file. You have complete control. ``Looper`` handles the mundane project organization tasks that you don't want to worry about.



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


