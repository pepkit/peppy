
Sample annotation sheet
------------------------

One can run a single sample using one of the pipelines, but as projects grow it is conveninent to keep track of all the samples and be able to submit them all at once for processing if needed.

``pipelines`` uses a "sample annotation sheet" for this. It is a **csv file containing information about all samples in a project**. This should be regarded as an immutable and the most important piece of metadata in a project.

A sample annotation sheet requires **only three columns** plus additional ones (one to three) to specify where the sample input file is.

Required columns are:

-  ``sample_name`` - a string describing a Sample [1]_.
-  ``library`` - the type of data the Sample is (*e.g.* ATAC-seq, RNA-seq, RRBS).
-  ``organism`` - the biological organism the Sample is from.

You may further annotate the sample annotation sheet with any column you want and these attributes will be part of the project's metadata for the samples.

One special optional column is ``run``. If the Sample value of this column is not 1 it will not be submitted by the Looper.


Input files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Input files are naturally associated with the Sample, but sometimes they come from different sources or the relationship between the two is not one-to-one, which can be a complication.

Nonetheless we tried to solve this problem in the simplest way possible.

Data produced in-house (BSF)
""""""""""""""""""""""""""""
In a case of data produced at CeMM by the BSF, three additional columns will allow the discovery of files associated with the sample:

-  ``flowcell`` - the name of the BSF flowcell (should be something like BSFXXX)
-  ``lane`` - the lane number in the instrument
-  ``BSF_name`` - the name used to describe the sample in the BSF annotation [1]_.

Other sources
""""""""""""""""""""""""""""
In a case of data produced elsewhere or that is simply not in the same filesystem structure as the BSF data, only one more column is necessary.

-  ``data_source`` - a string which will match a pattern specified in the project configuration file. 

How this string is going to be used will be described in the second piece of metadata you need to run samples with Looper: the project configuration file (see :doc:`config-files` ).

We can use Samples from both origins (BSF and others) in the same project.

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

.. [1] This should be a string without whitespace (space, tabs, etc...). If it contains whitespace, an error will be thrown.
