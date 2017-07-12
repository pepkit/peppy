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

Since these models provide useful methods to store, update, and read attributes in the objects created from them (most notably a *sample* - ``Sample`` object), a useful use case is during the run of a pipeline: a pipeline can create a more tailored ``Sample`` model, adding attributes or providing altered or additional methods.

**Example:**

You have several samples, of multiple different experiment *types*,
each yielding different *types* of data and files. For each sample of a given
experiment type that uses a particular pipeline, the set of file path types
that are relevant for the initial pipeline processing or for downstream
analysis is known. For instance, a peak file with a certain genomic location
is likely to be relevant for a ChIP-seq sample, while a transcript
abundance/quantification file will probably be used when working with a RNA-seq
sample. This common environment, in which one or more file types are specific
to a pipeline or analysis for a particular experiment type, is not only
amenable to a extension of the base ``Sample`` to a more bespoke ``Sample``
*type*, but it's also especially likely to be made more pleasant by doing so.
Rather than working with a generic, base ``Sample`` instance and needing to
repeatedly specify the paths to relevant files, those locations can be
specified just once, stored in an instance of the custom ``Sample`` *type*,
and then later used or modified as needed, referencing a named attribute on
the object. As this approach can dramatically reduce the number of times that
a full filepath must be accurately typed, it will certainly save a modest
amount of simple typing time; more significantly, it's likely to save time lost
to diagnostics of typo-induced errors. The most rewarding aspect of employing
the ``Sample`` extension strategy, however, is the potential for a drastic
readability boost; as the visual clutter of raw filepaths clears, code readers
are able to more clearly focus on the content and use of the data pointed to
by filepath rather than the path itself.

**Logistics:**

It's the specification of *both an experiment or data type* ("library" or
"protocol") *and a pipeline with which to process that input type* that
``Looper`` uses to determine which type of ``Sample`` object(s) to create for
pipeline processing and analysis (i.e., which ``Sample`` extension to use).
There's a pair of symmetric reasons for this--the relationship between input
type and pipeline can be one-to-many, in both directions. That is, it's
possible for a single pipeline to process more than one input type, and a
single input type may be processed by more than one pipeline.

There are a few different ``Sample`` extension scenarios, each of which
``Looper`` can interpret and handle. The most basic is the one in which
a ``Sample`` extension, or *subtype*, is neither defined nor needed--the
pipeline author does not provide such an implementation, and users do not
request a subtype in a pipeline interface. Almost equally effortless on the
user side is the case in which a pipeline author requires or otherwise intends
for a single ``Sample`` subtype to be used with her pipeline. In this situation,
the pipeline author simply implements the subtype within the pipeline module,
and nothing further is required--neither of the pipeline author nor of a
pipeline user! ``Looper`` will find the ``Sample`` subtype within the pipeline
module and infer that it's intended to be used as the fundamental object
representation of a sample within that pipeline. If a pipeline author extends
the base ``Sample`` type in the pipeline module, it's likely for the
pipeline's proper functionality to depend on the use of that ``Sample`` subtype.
In a rare case, though, it may be both possible and desirable to use the base
``Sample`` type even if the pipeline author has defined a bespoke type with
her pipeline. To favor the base ``Sample`` over the tailored one created by a
pipeline author--whether or not that custom type is declared in the
``sample_subtypes`` section of the pipeline interface--the user may simply
set ``sample_subtypes`` to ``null`` in his own version of the pipeline
interface, either for all input types to that pipeline, or for just a subset
of them. Read on for further information.

When either the pipeline author or a user wants to does want to leverage the
power of a ``Sample`` extension for one or more types of input data or
experiments, the relevant ``Looper`` component is the pipeline interface.
For each pipeline defined within in, the ``pipelines`` section of
``pipeline_interface.yaml`` accommodates a section ``sample_subtypes`` to
communicate this information. The value for this key may be either a single
string or a collection of key-value pairs. If it's a single string, the value
is the name of the class that is to be used as the template for each ``Sample``
object created for processing by that pipeline. If it's a collection of
key-value pairs, the keys should be names of input data types (experiment
protocols, or data/library types, as in the ``protocol_mapping``), and each
value is the name of the class that should be used for each sample object
of the corresponding key *for that pipeline*. This underscores the fact that
it's the *combination of a pipeline and input type* that determines the
desired ``Sample`` subtype.

If a pipeline author provides more than one ``Sample`` extension, ``Looper``
relies on the ``sample_subtypes`` section to select the proper subtype when
it's time to create a ``Sample`` object. If multiple options are available,
and the ``sample_subtypes`` section fails to disambiguate the decision,
``Looper`` will resort to the base/generic ``Sample``. The responsibility
for supplying the ``sample_subtypes`` section, as is true for the rest of the
pipeline interface, therefore rests primarily with the pipeline developer. It
is possible for an end user to modify these settings, though.

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
