# Define a project

To use `looper` with your project, you must define your project using a standard project definition format. 
If you follow this format, then your project can be read not only to run pipelines, but also for these **other useful tasks:** 
  - Summarizing pipeline output
  - Analysis in R (using the [`pepr` package](http://github.com/pepkit/pepr))
  - Building UCSC track hubs

The format is simple and modular, so you only need to define the components you plan to use. You need to supply 2 files:
1. **Project config file** - a `yaml` file describing input and output file paths and other (optional) project settings
2. **Sample annotation sheet** - a `csv` file with 1 row per sample

### Quick example

In the simplest case, the **"project config" file** consists of just a few lines of `yaml`-formatted data. 
Here's an example:
```yaml
metadata:
  sample_annotation: /path/to/sample_annotation.csv
  output_dir: /path/to/output/folder
  pipeline_interfaces: path/to/pipeline_interface.yaml
```

Let's break that down:
- The `output_dir` key specifies where to save results. 
- The `pipeline_interfaces` key points to `looper`-compatible pipelines, as described on the [pipeline interface page](pipeline-interface.md). 
- The `sample_annotation` key points to another file, which is a tabular (e.g., CSV or TSV) file describing samples in the project. 

Here's a small example sample annotation file:
```CSV
sample_name,library,file
frog_1,RNA-seq,frog1.fq.gz
frog_2,RNA-seq,frog2.fq.gz
frog_3,RNA-seq,frog3.fq.gz
frog_4,RNA-seq,frog4.fq.gz
```

With those two simple files, you could run `looper`, which is fine for running a quick test on a few files. 
In practice, you'll probably want to use some of the more advanced features of `looper` by adding additional information 
to your project configuration file and sample annotation file.

For example, by default, your jobs will run serially on your local computer, where you're running `looper`. 
If you want to submit to a cluster resource manager (like SLURM or SGE), you just need to specify a `compute` section.

For more detail about additional features of sample annotation sheets, please see the [annotation sheet page](sample-annotation-sheet.md)
Below is information about additional features of the project config file.

### Project config section: `data_sources`
This section uses regex-like commands to point to different spots on the filesystem for data. 
The variables (specified by `{variable}`) are populated by sample attributes (columns in the sample annotation sheet). 
You can also use shell environment variables, like `${HOME}`, in these.

**Example**:

```yaml
data_sources:
  source1: /path/to/raw/data/{sample_name}_{sample_type}.bam
  source2: /path/from/collaborator/weirdNamingScheme_{external_id}.fastq
  source3: ${HOME}/{test_id}.fastq
```

For more details, see the [derived columns page](derived-columns.md).

### Project config section: `derived_attributes`
This section is a list that tells `looper` which column names it should populate as `data_sources`. 
Corresponding sample attributes will then have as their value not the entry in the table, 
but the value derived from the string replacement of sample attributes specified in the config file. 
This enables you to point to more than one input file for each sample (for example `read1` and `read2`).

**Example**:

```yaml
derived_columns: [read1, read2, data_1]
```

For more details, see the [derived columns page](derived-columns.md).

### Project config section: `implied_attributes`
This section lets you infer additional attributes, which can be useful for pipeline arguments.

**Example**:

```yaml
implied_columns:
  organism:
    human:
      genome: "hg38"
      macs_genome_size: "hs"
```

For more details, see the [implied columns page](implied-columns.md).

### Project config section: `constants`
This section lets you declare additional attributes, for each of which there's a single value across all samples. This is particularly useful when combined with ``derived_columns`` and/or ``implied_columns``, especially when there are many samples.

**Example**:

```yaml
constants:
  data_source: src
  read_type: SINGLE
  organism: mouse
```

### Project config section: `subprojects`
Subprojects are useful to define multiple similar projects within a single project config file. 
Under the subprojects key, you can specify names of subprojects, and then within those you can specify any project config variables that you want to overwrite for that particular subproject. 
Tell looper to load a particular subproject by passing `--sp subproject-name` on the command line.

**Example**:

```yaml
subprojects:
  diverse:
    metadata:
      sample_annotation: psa_rrbs_diverse.csv
  cancer:
    metadata:
      sample_annotation: psa_rrbs_intracancer.csv
```

This project would specify 2 subprojects that have almost the exact same settings, 
but change only their `metadata.sample_annotation` parameter (so, each subproject points to a different sample annotation sheet). 
Rather than defining two 99% identical project config files, you can use a subproject. 

### Project config section: `pipeline_config`
Occasionally, a particular project needs to run a particular flavor of a pipeline. 
Rather than creating an entirely new pipeline, you can parameterize the differences with a **pipeline config** file, 
and then specify that file in the **project config** file.

**Example**:

```yaml
pipeline_config:
  # pipeline configuration files used in project.
  # Key string must match the _name of the pipeline script_ (including extension)
  # Relative paths are relative to this project config file.
  # Default (null) means use the generic config for the pipeline.
  rrbs.py: null
  # Or you can point to a specific config to be used in this project:
  wgbs.py: wgbs_flavor1.yaml
```

This will instruct `looper` to pass `-C wgbs_flavor1.yaml` to any invocations of wgbs.py (for this project only). 
Your pipelines will need to understand the config file (which will happen automatically if you use pypiper).


### Project config section: `pipeline_args`
Sometimes a project requires tweaking a pipeline, but does not justify a completely separate **pipeline config** file. 
For simpler cases, you can use the `pipeline_args` section, which lets you specify command-line parameters via the project config. 
This lets you fine-tune your pipeline, so it can run slightly differently for different projects.

**Example**:

```yaml
pipeline_args:
  rrbs.py:  # pipeline identifier: must match the name of the pipeline script
    # here, include all project-specific args for this pipeline
    "--flavor": simple
    "--flag": null
```

For flag-like options (options without parameters), you should set the value to the yaml keyword `null`. 
Looper will pass the key to the pipeline without a value. 
The above specification will now (for *this project only*) pass `--flavor simple` and `--flag` whenever `rrbs.py` is run.
This is a way to control (and record!) project-level pipeline arg tuning. The only keyword here is `pipeline_args`; 
all other variables in this section are specific to particular pipelines, command-line arguments, and argument values.

### Project config section: `compute`
You can specify project-specific compute settings in a `compute` section, 
but it's often more convenient and consistent to specify this globally with a `pepenv` environment configuration. 
Instructions for doing so are at the [`pepenv` repository](https://github.com/pepkit/pepenv). 
If you do need project-specific control over compute settings (like submitting a certain project to a certain resource account), 
you can do this by specifying variables in a project config `compute` section, which will override global `pepenv` values for that project only.

```yaml
compute:
  partition: project_queue_name
```

### Project config section: `track_configurations`
***Warning***: The `track_configurations` section is for making UCSC trackhubs. 
This is a work in progress that is functional, but ill-documented, so for now it should be used with caution.

### Project config complete example
```yaml
metadata:
  # Relative paths are considered relative to this project config file.
  # Typically, this project config file is stored with the project metadata
  # sample_annotation: one-row-per-sample metadata
  sample_annotation: table_experiments.csv
  # sample_subannotation: input for samples with more than one input file
  sample_subannotation: table_merge.csv
  # compare_table: comparison pairs or groups, like normalization samples
  compare_table: table_compare.csv
  # output_dir: the parent, shared space for this project where results go
  output_dir: /fhgfs/groups/lab_bock/shared/projects/example
  # results and submission subdirs are subdirectories under parent output_dir
  # results: where output sample folders will go
  # submission: where cluster submit scripts and log files will go
  results_subdir: results_pipeline
  submission_subdir: submission
  # pipeline_interfaces: the pipeline_interface.yaml file or files for Looper pipelines
  # scripts (and accompanying pipeline config files) for submission.
  pipeline_interfaces: /path/to/shared/projects/example/pipeline_interface.yaml


data_sources:
  # Ideally, specify the ABSOLUTE PATH of input files using variable path expressions.
  # Alternatively, a relative path will be with respect to the project config file's folder.
  # Entries correspond to values in the data_source column in sample_annotation table.
  # {variable} can be used to replace environment variables or other sample_annotation columns.
  # If you use {variable} codes, you should quote the field so python can parse it.
  bsf_samples: "$RAWDATA/{flowcell}/{flowcell}_{lane}_samples/{flowcell}_{lane}#{BSF_name}.bam"
  encode_rrbs: "/path/to/shared/data/encode_rrbs_data_hg19/fastq/{sample_name}.fastq.gz"


implied_columns:
# supported genomes/transcriptomes and organism -> reference mapping
organism:
  human:
    genome: hg38
    transcriptome: hg38_cdna
  mouse:
    genome: mm10
    transcriptome: mm10_cdna

pipeline_config:
  # pipeline configuration files used in project.
  # Default (null) means use the generic config for the pipeline.
  rrbs: null
  # Or you can point to a specific config to be used in this project:
  # rrbs: rrbs_config.yaml
  # wgbs: wgbs_config.yaml
  # cgps: cpgs_config.yaml
```
