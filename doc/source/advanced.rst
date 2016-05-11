Advanced features
=====================================

Derived columns
****************************************
You can actually create as many derived columns as you want.

Include a ``derived_columns`` attribute in your project config yaml file:

derived_columns: [data_source, read1, read2]




Merge table
****************************************

Sometimes you have multiple input files that you want to merge for one sample. Rather than putting multiple lines in your sample annotation sheet, which causes conceptual and analytical challenges, we introduce a *merge table* which maps input files to samples for samples with more than one input file.

Just provide a merge table in the *metadata* section of your project config:

metadata:
  merge_table: mergetable.csv

Make sure the ``sample_name`` column of this table matches, and then include any columns you need to point to the data. ``Looper`` will automatically include all of these files as input passed to the pipelines.


Note: to handle different *classes* of input files, like read1 and read2, these are *not* merged and should be handled as different derived columns in the main sample annotation sheet.


Data produced in-house (BSF)
****************************************
In a case of data produced at CeMM by the BSF, three additional columns will allow the discovery of files associated with the sample:

-  ``flowcell`` - the name of the BSF flowcell (should be something like BSFXXX)
-  ``lane`` - the lane number in the instrument
-  ``BSF_name`` - the name used to describe the sample in the BSF annotation [1]_.

