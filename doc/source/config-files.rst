
Configuration files
=========================

pipelines uses `YAML <http://www.yaml.com/>`_ configuration files (config files for short) to describe how a project is going to be run.

However, there are three types of config files (all yaml format) that are used by ``pipelines``:

-   :ref:`project-config-file`: This file is specific to each project and contains information about the project's metadata, where the processed sample files are going to exist and other variables that allow to configure the pipeline runs for this project.
-   :ref:`pipeline-config-file`: These files are specific to each pipeline and describe variables, options and paths that the pipeline needs to know to run.
-   :ref:`looper-config-files`: These are and tell the Looper which pipelines exist, how to map each sample to each pipeline and how to manage resources needed to run each sample.

.. note::
	As a user of the pipelines you will only have to deal with the :ref:`project-config-file`.

.. _project-config-file:

Project config file
-------------------
The project config file describes all *project-specific variables*. Its primary purpose as as input to Looper, which will submit jobs as appropriate
for each sample in the project. But it is also read by other tools, including:

  - Looper (primary purpose)
  - ``make_trackhubs`` scripts to produce web accessible results
  - stats summary scripts
  - analysis scripts requiring pointers to metadata, results, and other options.


Here's the structure of the project config file with all fields which are recognised. Additional fields can be added as well.

.. code-block:: yaml

	paths:
	  # output_dir: the parent, shared space for this project where results go
	  output_dir: /fhgfs/groups/lab_bock/shared/projects/example
	  # results and submission subdirs are subdirectories under parent output_dir
	  # results: where output sample folders will go
	  # submission: where cluster submit scripts and log files will go
	  results_subdir: results_pipeline
	  submission_subdir: submission
	  # pipelines_dir: the directory where the Looper will find pipeline
	  # scripts (and accompanying pipeline config files) for submission.
	  pipelines_dir: /fhgfs/groups/lab_bock/shared/projects/example/pipelines

	metadata:
	  # Relative paths are considered relative to this project config file.
	  # Typically, this project config file is stored with the project metadata
	  # sample_annotation: one-row-per-sample metadata
	  sample_annotation: table_experiments.csv
	  # merge_table: input for samples with more than one input file
	  merge_table: table_merge.csv
	  # compare_table: comparison pairs or groups, like normalization samples
	  compare_table: table_compare.csv

	data_sources:
	  # specify the ABSOLUTE PATH of input files using variable path expressions
	  # entries correspond to values in the data_source column in sample_annotation table
	  # {variable} can be used to replace environment variables or other sample_annotation columns
	  # If you use {variable} codes, you should quote the field so python can parse it.
	  bsf_samples: "{RAWDATA}{flowcell}/{flowcell}_{lane}_samples/{flowcell}_{lane}#{BSF_name}.bam"
	  encode_rrbs: "/fhgfs/groups/lab_bock/shared/projects/epigenome_compendium/data/encode_rrbs_data_hg19/fastq/{sample_name}.fastq.gz"

	genomes:
	  # supported genomes and organism -> genome mapping
	  human: hg19
	  mouse: mm10

	transcriptomes:
	  # supported transcriptomes and organism -> transcriptome mapping
	  human: hg19_cdna
	  mouse: mm10_cdna

	pipeline_config:
	  # pipeline configuration files used in project.
	  # Default (null) means use the generic config for the pipeline.
	  rrbs: null
	  # Or you can point to a specific config to be used in this project:
	  # rrbs: rrbs_config.yaml
	  # wgbs: wgbs_config.yaml
	  # cgps: cpgs_config.yaml

	compute:
	  # submission_template: the submission form which will be replaced with compute resource parameters
	  # Use this to change your cluster manager (SLURM, SGE, LFS, etc)
	  # Relative paths are relative to the pipelines_dir
	  submission_template: templates/slurm_template.sub
	  submission_command: sbatch
	  # To run on the localhost:
	  #submission_template: templates/localhost_template.sub
	  #submission_command: sh

	trackhubs:
	  trackhub_dir: /data/groups/lab_bock/public_html/nsheffield/b8ab8bs9b8d/ews_rrbs/
	  url: http://www.whatever.com/
	  matrix_x: cell_type
	  matrix_y: cell_count
	  sort_order: cell_type=+
	  parent_track_name: ews_rrbs
	  visibility: dense
	  hub_name: ews_hub
	  short_label_column: sample_name
	  email: nathan@code.databio.org


Data sources section
^^^^^^^^^^^^^^^^^^^^
The data sources can use regex-like commands to point to different spots on the filesystem for data. The variables (specified by ``{variable}``) are populated in this order:

.. warning::
	missing info here

The idea is: don't put absolute paths to files in your annotation sheet. Instead, specify a data source and then provide a regex in the config file. This way if your data changes locations (which happens more often than we would like), or you change servers, you just have to change the config file and not update paths in the annotation sheet. This makes the whole project more portable.

The track_configurations section is for making trackhubs (see below).


Subprojects
^^^^^^^^^^^^^^^^^^^^

.. warning::
	This feature is not implemented yet.



.. _pipeline-config-file:

Pipeline config file
--------------------

.. note::
	This section is only relevant if you're developing Looper or a pipeline.

In this yaml file, the developer of a pipeline records any information the pipeline needs to run that is not related to the Sample being processed. Relevant yaml sections are ``tools``, ``resources`` and ``parameters``, for consistensy across ppipelines, but the developer has the freedom to add other sections/variables as needed.

Other information related to a specific run (*e.g.* cpus and memory available) should ideally be passed as command-line arguments.

Pipeline config files should be named as the pipeline with the suffix ``.yaml`` and reside in the same directory as the pipeline code.


Example:

.. code-block:: yaml

	tools:
	  # absolute paths to required tools
	  java:  /home/user/.local/tools /home/user/.local/tools/java
	  trimmomatic:  /home/user/.local/tools/trimmomatic.jar
	  fastqc:  fastqc
	  samtools:  samtools
	  bsmap:  /home/user/.local/tools/bsmap
	  split_reads:  /home/user/.local/tools/split_reads.py  # split_reads.py script; distributed with this pipeline

	resources:
	  # paths to reference genomes, adapter files, and other required shared data
	  resources: /data/groups/lab_bock/shared/resources
	  genomes: /data/groups/lab_bock/shared/resources/genomes/
	  adapters: /data/groups/lab_bock/shared/resources/adapters/

	parameters:
	  # parameters passed to bioinformatic tools, subclassed by tool

	  trimmomatic:
	    quality_encoding: "phred33"
	    threads: 30
	    illuminaclip:
	      adapter_fasta: "/home/user/.local/tools/resources/cpgseq_adapter.fa"
	      seed_mismatches: 2
	      palindrome_clip_threshold: 40
	      simple_clip_threshold: 7
	    slidingwindow:
	      window_size: 4
	      required_quality: 15
	    maxinfo:
	      target_length: 17
	      strictness: 0.5
	    minlen:
	      min_length: 17

	  bsmap:
	    seed_size: 12
	    mismatches_allowed_for_background: 0.10
	    mismatches_allowed_for_left_splitreads: 0.06
	    mismatches_allowed_for_right_splitreads: 0.00
	    equal_best_hits: 100
	    quality_threshold: 15
	    quality_encoding: 33
	    max_number_of_Ns: 3
	    processors: 8
	    random_number_seed: 0
	    map_to_strands: 0


.. _looper-config-files:

Looper config files
-------------------

.. note::
	This section is only relevant if you're developing Looper or a pipeline.


Looper pipeline interface configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The pipeline interface file describes how the looper, which submits jobs, knows what resources to request for a pipeline, and what arguments to pass to the
pipeline. For each pipeline, you specify two components: an arguments list, a resources list, and optionally a pipeline name like so:

.. code-block:: yaml

	pipeline_script:
	  name: value  # used for assessing pipeline flags (optional)
	  arguments:
	    "-k" : value
	    "--key2" : value
	    "--key3" : null # value-less argument flags
	  resources:
	    default:
	      file_size: "0"
	      cores: "4"
	      mem: "6000"
	      time: "2-00:00:00"
	      partition: "longq"
	    resource_package_name:
	      file_size: "0"
	      cores: "4"
	      mem: "6000"
	      time: "2-00:00:00"
	      partition: "longq"

``arguments`` - the key corresponds verbatim to the string that will be passed on the command line to the pipeline. The value corresponds to an attribute of the sample, which will be derived from the sample_annotation csv file.

The looper will automatically add arguments for:

- **-c**: config_file (the pipeline config file specified in the project config file; or the default config file, if it exists)
- **-p**: cores (the number of cores specified by the resource package chosen)

``resources`` - You must define at least 1 option named 'default' with ``file_size`` = 0. Add as many additional resource sets as you want, with any names.
The looper will determine which resource package to use based on the ``file_size`` of the input file. It will select the lowest resource package whose ``file_size`` attribute does not exceed the size of the input file.

Example:

.. code-block:: yaml

	rrbs.py:
	  name: RRBS
	  looper_args: True
	  arguments:
	    "--sample-name": sample_name
	    "--genome": genome
	    "--input": data_path
	    "--single-or-paired": read_type
	  resources:
	    default:
	      file_size: "0"
	      cores: "4"
	      mem: "4000"
	      time: "2-00:00:00"
	      partition: "longq"
	    high:
	      file_size: "4"
	      cores: "6"
	      mem: "4000"
	      time: "2-00:00:00"
	      partition: "longq"

	rnaBitSeq.py:
	  looper_args: True
	  arguments:
	    "--sample-name": sample_name
	    "--genome": transcriptome
	    "--input": data_path
	    "--single-or-paired": read_type

	  resources:
	    default:
	      file_size: "0"
	      cores: "6"
	      mem: "6000"
	      time: "2-00:00:00"
	      partition: "longq"

	atacseq.py:
	  arguments:
	    "--sample-yaml": yaml_file
	    "-I": sample_name
	    "-G": genome
	  looper_args: True
	  resources:
	    default:
	      file_size: "0"
	      cores: "4"
	      mem: "8000"
	      time: "08:00:00"
	      partition: "shortq"



Looper protocol mapping configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The protocol mappings explains how the Looper should map from a sample protocol (like RNA-seq) to a particular pipeline (like rnaseq.py), or group of pipelines.
You can map multiple pipelines to a single protocol if you want samples of a type to kick of more than one pipeline run

The basic format for pipelines run simultaneously is:
``PROTOCOL: pipeline1 [, pipeline2, ...]``

Use semi-colons to indicate dependency.

.. warning::
	Pipeline dependency is not implemented yet.

Rules:

- **Basic case:** one protocol maps to one pipeline: ``RNA-seq: rnaseq.py``
- **Case:** one protocol maps to multiple independent pipelines: ``Drop-seq: quality_control.py, dropseq.py``
- **Case:** a protocol runs one pipeline which depends on another: ``WGBSNM: first;second;third;(fourth, fifth)``


Examples:

.. code-block:: yaml

	CORE: >
	  wgbs.py,
	  rnaBitSeq.py --core-seq;
	  rnaTopHat.py --core-seq
	RRBS: rrbs.py
	WGBS: wgbs.py
	EG: wgbs.py
	WGBSQC: >
	  wgbs.py;
	  (nnm.py, pdr.py)
	SMART:  >
	  rnaBitSeq.py -f;
	  rnaTopHat.py -f
	SMART-seq:  >
	  rnaBitSeq.py -f;
	  rnaTopHat.py -f
	ATAC: atacseq.py
	ATAC-SEQ: atacseq.py
	CHIP: chipseq.py
	CHIP-SEQ: chipseq.py
	CHIPMENTATION: chipseq.py
	STARR: starrseq.py
	STARR-SEQ: starrseq.py
