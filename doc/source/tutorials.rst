Extended tutorial
***************************************************

The best way to learn is by example, so here's an extended tutorial to get you started using looper to run pre-made pipelines on a pre-made project.

First, install looper and pypiper. `Pypiper <https://pypiper.readthedocs.io>`_ is our pipeline development framework; it is not required to use looper, which can work with any command-line pipeline, but this tutorial uses pypiper pipelines so we must install it now:

.. code:: bash

	pip install --user https://github.com/epigen/looper/zipball/master
	pip install --user https://github.com/epigen/pypiper/zipball/master


Now, you will need to grab a project to run, and some pipelines to run on it. We have a functional working project example and an open source pipeline repository on github.


.. code:: bash

	git clone https://github.com/epigen/microtest.git
	git clone https://github.com/epigen/open_pipelines.git


Now you can run this project with looper! Just use ``looper run``:

.. code:: bash

	looper run microtest/config/microtest_config.tutorial.yaml


.. HINT::

	If the looper executable isn't in your path, add it with ``export PATH=~/.local/bin:$PATH``.

Pipeline outputs
^^^^^^^^^^^^^^^^^^^^^^^^^^
Outputs of pipeline runs will be under the directory specified in the ``output_dir`` variable under the ``paths`` section in the project config file (see :doc:`config-files` ) this is usually the name of the project being run.

Inside there will be two directories:

-  ``results_pipeline`` - a directory containing one directory with the output of the pipelines, for each sample.
-  ``submissions`` - which holds yaml representations of the samples and log files of the submited jobs.

In this example, we just ran one example sample (an amplicon sequencing library) through a pipeline that processes amplicon data (to determine percentage of indels in amplicon).

From here to running hundreds of samples of various sample types is virtually the same effort!

On your own
^^^^^^^^^^^^^^^^^^^^^^^^^^

To use looper on your own, you will need to prepare 2 things: your project (what data do you want to process), and your pipelines (what do you want to do with that data). The next sections provide detailed instructions on how to tell looper about these 2 things:

1. **Project**. To link your project to looper, you will need to :doc:`define your project <define-your-project>` using looper's standard format. 

	
2.  **Pipelines**. You will want to either use pre-made looper-compatible pipelines, or link your own, custom built pipelines. Either way, the next section includes detailed instructions  on how to :doc:`connect your pipeline to looper <pipeline-interface>`.





