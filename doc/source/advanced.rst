Advanced features
=====================================

Handling multiple input files
****************************************

Sometimes you have multiple input files that you want to merge for one sample. For example, a common use case is a single library that was spread across multiple sequencing lanes, yielding multiple input files that need to be merged, and then run through the pipeline as one. Rather than putting multiple lines in your sample annotation sheet, which causes conceptual and analytical challenges, we introduce two ways to merge these:

1. Use shell expansion characters (like '*' or '[]') in your `data_source` definition or filename (good for simple merges)
2. Specify a *merge table* which maps input files to samples for samples with more than one input file (infinitely customizable for more complicated merges).

To do the first option, just change your data source specifications, like this:

.. code-block:: yaml

      data_R1: "${DATA}/{id}_S{nexseq_num}_L00*_R1_001.fastq.gz"
      data_R2: "${DATA}/{id}_S{nexseq_num}_L00*_R2_001.fastq.gz"

To do the second option, just provide a merge table in the *metadata* section of your project config:

metadata:
  merge_table: mergetable.csv

Make sure the ``sample_name`` column of this table matches, and then include any columns you need to point to the data. ``Looper`` will automatically include all of these files as input passed to the pipelines. Warning: do not use both of these options simultaneously for the same sample, it will lead to multiple merges.

Note: to handle different *classes* of input files, like read1 and read2, these are *not* merged and should be handled as different derived columns in the main sample annotation sheet (and therefore different arguments to the pipeline).


Connecting to multiple pipelines
****************************************

If you have a project that contains samples of different types, then you may need to specify multiple pipeline repositories to your project. Starting in version 0.5, looper can handle a priority list of pipelines. Starting with version 0.6, these pointers should point directly at a pipeline interface files (instead of at directories as previously). in the metadata.pipeline_interfaces attribute.

For example:

.. code-block:: yaml

	metadata:
	  pipeline_interfaces: [pipeline_iface1.yaml, pipeline_iface2.yaml]


In this case, for a given sample, looper will first look in pipeline_iface1.yaml to see if appropriate pipeline exists for this sample type. If it finds one, it will use this pipeline (or set of pipelines, as specified in the protocol_mappings.yaml file). Having submitted a suitable pipeline it will ignore the pipeline_iface2.yaml interface. However if there is no suitable pipeline in the first interface, looper will check the second and, if it finds a match, will submit that. If no suitable pipelines are found in any of the interfaces, the sample will be skipped as usual.

