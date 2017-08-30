How to link a pipeline to your project
=============================================

Looper links to pipelines through a file called the `pipeline_interface`. How you use this depends on if you're using an existing pipeline or building a new pipeline. 

* **If you're using pre-made looper pipelines**, you don't need to create a new interface; you just point your project at the one that comes with the pipeline. See the first section below, `Linking a looper-compatible pipeline`.

* **If you need to link a new pipeline to looper**, then you'll need to create a new pipeline interface file. See the second section below, `Linking a custom pipeline`.


Linking a looper-compatible pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Many projects will require only existing pipelines that are already looper-compatible. We maintain a (growing) list of known publicly available `looper-compatible pipelines <https://github.com/pepkit/hello_looper/blob/master/looper_pipelines.md>`_ that will give you a good place to start. This list includes pipelines for data types like RNA-seq, bisulfite sequencing, etc.

To use one of these pipelines, just clone the repository and the point your project to that pipeline's `pipeline_interface` file. You do this with the `pipeline_interfaces` attribute in the `metadata` section of your `project_config` file:

.. code-block:: yaml

  metadata:
    pipeline_interfaces: /path/to/pipeline_interface.yaml

This value should be the absolute path to the pipeline interface file. After that, you just need to make sure your project definition provides all the necessary sample metadata that is required by the pipeline you want to use. For example, you will need to make sure your sample annotation sheet specifies the correct value under `protocol` that your linked pipeline understands. These details are specific to each pipeline and should be defined in the pipeline's README.


Linking a custom pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. HINT:: 

	If you're just a pipeline **user**, you don't need to worry about this section. This is for those who want to configure a new pipeline or an existing pipeline that isn't already looper-compatible.

Looper can connect samples to any pipeline, as long as it runs on the command line and uses text command-line arguments. These pipelines could be simple shell scripts, python scripts, perl scripts, or even pipelines built using a framework. Typically, we use python pipelines built using the `pypiper <http://pypiper.readthedocs.io>`_ package, which provides some additional power to looper, but this is optional.

Regardless of what pipelines you use, you will need to tell looper how to interface with your pipeline. You do that by specifying a **pipeline interface file**. The **pipeline interface** is a ``yaml`` file with two subsections:

1. ``protocol_mapping`` - maps sample ``protocol`` (aka ``library``) to one or more pipeline scripts.
2. ``pipelines`` -  describes the arguments and resources required by each pipeline script.

Let's start with a very simple example. A basic ``pipeline_interface.yaml`` file may look like this:


.. code-block:: yaml
    
    protocol_mapping:
      RRBS: rrbs_pipeline

    pipelines:
      rrbs_pipeline:
        name: RRBS
        path: path/to/rrbs.py
        arguments:
          "--sample-name": sample_name
          "--input": data_path


The first section specifies that samples of protocol ``RRBS`` will be mapped to the pipeline specified by key ``rrbs_pipeline``. The second section describes where the pipeline with key ``rrbs_pipeline`` is located and what command-line arguments it requires. Pretty simple. Let's go through these 2 sections in more detail:

.. include:: pipeline-interface-mapping.rst.inc

.. include:: pipeline-interface-pipelines.rst.inc

