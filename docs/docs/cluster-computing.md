# Cluster computing

By default, `looper` will build a shell script for each sample and then run each sample serially on the local computer. 
Where `looper` really excels, though, is in large projects that require submitting these jobs to a cluster resource manager 
(like SLURM, SGE, LFS, etc.). Looper handles the interface to the resource manager so that projects and pipelines can easily travel among environments. 

To configure `looper` to use cluster computing, all you have to do is tell provide a few things about your cluster setup. 
You create a configuration file (`compute_config.yaml`) and point an environment variable (`PEPENV`) to this file, and that's it!

Following is a brief overview to familiarize you with how this will work. 
When you're ready to hook looper up to your compute cluster, you should follow the complete, step-by-step instructions 
and examples in the [pepenv repository](https://github.com/pepkit/pepenv). 


## `PEPENV` overview
Here is an example ``compute_config.yaml`` file that works with a SLURM environment:
```yaml
compute:
  default:
    submission_template: templates/local_template.sub
    submission_command: sh
  loc:
    submission_template: templates/local_template.sub
    submission_command: sh    
  slurm:
    submission_template: templates/slurm_template.sub
    submission_command: sbatch
    partition: queue_name
```

Each section within `compute` defines a "compute package" that can be activated. 
By default, the package named `default` will be used, which in this example is identical to the `loc` package. 
You can make your default whatever you like. 
You may then choose a different compute package on the fly by specifying the `--compute` option: ``looper run --compute PACKAGE``. 
In this case, `PACKAGE` could be either `loc` (which would do the same thing as the default, so doesn't change anything) or `slurm`, 
which would run the jobs on SLURM, from queue `queue_name`. 
You can make as many compute packages as you wish (for example, to submit to different SLURM partitions).

There are a few sub-parameters for a compute package:
- `submission_template` is a path to the template submission script. 
A template file contains variables that are populated with values for each job you submit. 
More details can be found at the [`pepenv` repository](https://github.com/pepkit/pepenv). 
- `submission_command` is the command-line command that `looper` will prepend to the path of the 
submission script produced to actually run it (`sbatch` for SLURM, `qsub` for SGE, `sh` for localhost, etc).
- `partition` (optional) specifies a queue name.


## Resources
You may notice that the compute config file does not specify resources to request (like memory, CPUs, or time). Yet, these are required as well in order to submit a job to a cluster. In the looper system, **resources are not handled by the pepenv file** because they not relative to a particular computing environment; instead they are are variable and specific to a pipeline and a sample. As such, these items are defined in the ``pipeline_interface.yaml`` file (``pipelines`` section) that connects looper to a pipeline. The reason for this is that the pipeline developer is the most likely to know what sort of resources her pipeline requires, so she is in the best position to define the resources requested.

For more information on how to adjust resources, see the `pipelines` section of the [pipeline interface page](pipeline-interface.md). 
If all the different configuration files seem confusing, 
now is a good time to review [who's who in configuration files](config-files.md).
