
Introduction
=====================================

Looper is a job submitting engine. Do not confuse it with a pipeline workflow engine, which is used to build pipelines. Looper assumes you already have pipelines built, and it helps you map samples to those pipelines. If you have a pipeline and a bunch of samples you want to run, looper can help you organize the inputs and outputs.

It's scalable: by default, it runs your jobs sequentially on the local computer, but with a small configuration change, it will create and submit jobs to any cluster resource manager (like SLURM, SGE, or LFS).

The basics: We provide a format specification (the :ref:`project config file <project-config-file>`), which you use to describe your project. You create this single configuration file (in `yaml format <http://www.yaml.org/>`_), pass this file as input to ``looper``, which parses it, reads your sample list, maps each sample to the appropriate pipeline, and creates and runs (or submits) job scripts. Easy.

Looper is modular and totally configurable, so it scales as your needs grow. We provide sensible defaults for ease-of-use, but you can configure just about anything. You have complete control. ``Looper`` handles the mundane project organization tasks that you don't want to worry about.
