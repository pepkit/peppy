
Introduction
=====================================

Looper is a pipeline submitting engine. It helps you run a bunch of samples through an existing command-line pipeline. Looper standardizes the way the user (you) communicates with pipelines. While most pipelines specify a unique interface, looper lets you to use the same interface for every pipeline and every project. As you have more projects, this will save you time.

Looper is modular and totally configurable, so it scales as your needs grow. We provide sensible defaults for ease-of-use, but you can configure just about anything. By default, it runs your jobs sequentially on the local computer, but with a small configuration change, it will create and submit jobs to any cluster resource manager (like SLURM, SGE, or LFS).



How does it work?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We provide a format specification (the :ref:`project config file <project-config-file>`), which you use to describe your project. You create this single configuration file (in `yaml format <http://www.yaml.org/>`_), pass this file as input to ``looper``, which parses it, reads your sample list, maps each sample to the appropriate pipeline, and creates and runs (or submits) job scripts.

What looper does NOT do
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Looper **is not a pipeline workflow engine**, which is used to build pipelines. Looper assumes you already have pipelines built; if you're looking to build a new pipeline, we recommend `pypiper <http://pypiper.readthedocs.io/>`_, but you can use looper with **any pipeline that accepts command-line arguments**. Looper will then map samples to pipelines for you.


Why should I use looper?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The philosophical rationale for looper is that it **decouples sample handling from pipeline processing**. This creates a modular system that subscribes to `the unix philosophy <https://en.wikipedia.org/wiki/Unix_philosophy>`_, which provides many benefits. In many published bioinformatics pipelines, sample handling (submitting different samples to a cluster) is delicately intertwined with pipeline commands (running the actual code on a single sample). Often, it is impossible to divide sample handling from the pipeline itself. This approach leads to several challenges that can be reduced by separating the two:

	* running a pipeline on just a few samples or just a single test case for debugging may require a full-blown distributed compute environment if the system is not set up to work locally.

	* pipelines that handle multiple samples must necessary implement sample handling code, which in theory could be shared across many pipelines. Instead, most pipelines re-implement this, leading to a unique (and often sub-par) sample handling system for each published pipeline.

	* if each pipeline has its own sample processing code, then each also necessarily must define a unique interface: the expected folder structure, file naming scheme, and sample annotation format. This makes it nontrivial to move a dataset from one pipeline to another.

The modular approach taken by looper addresses these issues. By dividing sample processing from pipelining, the sample processing code needs only be written once (and can thus be written well) -- that's what looper is. The user interface can be made simple and intuitive, and a user must then learn only a single interface, which will work with any pipeline.