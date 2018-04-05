Project models
****************************************

``peppy`` models projects and samples as objects in Python.

.. code-block:: python

	import peppy

	my_project = peppy.Project("path/to/project_config.yaml")
	my_samples = my_project.samples

Once you have your project and samples in your Python session, the possibilities are endless. For example, one way we use these objects is for post-pipeline processing. After we use looper to run each sample through its pipeline, we can load the project and it sample objects into an analysis session, where we do comparisons across samples.

**Exploration:**

To interact with the various ``models`` and become acquainted with their
features and behavior, there is a lightweight module that provides small
working versions of a couple of the core objects. Specifically, from
within the ``tests`` directory, the Python code in the ``tests.interactive``
module can be copied and pasted into an interpreter. This provides a
``Project`` instance called ``proj`` and a ``PipelineInterface`` instance
called ``pi``. Additionally, this provides logging information in great detail,
affording visibility into some what's happening as the ``models`` are created
and used.


.. _extending-sample-objects:

Extending sample objects
****************************************

By default we use `generic models <https://github.com/epigen/looper/tree/master/looper/models.py>`_ (see the `API <api.html>`_ for more) to handle samples in Looper, but these can also be reused in other contexts by importing ``models`` or by means of object serialization through YAML files.

Since these models provide useful methods to store, update, and read attributes in the objects created from them (most notably a *sample* - ``Sample`` object), a useful use case is during the run of a pipeline: a pipeline can create a more tailored ``Sample`` model, adding attributes or providing altered or additional methods.

**Example:**

You have several samples, of different experiment types,
each yielding different varieties of data and files. For each sample of a given
experiment type that uses a particular pipeline, the set of file path types
that are relevant for the initial pipeline processing or for downstream
analysis is known. For instance, a peak file with a certain genomic location
will likely be relevant for a ChIP-seq sample, while a transcript
abundance/quantification file will probably be used when working with a RNA-seq
sample. This common situation, in which one or more file types are specific
to a pipeline and analysis both benefits from and is amenable to a bespoke
``Sample`` *type*. Rather than working with a base ``Sample`` instance and
repeatedly specifying paths to relevant files, those locations can be provided
just once, stored in an instance of the custom ``Sample`` *type*, and later
used or modified as needed by referencing a named attribute on the object.
This approach can dramatically reduce the number of times that a full filepath
must be accurately keyed and thus saves some typing time. More significant,
it's likely to save time lost to diagnostics of typo-induced errors. The most
rewarding aspect of employing the ``Sample`` extension strategy, though, is
a drastic readability boost. As the visual clutter of raw filepaths clears,
code readers can more clearly focus on questions of *what* a filepath points
to and *how* it's being used, rather than on the path itself.

**Logistics:**

It's the specification of *both an experiment or data type* ("library" or
"protocol") *and a pipeline with which to process that input type* that
``Looper`` uses to determine which type of ``Sample`` object(s) to create for
pipeline processing and analysis (i.e., which ``Sample`` extension to use).
There's a pair of symmetric reasons for this--the relationship between input
type and pipeline can be one-to-many, in both directions. That is, it's
possible for a single pipeline to process more than one input type, and a
single input type may be processed by more than one pipeline.

There are a few different ``Sample`` extension scenarios. Most basic is the
one in which an extension, or *subtype*, is neither defined nor needed--the
pipeline author does not provide one, and users do not request one. Almost
equally effortless on the user side is the case in which a pipeline author
intends for a single subtype to be used with her pipeline. In this situation,
the pipeline author simply implements the subtype within the pipeline module,
and nothing further is required--of the pipeline author or of a user! The
``Sample`` subtype will be found within the pipeline module, and the inference
will be made that it's intended to be used as the fundamental representation
of a sample within that pipeline. If a pipeline author extends the base
``Sample`` type in the pipeline module, it's likely that the pipeline's proper
functionality depends on the use of that subtype. In a rare case, though, it
may be desirable to use the base ``Sample`` type even if the pipeline author
has provided a more customized version with her pipeline. To favor the base
``Sample`` over the tailored one created by a pipeline author, the user may
simply set ``sample_subtypes`` to ``null`` in his own version of the pipeline
interface, either for all types of inpute to that pipeline, or for just a
subset of them. Read on for further information.


.. code-block:: python

	# atacseq.py

	from models import Sample

	class ATACseqSample(Sample):
		"""
		Class to model ATAC-seq samples based on the generic Sample class.

		:param series: Pandas `Series` object.
		:type series: pandas.Series
		"""

		def __init__(self, series):
			if not isinstance(series, pd.Series):
				raise TypeError("Provided object is not a pandas Series.")
			super(ATACseqSample, self).__init__(series)
			self.make_sample_dirs()

		def set_file_paths(self, project=None):
			"""Sets the paths of all files for this sample."""
			# Inherit paths from Sample by running Sample's set_file_paths()
			super(ATACseqSample, self).set_file_paths(project)

			self.fastqc = os.path.join(self.paths.sample_root, self.name + ".fastqc.zip")
			self.trimlog = os.path.join(self.paths.sample_root, self.name + ".trimlog.txt")
			self.fastq = os.path.join(self.paths.sample_root, self.name + ".fastq")
			self.trimmed = os.path.join(self.paths.sample_root, self.name + ".trimmed.fastq")
			self.mapped = os.path.join(self.paths.sample_root, self.name + ".bowtie2.bam")
			self.peaks = os.path.join(self.paths.sample_root, self.name + "_peaks.bed")


To leverage the power of a ``Sample`` subtype, the relevant model is the
``PipelineInterface``. For each pipeline defined in the ``pipelines`` section
of ``pipeline_interface.yaml``, there's accommodation for a ``sample_subtypes``
subsection to communicate this information. The value for each such key may be
either a single string or a collection of key-value pairs. If it's a single
string, the value is the name of the class that's to be used as the template
for each ``Sample`` object created for processing by that pipeline. If instead
it's a collection of key-value pairs, the keys should be names of input data
types (as in the ``protocol_mapping``), and each value is the name of the class
that should be used for each sample object of the corresponding key*for that
pipeline*. This underscores that it's the *combination of a pipeline and input
type* that determines the subtype.


.. code-block:: yaml

    # Content of pipeline_interface.yaml

    protocol_mapping:
        ATAC: atacseq.py

    pipelines:
        atacseq.py:
            ...
            ...
            sample_subtypes: ATACseqSample
            ...
            ...
        ...
        ...


If a pipeline author provides more than one subtype, the ``sample_subtypes``
section is needed to select from among them once it's time to create
``Sample`` objects. If multiple options are available, and the
``sample_subtypes`` section fails to clarify the decision, the base/generic
type will be used. The responsibility for supplying the ``sample_subtypes``
section, as is true for the rest of the pipeline interface, therefore rests
primarily with the pipeline developer. It is possible for an end user to
modify these settings, though.

Since the mechanism for subtype detection is ``inspect``-ion of each of the
pipeline module's classes and retention of those which satisfy a subclass
status check against ``Sample``, it's possible for pipeline authors to
implement a class hierarchy with multi-hop inheritance relationships. For
example, consider the addition of the following class to the previous example
of a pipeline module ``atacseq.py``:


.. code-block:: python

    class DNaseSample(ATACseqSample):
        ...


In this case there are now two ``Sample`` subtypes available, and more
generally, there will necessarily be multiple subtypes available in any
pipeline module that uses a subtype scheme with multiple, serial inheritance
steps. In such cases, the pipeline interface should include an unambiguous
``sample_subtypes`` section.


.. code-block:: yaml

    # Content of pipeline_interface.yaml

    protocol_mapping:
        ATAC: atacseq.py
        DNase: atacseq.py

    pipelines:
        atacseq.py:
            ...
            ...
            sample_subtypes:
                ATAC: ATACseqSample
                DNase: DNaseSample
            ...
            ...
        ...
        ...
