Extended tutorial
***************************************************

The best way to learn is by example, so here's a quick tutorial to get you started using looper to run pre-made pipelines on a pre-made project.

First, install looper and pypiper (since our tutorial uses pypiper pipelines):

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

	If the looper executable isn't in your path, add it with ``export PATH=~/.local/bin:$PATH`` -- check out the :doc:`FAQ <faq>`.

Pipeline outputs
^^^^^^^^^^^^^^^^^^^^^^^^^^
Outputs of pipeline runs will be under the directory specified in the ``output_dir`` variable under the ``paths`` section in the project config file (see :doc:`config-files` ) this is usually the name of the project being run.

Inside there will be two directories:

-  ``results_pipeline`` [1]_ - a directory containing one directory with the output of the pipelines, for each sample.
-  ``submissions`` [2]_ - which holds yaml representations of the samples and log files of the submited jobs.


The sample-specific output of each pipeline type varies and is described in :doc:`pipelines`.

To use pre-made pipelines with your project, all you have to do is :doc:`define your project <define-your-project>` using looper's standard format. To link your own, custom built pipelines, you can :doc:`connect your pipeline to looper with a pipeline interface <pipeline-interface>`.

In this example, we just ran one example sample (an amplicon sequencing library) through a pipeline that processes amplicon data (to determine percentage of indels in amplicon).

From here to running hundreds of samples of various sample types is virtually the same effort!



.. rubric:: Footnotes

.. [1] This variable can also be specified in the ``results_subdir`` variable under the ``paths`` section of the project config file
.. [2] This variable can also be specified in the ``submission_subdir`` variable under the ``paths`` section of the project config file
