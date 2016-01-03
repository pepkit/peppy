
Outputs and post-run scripts
============================

Pipeline outputs
------------------------
Outputs of pipeline runs will be under the directory specified in the ``output_dir`` variable under the ``paths`` section in the project config file (see :doc:`config-files` ) this is usually the name of the project being run.

Inside there will be two directories:

-  ``results_pipeline`` [1]_ - a directory containing one directory with the output of the pipelines, for each sample.
-  ``submissions`` [2]_ - which holds yaml representations of the samples and log files of the submited jobs.


The sample-specific output of each pipeline type varies and is described in :doc:`pipelines`.

Post-pipeline processing
------------------------

Once a pipeline has been run (or is running), you can do some post-processing on the results.

Here are some options:

-  ``scripts/flagCheck.sh`` - Summarize status flag to check on the status (running, completed, or failed) of pipelines.
-  ``scripts/make_trackhubs.py`` - Builds a track hub. Just pass it your config file.
-  ``scripts/summarizePipelineStats.R`` - Run this in the output folder and it will aggregate and summarize all key-value pairs reported in the ``PIPE_stats`` files, into tables for each pipeline, and a combined table across all pipelines run in this folder.

You can find other examples of stuff in the ``scripts`` folder.

.. rubric:: Footnotes

.. [1] This variable can also be specified in the ``results_subdir`` variable under the ``paths`` section of the project config file
.. [2] This variable can also be specified in the ``submission_subdir`` variable under the ``paths`` section of the project config file

