Linking the pipeline interface
=============================================

.. HINT:: 

	Pipeline users don't need to worry about this section. This is for those who develop pipelines, or those who want to use a currently defined looper project to submit to an existing pipeline that isn't already configured for looper.

Looper can connect samples to any pipeline, as long as it runs on the command line and uses text command-line arguments. These pipelines could be simple shell scripts, python scripts, perl scripts, or even pipelines built using a framework. Typically, we use python pipelines built using the `pypiper <https://databio.org/pypiper>`_ package, which provides some additional power to looper, but this is optional.

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


The first section specifies that samples of protocol ``RRBS`` will be mapped to the pipeline specified by key ``rrbs_pipeline``. The second section describes where the pipeline named ``rrbs_pipeline`` is located and what command-line arguments it requires. Pretty simple. Let's go through each of these sections in more detail:

.. include:: pipeline-interface-mapping.rst.inc

.. include:: pipeline-interface-pipelines.rst.inc

