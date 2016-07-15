
Sample annotation sheet
**************************************************

The ``sample annotation sheet`` is a csv file containing information about all samples in a project. This should be regarded as an immutable and the most important piece of metadata in a project. **One row corresponds to one sample** (or, more specifically, one pipeline run).

A sample annotation sheet may contain any number of columns you need for your project. You can think of these columns as `sample attributes`, and you may use these columns later in your pipelines or analysis (for example, to adjust tool parameters depending on sample attributes).

Certain keyword columns are required or provide looper-specific features.

Required columns are:

-  ``sample_name`` - a **unique** string identifying each sample [1]_.
-  ``library`` - the source of data for the sample (*e.g.* ATAC-seq, RNA-seq, RRBS).
-  ``organism`` - a string identifying the organism ("human", "mouse", "mixed").

Any additional columns become attributes of your sample and will be part of the project's metadata for the samples.

Special columns
""""""""""""""""""""""""""""""""""""""""""""""""""
Mostly, you have complete control over any other column names you want to add, but there are a few reserved names that Looper treats differently. One such special optional column is ``run``. If the value of this column is not 1, Looper will not submit the pipeline for that sample. This enables you to submit a subset of samples.

Usually you want your annotation sheet to specify the locations of files corresponding to each sample. For, this Looper adds a special column called ``data_source``. You can use this to simplify pointing to file locations with a neat string-replacement method that keeps things clean and portable. For more details, see :ref:`advanced-derived-columns`.

.. csv-table:: Example Sample Annotation Sheet
	:file: ../../examples/microtest_sample_annotation.csv

Example sample annotation sheet:

.. csv-table:: Example Sample Annotation Sheet
   :header: "sample_name", "library", "organism", "flowcell", "lane", "BSF_name", "data_source"
   :widths: 30, 30, 30, 30, 30, 30, 30

   "albt_0h", "RRBS", "albatross", "BSFX0190", "1", "albt_0h", ""
   "albt_1h", "RRBS", "albatross", "BSFX0190", "1", "albt_1h", ""
   "albt_2h", "RRBS", "albatross", "BSFX0190", "1", "albt_2h", ""
   "albt_3h", "RRBS", "albatross", "BSFX0190", "1", "albt_3h", ""
   "frog_0h", "RRBS", "frog", "", "", "", "frog_data"
   "frog_1h", "RRBS", "frog", "", "", "", "frog_data"
   "frog_2h", "RRBS", "frog", "", "", "", "frog_data"
   "frog_3h", "RRBS", "frog", "", "", "", "frog_data"


.. rubric:: Footnotes

.. [1] This should be a string without whitespace (space, tabs, etc...). If it contains whitespace, an error will be thrown. Similarly, looper will not allow this to be duplicated in your project.
