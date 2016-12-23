Advanced features
=====================================

.. _advanced-derived-columns:

Pointing to flexible data with derived columns
****************************************
On your sample sheet, you will need to point to the input file or files for each sample. Of course, you could just add a column with the file path, like ``/path/to/input/file.fastq.gz``. For example:


.. csv-table:: Sample Annotation Sheet (bad example)
	:header: "sample_name", "library", "organism", "time", "file_path"
	:widths: 20, 20, 20, 10, 30

	"pig_0h", "RRBS", "pig", "0", "/data/lab/project/pig_0h.fastq"
	"pig_1h", "RRBS", "pig", "1", "/data/lab/project/pig_1h.fastq"
	"frog_0h", "RRBS", "frog", "0", "/data/lab/project/frog_0h.fastq"
	"frog_1h", "RRBS", "frog", "1", "/data/lab/project/frog_1h.fastq"
  

This is common, and it works in a pinch with Looper, but what if the data get moved, or your filesystem changes, or you switch servers or move institutes? Will this data still be there in 2 years? Do you want long file paths cluttering your annotation sheet? What if you have 2 or 3 input files? Do you want to manually manage these unwieldy absolute paths?


``Looper`` makes it really easy to do better: using a ``derived column``, you can use variables to make this flexible. So instead of ``/long/path/to/sample.fastq.gz`` in your table, you just write ``source1`` (or whatever):

.. csv-table:: Sample Annotation Sheet (good example)
	:header: "sample_name", "library", "organism", "time", "file_path"
	:widths: 20, 20, 20, 10, 30

	"pig_0h", "RRBS", "pig", "0", "source1"
	"pig_1h", "RRBS", "pig", "1", "source1"
	"frog_0h", "RRBS", "frog", "0", "source1"
	"frog_1h", "RRBS", "frog", "1", "source1"

Then, in your config file you specify which columns are derived (in this case, ``file_path``), as well as a string that will construct your path based on other sample attributes encoded using brackets as in ``{sample_attribute}``, like this:


.. code-block:: yaml

  derived_columns: [file_path]
  data_sources:
    source1: /data/lab/project/{sample_name}.fastq
    source2: /path/from/collaborator/weirdNamingScheme_{external_id}.fastq

That's it! The variables will be automatically populated as in the original example. To take this a step further, you'd get the same result with this config file, which substitutes ``{sample_name}`` for other sample attributes, ``{organism}`` and ``{time}``:

.. code-block:: yaml

  derived_columns: [file_path]
  data_sources:
    source1: /data/lab/project/{organism}_{time}h.fastq
    source2: /path/from/collaborator/weirdNamingScheme_{external_id}.fastq


As long as your file naming system is systematic, you can easily deal with any external naming scheme, no problem at all. The idea is: don't put absolute paths to files in your annotation sheet. Instead, specify a data source and then provide a regex in the config file. This way if your data changes locations (which happens more often than we would like), or you change servers, you just have to change the config file and not update paths in the annotation sheet. This makes the whole project more portable.

By default, the "data_source" column is considered a derived column. But you can specify as many additional derived columns as you want. An expression including any sample attributes (using ``{attribute}``) will be populated for those columns. 

Think of each sample as belonging to a certain type (for simple experiments, the type will be the same); then define the location of these samples in the project configuration file. As a side bonus, you can easily include samples from different locations, and you can also share the same sample annotation sheet on different environments (i.e. servers or users) by having multiple project config files (or, better yet, by defining a subproject for each environment). The only thing you have to change is the project-level expression describing the location, not any sample attributes (plus, you get to eliminate those annoying long/path/arguments/in/your/sample/annotation/sheet).

Check out the complete working example in the `microtest repository <https://github.com/epigen/microtest/tree/master/config>`_.

.. _cluster-resource-managers:

Using cluster resource managers
****************************************

.. warning:: This is still in progress

Looper uses a template-based system for building scripts. By default, looper will just build a shell script and run them serially. Compute settings can be changed using an environment script, which you point to with a shell environment variable called ``LOOPERENV``.

Complete instructions for configuring your compute environment are availble in the looperenv repository at https://github.com/epigen/looperenv.

For each iteration, `looper` will create one or more submission scripts for that sample. The `compute` settings specify how these scripts will be both produced and run.  This makes it very portable and easy to change cluster management systems, or to just use a local compute power like a laptop or standalone server, by just changing the two variables in the `compute` section.

Example:

.. code-block:: yaml

	compute:
	  default:
	    submission_template: pipelines/templates/local_template.sub
	    submission_command: sh
	  slurm:
	    submission_template: pipelines/templates/slurm_template.sub
	    submission_command: sbatch
	    partition: queue_name


There are two sub-parameters in the compute section. First, `submission_template` is a (relative or absolute) path to the template submission script. This is a template with variables (encoded like `{VARIABLE}`), which will be populated independently for each sample as defined in `pipeline_inteface.yaml`. The one variable ``{CODE}`` is a reserved variable that refers to the actual python command that will run the pipeline. Otherwise, you can use any variables you define in your `pipeline_interface.yaml`.

Second, the `submission_command` is the command-line command that `looper` will prepend to the path of the produced submission script to actually run it (`sbatch` for SLURM, `qsub` for SGE, `sh` for localhost, etc).

In [`templates/`](templates/) are examples for submission templates for [SLURM](templates/slurm_template.sub), [SGE](templates/sge_template.sub), and [local runs](templates/localhost_template.sub). For a local run, just pass the script to the shell with `submission_command: sh`. This will cause each sample to run sequentially, as the shell will block until the run is finished and control is returned to `looper` for the next iteration.



Merge table
****************************************

Sometimes you have multiple input files that you want to merge for one sample. Rather than putting multiple lines in your sample annotation sheet, which causes conceptual and analytical challenges, we introduce a *merge table* which maps input files to samples for samples with more than one input file.

Just provide a merge table in the *metadata* section of your project config:

metadata:
  merge_table: mergetable.csv

Make sure the ``sample_name`` column of this table matches, and then include any columns you need to point to the data. ``Looper`` will automatically include all of these files as input passed to the pipelines.


Note: to handle different *classes* of input files, like read1 and read2, these are *not* merged and should be handled as different derived columns in the main sample annotation sheet.


Data produced at CeMM
****************************************
In a case of data produced at CeMM by the BSF, three additional columns will allow the discovery of files associated with the sample:

-  ``flowcell`` - the name of the BSF flowcell (should be something like BSFXXX)
-  ``lane`` - the lane number in the instrument
-  ``BSF_name`` - the name used to describe the sample in the BSF annotation [1]_.

