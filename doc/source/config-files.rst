
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

Looper requires only one argument: a *project config file* that specifies information about your project. The project config file describes all *project-specific variables*. Its primary purpose as as input to Looper, which will submit jobs as appropriate for each sample in the project. But it is also read by other tools, including:

  - Looper (primary purpose)
  - ``make_trackhubs`` scripts to produce web accessible results
  - stats summary scripts
  - analysis scripts requiring pointers to metadata, results, and other options.


 Here's an example. Additional fields can be added as well.

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



Details on project config file sections:


Project config section: paths
^^^^^^^^^^^^^^^^^^^^

The `paths` section contains paths to various parts of the project: the output directory (the parent directory), the results subdirector, the submission subdirectory (where submit scripts are stored), and pipeline scripts.

Project config section: metadata
^^^^^^^^^^^^^^^^^^^^

Pointers to sample annotation sheets.

Project config section: pipeline_config
^^^^^^^^^^^^^^^^^^^^
Occasionally, a particular project needs to run a particular flavor of a pipeline. Rather than creating an entirely new pipeline, you can parameterize the differences with a _pipeline config_ file, and then specify that file in the _project config_ file.

Example:

.. code-block:: yaml

	pipeline_config:
	  # pipeline configuration files used in project.
	  # Key string must match the _name of the pipeline script_ (including extension)
	  # Relative paths are relative to this project config file.
	  # Default (null) means use the generic config for the pipeline.
	  rrbs.py: null
	  # Or you can point to a specific config to be used in this project:
	  wgbs.py: wgbs_flavor1.yaml


This will instruct `looper` to pass `-C wgbs_flavor1.yaml` to any invocations of wgbs.py (for this project only). Your pipelines will need to understand the config file (which will happen automatically if you use pypiper).


Project config section: pipeline_args
^^^^^^^^^^^^^^^^^^^^

Sometimes a project requires tweaking a pipeline, but does not justify a completely separate _pipeline config_ file. For simpler cases, you can use the `pipeline_args` section, which lets you specify command-line parameters via the project config. This lets you fine-tune your pipeline, so it can run slightly differently for different projects.

Example:

.. code-block:: yaml

	pipeline_args:
	  rrbs.py:  # pipeline identifier: must match the name of the pipeline script
		# here, include all project-specific args for this pipeline
		"--flavor": simple
		"--flag": null


The above specification will now pass '--flavor=simple' and '--flag' whenever rrbs.py is invoked -- for this project only. This is a way to control (and record!) project-level pipeline arg tuning. The only keyword here is `pipeline_args`; all other variables in this section are specific to particular pipelines, command-line arguments, and argument values.

Project config section: compute
^^^^^^^^^^^^^^^^^^^^
For each iteration, `looper` will create one or more submission scripts for that sample. The `compute` specifies how jobs these scripts will be both produced and run.  This makes it very portable and easy to change cluster management systems, or to just use a local compute power like a laptop or standalone server, by just changing the two variables in the `compute` section.

Example:

.. code-block:: yaml

	compute:
	  submission_template: pipelines/templates/slurm_template.sub
	  submission_command: sbatch


There are two sub-parameters in the compute section. First, `submission_template` is a (relative or absolute) path to the template submission script. This is a template with variables (encoded like `{VARIABLE}`), which will be populated independently for each sample as defined in `pipeline_inteface.yaml`. The one variable `{CODE}` is a reserved variable that refers to the actual python command that will run the pipeline. Otherwise, you can use any variables you define in your `pipeline_interface.yaml`.

Second, the `submission_command` is the command-line command that `looper` will prepend to the path of the produced submission script to actually run it (`sbatch` for SLURM, `qsub` for SGE, `sh` for localhost, etc).

In [`templates/`](templates/) are examples for submission templates for [SLURM](templates/slurm_template.sub), [SGE](templates/sge_template.sub), and [local runs](templates/localhost_template.sub). For a local run, just pass the script to the shell with `submission_command: sh`. This will cause each sample to run sequentially, as the shell will block until the run is finished and control is returned to `looper` for the next iteration.


Project config section: data_sources
^^^^^^^^^^^^^^^^^^^^

The `data_sources` can use regex-like commands to point to different spots on the filesystem for data. The variables (specified by `{variable}`) are populated first by shell environment variables, and then by variables (columns) named in the project sample annotation sheet.

The idea is: don't put absolute paths to files in your annotation sheet. Instead, specify a data source and then provide a regex in the config file. This way if your data changes locations (which happens more often than we would like), or you change servers, you just have to change the config file and not update paths in the annotation sheet. This makes the whole project more portable.

Project config section: track_configurations
^^^^^^^^^^^^^^^^^^^^
The `track_configurations` section is for making trackhubs (see below).

.. warning::
	missing info here


However, there are more options. See the [project config template](examples/example_project_config.yaml) for a more comprehensive list of options or the [microtest config template](examples/microtest_project_config.yaml) for a ready-to-run example. You can try out the microtest example like this (the `-d` option indicates a dry run, meaning submit scripts are created but not actually submitted).
```
./pipelines/looper.py -c pipelines/examples/microtest_project_config.yaml -d
```


Project config section: subprojects
^^^^^^^^^^^^^^^^^^^^

Subprojects are useful to define multiple similar projects within a single project config file. Under the subprojects key, you can specify names of subprojects, and then underneath of of these you can specify any project config variables that you want to overwrite for that particular subproject.

For example:

.. code-block:: yaml

	subprojects:
	  diverse:
		metadata:
		  sample_annotation: psa_rrbs_diverse.csv
	  cancer:
		metadata:
		  sample_annotation: psa_rrbs_intracancer.csv

This project would specify 2 subprojects that have almost the exact same settings, but change only their metadata/sample_annotation parameter. Rather than defining two 99% identical project config files, you can use a subproject. 


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
pipeline. For each pipeline (defined by the filename of the script itself), you specify three components: ``name``, ``arguments``, and ``resources``.

.. code-block:: yaml

	pipeline_script.py:  # this is variable (script filename)
	  name: value  # used for assessing pipeline flags (optional)
	  looper_args: True
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

``arguments`` - the key corresponds verbatim to the string that will be passed on the command line to the pipeline. The value corresponds to an attribute of the sample, which will be derived from the sample_annotation csv file (in other words, it's a column name of your sample annotation sheet).

In addition to arguments you specify here, you may include ``looper_args: True`` and then looper will automatically add arguments for:

- **-C**: config_file (the pipeline config file specified in the project config file; or the default config file, if it exists)
- **-P**: cores (the number of cores specified by the resource package chosen)
- **-M**: mem (the memory limit)

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
