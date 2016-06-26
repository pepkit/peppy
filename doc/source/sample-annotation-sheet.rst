
Sample annotation sheet
**************************************************

The ``sample annotation sheet`` is a csv file containing information about all samples in a project. This should be regarded as an immutable and the most important piece of metadata in a project. **One row corresponds to one sample** (or, more specifically, one pipeline run).

A sample annotation sheet may contain any number of columns you need for your project. You can think of these columns as __sample attributs__, and you may use these columns later in your pipelines or analysis (for example, to adjust tool parameters depending on sample attributes).

Certain keyword columns are required or provide looper-specific features.

Required columns are:

-  ``sample_name`` - a **unique** string identifying each sample [1]_.
-  ``library`` - the source of data for the sample (*e.g.* ATAC-seq, RNA-seq, RRBS).
-  ``organism`` - a string identifying the organism ("human", "mouse", "mixed").

Any additional columns become attributes of your sample and will be part of the project's metadata for the samples.

Special columns: 

One special optional column is ``run``. If the value of this column is not 1, Looper will submit the pipeline for that sample. This enables you to specify only submitting a subset of samples.

Pointing to data files 
""""""""""""""""""""""""""""
On your sample sheet, you also want to somehow point to the input file for each sample. How do you add the path to the input file? Of course, you could just add a column with the file path, like ``/path/to/input/file.fastq.gz``. This is common, and it works in a pinch with Looper, but what if the data get moved, or your filesystem changes, or you switch servers or move institutes? Will this data still be there in 2 years? Do you want to manually manage these absolute paths?

``Looper`` makes it really easy to do better: using a "derived" column, you can use a variable to make this flexible. Think of each sample as belonging to a certain type (for simple experiments, the type will be the same); then define the location of these samples in the project configuration file. As a side bonus, you can easily include samples from different locations, and you can also share the same sample annotation sheet on different environments (i.e. servers or users) by having multiple project config files (or, better yet, by defining a subproject for each environment). The only thing you have to change is the project-level expression describing the location, not any sample attributes (plus, you get to eliminate those annoying long/path/arguments/in/your/sample/annotation/sheet).

By default, the "data_source" column is considered a derived column. Then, in project config, you specify an expression including variables (using "{variable}") to refer to any sample attributes. Like this:

```
data_sources:
  source1: /path/to/raw/data/{sample_name}_{sample_type}.bam
  source2: /path/from/collaborator/weirdNamingScheme_{external_id}.fastq
```

You can specify any derived columns you like by adding a ``derived_column`` section in the project config (more about this later).

How this string is going to be used will be described in the second piece of metadata you need to run samples with Looper: the project configuration file (see :doc:`config-files` ).

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
