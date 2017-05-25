Project models
****************************************

Looper uses object oriented programming (OOP) under the hood. This means that concepts like a sample to be processed or a project are modeled as objects in Python. These project objects are actually useful outside of looper. At some point, we will likely separate the project objects into their own Python package, but for now, you can use them independently of looper, even though they are embedded within the looper package. They are functionally independent.

If you define your project using looper's :doc:`standardized project definition format <define-your-project>` , you can use the project models to instantiate an in memory representation of your project and all of its samples, without using looper. Here is a brief description of how you would do this.

.. code-block:: python

	from looper import models

	my_project = models.Project("path/to/project_config.yaml")
	my_samples = my_project.samples

Once you have your project and samples in your Python session, the possibilities are endless. This is the way looper reads your project; looper uses these objects to loop through each sample and submit pipelines for each. You could just as easily use these objects for other purposes; for example, one way we use these objects is for post-pipeline processing. After we use looper to run each sample through its pipeline, we can load the project and it sample objects into an analysis session, where we do comparisons across samples. We are also working on on R package that will similarly read this standardized project definition format, giving you access to the same information within R.

This is a work in progress, but you can find more information and examples in the `API <api.html>`_.



.. _extending-sample-objects:

Extending sample objects
****************************************

By default we use `generic models <https://github.com/epigen/looper/tree/master/looper/models.py>`_ (see the `API <api.html>`_ for more) to handle samples in Looper, but these can also be reused in other contexts by importing ``models`` or by means of object serialization through YAML files.

Since these models provide useful methods to interact, update, and store attributes in the objects (most nobly *samples* - ``Sample`` object), a useful use case is during the run of a pipeline: pipeline scripts can extend ``Sample`` objects with further attributes or methods.

Example:

You want a convenient yet systematic way of specifying many file paths for several samples depending on the type of NGS sample you're handling: a ChIP-seq sample might have at some point during a run a peak file with a certain location, while a RNA-seq sample will have a file with transcript quantifications. Both paths to the files exist only for the respective samples, will likely be used during a run of a pipeline, but also during some analysis later on.
By working with ``Sample`` objects that are specific to each file type, you can specify the location of such files only once during the whole process and later access them "on the fly".


**To have** ``Looper`` **create a ``Sample`` object specific to your data type, simply import the base** ``Sample`` **object from** ``models``, **and create a** ``class`` **that inherits from it that has an** ``__library__`` **attribute:**


.. code-block:: python

	# atacseq.py

	from models import Sample

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
