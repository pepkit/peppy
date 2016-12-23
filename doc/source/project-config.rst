Project config file
***************************************************


Details on project config file sections:


Project config section: metadata
"""""""""""""""""""""""""""""""""""""""""""

The `metadata` section contains paths to various parts of the project: the output directory (the parent directory), the results subdirector, the submission subdirectory (where submit scripts are stored), and pipeline scripts.Pointers to sample annotation sheets. This is the only required section.


Project config section: data_sources
"""""""""""""""""""""""""""""""""""""""""""

The `data_sources` section uses regex-like commands to point to different spots on the filesystem for data. The variables (specified by ``{variable}``) are populated first by shell environment variables, and then by sample attributes (columns in the sample annotation sheet).

Example:

.. code-block:: yaml

  data_sources:
    source1: /path/to/raw/data/{sample_name}_{sample_type}.bam
    source2: /path/from/collaborator/weirdNamingScheme_{external_id}.fastq

For more details, see :ref:`advanced-derived-columns`.

Project config section: derived_columns
"""""""""""""""""""""""""""""""""""""""""""
``derived_columns`` is just a simple list that tells looper which column names it should populate as data_sources. Corresponding sample attributes will then have as their value not the entry in the table, but the value derived from the string replacement of sample attributes specified in the config file.

Example:

.. code-block:: yaml

  derived_columns: [read1, read2, data_1]


For more details, see :ref:`advanced-derived-columns`.


Project config section: subprojects
"""""""""""""""""""""""""""""""""""""""""""""""

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




Project config section: pipeline_config
"""""""""""""""""""""""""""""""""""""""""""
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
"""""""""""""""""""""""""""""""""""""""""""
Sometimes a project requires tweaking a pipeline, but does not justify a completely separate _pipeline config_ file. For simpler cases, you can use the `pipeline_args` section, which lets you specify command-line parameters via the project config. This lets you fine-tune your pipeline, so it can run slightly differently for different projects.

Example:

.. code-block:: yaml

	pipeline_args:
	  rrbs.py:  # pipeline identifier: must match the name of the pipeline script
		# here, include all project-specific args for this pipeline
		"--flavor": simple
		"--flag": null


The above specification will now pass '--flavor=simple' and '--flag' whenever rrbs.py is invoked -- for this project only. This is a way to control (and record!) project-level pipeline arg tuning. The only keyword here is `pipeline_args`; all other variables in this section are specific to particular pipelines, command-line arguments, and argument values.


Project config section: track_configurations
"""""""""""""""""""""""""""""""""""""""""""""""
The `track_configurations` section is for making trackhubs.

.. warning::
	missing info here



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
