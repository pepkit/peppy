Advanced features
=====================================

.. _advanced-derived-columns:

Pointing to data paths flexibly with "derived columns"
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


``Looper`` makes it really easy to do better: using a columns from the sample metadata, you can derive a data path that is flexible - we call these newly constructed fields a ``derived column``. So instead of ``/long/path/to/sample.fastq.gz`` in your table, you just write ``source1`` (or whatever):

.. csv-table:: Sample Annotation Sheet (good example)
	:header: "sample_name", "library", "organism", "time", "file_path"
	:widths: 20, 20, 20, 10, 30

	"pig_0h", "RRBS", "pig", "0", "source1"
	"pig_1h", "RRBS", "pig", "1", "source1"
	"frog_0h", "RRBS", "frog", "0", "source1"
	"frog_1h", "RRBS", "frog", "1", "source1"

Then, in your config file you specify which sample attributes (similar to the metadata columns) are derived (in this case, ``file_path``), as well as a string that will construct your path based on other sample attributes encoded using brackets as in ``{sample_attribute}``, like this:


.. code-block:: yaml

  derived_columns: [file_path]
  data_sources:
    source1: /data/lab/project/{sample_name}.fastq
    source2: /path/from/collaborator/weirdNamingScheme_{external_id}.fastq

That's it! The attributes will be automatically populated as in the original example. To take this a step further, you'd get the same result with this config file, which substitutes ``{sample_name}`` for other sample attributes, ``{organism}`` and ``{time}``:

.. code-block:: yaml

  derived_columns: [file_path]
  data_sources:
    source1: /data/lab/project/{organism}_{time}h.fastq
    source2: /path/from/collaborator/weirdNamingScheme_{external_id}.fastq


As long as your file naming system is systematic, you can easily deal with any external naming scheme, no problem at all. The idea is: don't put absolute paths to files in your annotation sheet. Instead, specify a data source and then provide a regex in the config file. This way if your data changes locations (which happens more often than we would like), or you change servers, you just have to change the config file and not update paths in the annotation sheet. This makes the whole project more portable.

By default, the "data_source" column is considered a derived column. But you can specify as many additional derived columns as you want. An expression including any sample attributes (using ``{attribute}``) will be populated for those columns. 

Think of each sample as belonging to a certain type (for simple experiments, the type will be the same); then define the location of these samples in the project configuration file. As a side bonus, you can easily include samples from different locations, and you can also share the same sample annotation sheet on different environments (i.e. servers or users) by having multiple project config files (or, better yet, by defining a subproject for each environment). The only thing you have to change is the project-level expression describing the location, not any sample attributes (plus, you get to eliminate those annoying long/path/arguments/in/your/sample/annotation/sheet).

Check out the complete working example in the `microtest repository <https://github.com/epigen/microtest/tree/master/config>`__.

.. _cluster-resource-managers:

Using cluster resource managers
****************************************

For each sample, ``looper`` will create one or more submission scripts for that sample. The ``compute`` settings specify how these scripts will be both produced and run. This makes it very portable and easy to change cluster management systems by just changing a few variables in a configuration file. By default, looper builds a shell script for each sample and runs them serially: the shell will block until the each run is finished and control is returned to ``looper`` for the next iteration. Compute settings can be changed using an environment configuration file called ``looperenv``. Several common engines (SLURM and SGE) come by default, but the system gives you complete flexibility, so you can easily configure looper to work with your resource manager.

For complete instructions on configuring your compute environment, see the looperenv repository at https://github.com/epigen/looperenv. Here's a brief overview. Here's an example `looperenv` file:

.. code-block:: yaml

	compute:
	  default:
	    submission_template: pipelines/templates/local_template.sub
	    submission_command: sh
	  slurm:
	    submission_template: pipelines/templates/slurm_template.sub
	    submission_command: sbatch
	    partition: queue_name


There are two sub-parameters in the compute section. First, ``submission_template`` is a (relative or absolute) path to the template submission script. Looper uses a template-based system for building scripts. This is a template with variables (encoded like ``{VARIABLE}``), which will be populated independently for each sample as defined in ``pipeline_inteface.yaml``. The one variable ``{CODE}`` is a reserved variable that refers to the actual shell command that will run the pipeline. Otherwise, you can use any variables you define in your `pipeline_interface.yaml`.

Second, the ``submission_command`` is the command-line command that ``looper`` will prepend to the path of the produced submission script to actually run it (``sbatch`` for SLURM, `qsub` for SGE, ``sh`` for localhost, etc).

In `Templates <https://github.com/epigen/looper/tree/master/templates>`__ are examples for submission templates for `SLURM <https://github.com/epigen/looper/blob/master/templates/slurm_template.sub>`__, `SGE <https://github.com/epigen/looper/blob/master/templates/sge_template.sub>`__, and `local runs <https://github.com/epigen/looper/blob/master/templates/localhost_template.sub>`__. 




Handling multiple input files with a merge table
****************************************

Sometimes you have multiple input files that you want to merge for one sample. Rather than putting multiple lines in your sample annotation sheet, which causes conceptual and analytical challenges, we introduce a *merge table* which maps input files to samples for samples with more than one input file.

Just provide a merge table in the *metadata* section of your project config:

metadata:
  merge_table: mergetable.csv

Make sure the ``sample_name`` column of this table matches, and then include any columns you need to point to the data. ``Looper`` will automatically include all of these files as input passed to the pipelines.

Note: to handle different *classes* of input files, like read1 and read2, these are *not* merged and should be handled as different derived columns in the main sample annotation sheet (and therefore different arguments to the pipeline).


.. _extending-sample-objects:

Extending Sample objects
****************************************

Looper uses object oriented programming (OOP) under the hood. This means that concepts like a sample to be processed or a project are modeled as objects in Python. 

By default we use `generic models <https://github.com/epigen/looper/tree/master/looper/models.py>`__ (see the `API <api.html>`__ for more) to handle samples in Looper, but these can also be reused in other contexts by importing ``looper.models`` or by means of object serialization through YAML files.

Since these models provide useful methods to interact, update, and store attributes in the objects (most nobly *samples* - ``Sample`` object), a useful use case is during the run of a pipeline: pipeline scripts can extend ``Sample`` objects with further attributes or methods.

Example:

You want a convenient yet systematic way of specifying many file paths for several samples depending on the type of NGS sample you're handling: a ChIP-seq sample might have at some point during a run a peak file with a certain location, while a RNA-seq sample will have a file with transcript quantifications. Both paths to the files exist only for the respective samples, will likely be used during a run of a pipeline, but also during some analysis later on.
By working with ``Sample`` objects that are specific to each file type, you can specify the location of such files only once during the whole process and later access them "on the fly".


**To have** ``Looper`` **create a Sample object specific to your data type, simply import the base** ``Sample`` **object from** ``looper.models``, **and create a** ``class`` **that inherits from it that has an** ``__library__`` **attribute:**


.. code-block:: python

	# atacseq.py

	from looper.models import Sample

	class ATACseqSample(Sample):
		"""
		Class to model ATAC-seq samples based on the generic Sample class.

		:param series: Pandas `Series` object.
		:type series: pandas.Series
		"""
		__library__ = "ATAC-seq"

		def __init__(self, series):
			if not isinstance(series, pd.Series):
				raise TypeError("Provided object is not a pandas Series.")
			super(ATACseqSample, self).__init__(series)
			self.make_sample_dirs()

		def set_file_paths(self):
			"""Sets the paths of all files for this sample."""
			# Inherit paths from Sample by running Sample's set_file_paths()
			super(ATACseqSample, self).set_file_paths()

			self.fastqc = os.path.join(self.paths.sample_root, self.name + ".fastqc.zip")
			self.trimlog = os.path.join(self.paths.sample_root, self.name + ".trimlog.txt")
			self.fastq = os.path.join(self.paths.sample_root, self.name + ".fastq")
			self.trimmed = os.path.join(self.paths.sample_root, self.name + ".trimmed.fastq")
			self.mapped = os.path.join(self.paths.sample_root, self.name + ".bowtie2.bam")
			self.peaks = os.path.join(self.paths.sample_root, self.name + "_peaks.bed")


When ``Looper`` parses your config file and creates ``Sample`` objects, it will:

	- check if any pipeline has a class extending ``Sample`` with the ``__library__`` attribute:
		
		- first by trying to import a ``pipelines`` module and checking the module pipelines;

		- if the previous fails, it will try appending the provided pipeline_dir to ``$PATH`` and checking the module files for pipelines;

	- if any of the above is successful, if will match the sample ``library`` with the ``__library__`` attribute of the classes to create extended sample objects.

	- if a sample cannot be matched to an extended class, it will be a generic ``Sample`` object.
