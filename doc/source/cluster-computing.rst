.. _cluster-resource-managers:

Cluster computing
=============================================

By default, looper will build a shell script for each sample and then run each sample serially on the local computer. But where looper really excels is in large projects that require submitting these jobs to a cluster resource manager (like SLURM, SGE, LFS, etc.). Looper handles the interface to the resource manager so that projects and pipelines can be moved to different environments with ease. 

To configure looper to use cluster computing, all you have to do is tell looper a few things about your cluster setup. You do this by specifying a computing environment configuration file (`compute_config.yaml`). Once you create the file, you will need to point an environment variable called ``LOOPERENV`` to this file, and that's it! Complete instructions for configuring your compute environment, as well as some working configuration files, are available in the looperenv repository at https://github.com/epigen/looperenv.


Here is an example ``compute_config.yaml`` file that works with a SLURM environment:

.. code-block:: yaml

   compute:
     default:
       submission_template: pipelines/templates/local_template.sub
       submission_command: sh
     local:
       submission_template: pipelines/templates/local_template.sub
       submission_command: sh    
     slurm:
       submission_template: pipelines/templates/slurm_template.sub
       submission_command: sbatch
       partition: queue_name


The sub-sections below ``compute`` each define a "compute package" that can be activated. By default, the package named ``default`` will be used, which is identical to the ``local`` package. You can switch which compute resources to use on the fly by specifying the ``--compute`` argument to looper run like so: ``looper run --compute slurm``. This would run the jobs on slurm, with queue ``queue_name``. You can make as many compute packages as you wish (for example, to submit to different slurm partitions).

There are two or three sub-parameters for a compute package. First, `submission_template` is a (relative or absolute) path to the template submission script. Templates are described in more detail in the `looperenv readme <https://github.com/epigen/looperenv>`_. Second, the `submission_command` is the command-line command that `looper` will prepend to the path of the produced submission script to actually run it (`sbatch` for SLURM, `qsub` for SGE, `sh` for localhost, etc).

Submission templates
****************************************
A template uses variables (encoded like `{VARIABLE}`), which will be populated independently for each sample as defined in `pipeline_interface.yaml`. The one variable ``{CODE}`` is a reserved variable that refers to the actual python command that will run the pipeline. Otherwise, you can use any variables you define in your `pipeline_interface.yaml`. In `Templates <https://github.com/epigen/looperenv/tree/master/templates>`__ are examples for submission templates for `SLURM <https://github.com/epigen/looperenv/blob/master/templates/slurm_template.sub>`__, `SGE <https://github.com/epigen/looperenv/blob/master/templates/sge_template.sub>`__, and `local runs <https://github.com/epigen/looperenv/blob/master/templates/localhost_template.sub>`__. You can also create your own templates, giving looper ultimate flexibility to work with any compute infrastructure in any environment.

