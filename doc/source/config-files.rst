
Configuration files
=========================

Looper uses `YAML <http://www.yaml.org/>`_ configuration files to describe a project. Looper is a very modular system, so there are few different YAML files. Since it's easy to confuse what the different configuration files are used for, here's an explanation of each. Which ones you need to know about will depend on whether you're a pipeline user (running pipelines on your project) or a pipeline developer (building your own pipeline).


Pipeline users
*****************

Users (non-developers) of pipelines only need to be aware of one or two YAML files:

-   :ref:`project config file <project-config-file>`: This file is specific to each project and contains information about the project's metadata, where the processed files should be saved, and other variables that allow to configure the pipelines specifically for this project. This file follows the standard looper format (now referred to as ``PEP`` format).

If you are planning to submit jobs to a cluster, then you need to know about a second YAML file:

-	:ref:`PEPENV environment config <cluster-resource-managers>`:  This file tells looper how to use compute resource managers, like SLURM. You can find examples and instructions for setting this up at https://github.com/pepkit/pepenv. This file doesn't require much editing or maintenance beyond initial setup.

Pipeline developers
*****************

If you want to add a new pipeline to looper or tweak the way looper interacts with a pipeline for a given project, then you need to know about a configuration file that coordinates linking your pipeline in to your looper project.

-	:doc:`pipeline interface file <connecting-pipelines>`: Has two sections: 1) ``protocol_mapping`` tells looper which pipelines exist, and how to map each protocol (sample data type) to its pipelines; 2) ``pipelines`` links looper to the pipelines by describing variables, options and paths that the pipeline needs to know to run and outlines resource requirements for cluster managers.

Finally, if you're using Pypiper to develop pipelines, it uses a pipeline-specific configuration file (detailed in the Pypiper documentation):

-   `Pypiper pipeline config file <http://pypiper.readthedocs.io/en/latest/advanced.html#pipeline-config-files>`_: Each pipeline may (optionally) provide a configuration file describing where software is, and parameters to use for tasks within the pipeline. This configuration file is by default named identical to the pypiper script name, with a `.yaml` extension instead of `.py` (So `rna_seq.py` looks for an accompanying `rna_seq.yaml` file by default). These files can be changed on a per-project level using the :ref:`pipeline_config section in your project config file <pipeline-config-section>`.
