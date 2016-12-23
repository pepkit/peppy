
Configuration files
=========================

Looper uses `YAML <http://www.yaml.org/>`_ configuration files to describe a project. Looper is a very modular system, so there are few different YAML files. Here's an explanation of each. Which ones you need to know about will depend on whether you're a pipeline user (running pipelines on your project) or a pipeline developer (building a new pipeline).

Pipeline users
*****************

Users (non-developers) of the system only need to be aware of one YAML file:

-   :ref:`project config file <project-config-file>`: This file is specific to each project and contains information about the project's metadata, where the processed files should be saved, and other variables that allow to configure the pipelines specifically for this project.

If you are planning to submit jobs to a cluster, then you need to know about a second YAML file:

-	looper environment configuration: (in progress). This file tells looper how to use compute resource managers.

Pipeline developers
*****************

If you want to add a new pipeline to looper, then there are two YAML files that coordinate linking your pipeline in to your looper project.

-   :doc:`protocol mapping file <protocol-mapping>`: Tell looper which pipelines exist, and how to map each library (sample data type) to its pipelines.

-	:doc:`pipeline interface file <pipeline-interface>`: Links looper to the pipelines, describes variables, options and paths that the pipeline needs to know to run, and resource requirements for cluster managers.


Finally, if you're using Pypiper to develop pipelines, it uses a pipeline-specific configuration file (detailed in the Pypiper documentation):

-   :ref:`pipeline-config-file`: Each pipeline may have a configuration file describing where software is, and parameters to use for tasks within the pipeline.
 