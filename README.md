# Pipelines

This repository contains two separate components.

First, pipelines, which consist of:
  1. pipeline scripts (written in python)
  2. associated scripts used by the pipelines (in a subdirectory)

Second, this repository _also contains `looper.py`, a pipeline submission engine_ that parses sample inputs and submits pipelines for each sample. It also has several accompanying scripts that use the same infrastructure to do other processing for projects.

These pipelines use [`pypiper`](https://github.com/epigen/pypiper/) (see the corresponding repository).

# Installing

### Option 1 (clone the repository)

1. Install [`pypiper`](https://github.com/epigen/pypiper/).
2. Clone this repository.
```bash
git clone git@github.com:epigen/pipelines.git
```
3. Produce a config file (it just has a bunch of paths).
4. Go!

If you are just _using a pipeline_ in a project, and you are not _developing the pipeline_, you should treat this cloned repo as read-only, frozen code, which should reside in a shared project workspace. There should be only one clone for the project, to avoid running data under changing pipeline versions (you should not pull any pipeline updates unless you plan to re-run the whole thing).

### Option 2 (install the packages)

```
pip install https://github.com/epigen/pypiper/zipball/master
pip install https://github.com/epigen/pipelines/zipball/master
```

You will have all runnable pipelines and accessory scripts (from [`scripts/`](scripts/), see below) in your `$PATH`.

# Running pipelines

We use the Looper (`looper.py`) to run pipelines. This just requires a yaml format config file passed as an argument, which contains all the settings required.

This can, for example, submit each job to SLURM (or SGE, or run them locally).

```bash
python ~/code/pipelines/looper.py -c metadata/config.yaml
```
or

```bash
looper -c metadata/config.yaml
```
# Looper at a glance

Looper is a _project management system_ which defines and implements a grammar of projects. In other words, it does two things: 1) it specifies a format for describing a computational biology project and the samples that accompany it; and 2) it implements software for reading that description to process each sample in the project.

Some of the benefits of using `looper` are:

1. Portability. You can easily switch from a local computer to a cluster using SLURM or SGE or any other system.
2. Standardization. Samples are all run the same way, and results are all collected in the sample place.
3.

# Getting started

You define a project by creating a _project config file_, which is a yaml file with certain defined parameters. You describe locations for where to find data, provide an annotation of all samples included in the project, and make sure you record how to connect a sample type to the pipeline that should process it.

# Project config files

Looper requires only one argument: a _project config file_ that specifies information about your project. Here's an example:

```yaml
paths:
  # output_dir: ABSOLUTE PATH to the parent, (shared) space where project results go
  output_dir: /scratch/lab_bock/shared/projects/microtest
  # pipelines_dir: ABSOLUTE PATH the directory with the pipeline repository
  pipelines_dir: /scratch/lab_bock/shared/code/pipelines

metadata:
  # Elements in this section can be absolute or relative.
  # Typically, this project config file is stored with the project metadata, so
  # relative paths are considered relative to this project config file.
  # sample_annotation: one-row-per-sample metadata
  sample_annotation: microtest_sample_annotation.csv
  # merge_table: input for samples with more than one input file
  merge_table: microtest_merge_table.csv

data_sources:
  # specify the ABSOLUTE PATH of input files using variable path expressions
  # entries correspond to values in the data_source column in sample_annotation table
  # {variable} can be used to replace environment variables or other sample_annotation columns
  # If you use {variable} codes, you should quote the field so python can parse it.
  bsf_samples: "{RAWDATA}{flowcell}/{flowcell}_{lane}_samples/{flowcell}_{lane}#{BSF_name}.bam"
  microtest: "/data/groups/lab_bock/shared/resources/microtest/{sample_name}.bam"

compute:
  submission_template: pipelines/templates/slurm_template.sub
  submission_command: sbatch
```

Details on project config file sections:

### Project config section: paths

The `paths` section contains paths to various parts of the project: the output directory (the parent directory), the results subdirector, the submission subdirectory (where submit scripts are stored), and pipeline scripts.

### Project config section: metadata

Pointers to sample annotation sheets.

### Project config section: pipeline_config
Occasionally, a particular project needs to run a particular flavor of a pipeline. Rather than creating an entirely new pipeline, you can parameterize the differences with a _pipeline config_ file, and then specify that file in the _project config_ file.

Example:
```
pipeline_config:
  # pipeline configuration files used in project.
  # Key string must match the _name of the pipeline script_ (including extension)
  # Relative paths are relative to this project config file.
  # Default (null) means use the generic config for the pipeline.
  rrbs.py: null
  # Or you can point to a specific config to be used in this project:
  wgbs.py: wgbs_flavor1.yaml
```

This will instruct `looper` to pass `-C wgbs_flavor1.yaml` to any invocations of wgbs.py (for this project only). Your pipelines will need to understand the config file (which will happen automatically if you use pypiper).

### Project config section: pipeline_args

Sometimes a project requires tweaking a pipeline, but does not justify a completely separate _pipeline config_ file. For simpler cases, you can use the `pipeline_args` section, which lets you specify command-line parameters via the project config. This lets you fine-tune your pipeline, so it can run slightly differently for different projects.

Example:
```
pipeline_args:
  rrbs.py:  # pipeline identifier: must match the name of the pipeline script
    # here, include all project-specific args for this pipeline
    "--flavor": simple
    "--flag": null
```

The above specification will now pass '--flavor=simple' and '--flag' whenever rrbs.py is invoked -- for this project only. This is a way to control (and record!) project-level pipeline arg tuning. The only keyword here is `pipeline_args`; all other variables in this section are specific to particular pipelines, command-line arguments, and argument values.

### Project config section: compute
For each iteration, `looper` will create one or more submission scripts for that sample. The `compute` specifies how jobs these scripts will be both produced and run.  This makes it very portable and easy to change cluster management systems, or to just use a local compute power like a laptop or standalone server, by just changing the two variables in the `compute` section.

Example:
```
compute:
  submission_template: pipelines/templates/slurm_template.sub
  submission_command: sbatch
```

There are two sub-parameters in the compute section. First, `submission_template` is a (relative or absolute) path to the template submission script. This is a template with variables (encoded like `{VARIABLE}`), which will be populated independently for each sample as defined in `pipeline_inteface.yaml`. The one variable `{CODE}` is a reserved variable that refers to the actual python command that will run the pipeline. Otherwise, you can use any variables you define in your `pipeline_interface.yaml`.

Second, the `submission_command` is the command-line command that `looper` will prepend to the path of the produced submission script to actually run it (`sbatch` for SLURM, `qsub` for SGE, `sh` for localhost, etc).

In [`templates/`](templates/) are examples for submission templates for [SLURM](templates/slurm_template.sub), [SGE](templates/sge_template.sub), and [local runs](templates/localhost_template.sub). For a local run, just pass the script to the shell with `submission_command: sh`. This will cause each sample to run sequentially, as the shell will block until the run is finished and control is returned to `looper` for the next iteration.

### Project config section: data_sources

The `data_sources` can use regex-like commands to point to different spots on the filesystem for data. The variables (specified by `{variable}`) are populated first by shell environment variables, and then by variables (columns) named in the project sample annotation sheet.

The idea is: don't put absolute paths to files in your annotation sheet. Instead, specify a data source and then provide a regex in the config file. This way if your data changes locations (which happens more often than we would like), or you change servers, you just have to change the config file and not update paths in the annotation sheet. This makes the whole project more portable.

### Project config section: track_configurations

The `track_configurations` section is for making trackhubs (see below).

However, there are more options. See the [project config template](examples/example_project_config.yaml) for a more comprehensive list of options or the [microtest config template](examples/microtest_project_config.yaml) for a ready-to-run example. You can try out the microtest example like this (the `-d` option indicates a dry run, meaning submit scripts are created but not actually submitted).
```
./pipelines/looper.py -c pipelines/examples/microtest_project_config.yaml -d
```
We need better documentation on all the options for the config files.


# Post-pipeline processing (accessory scripts)

Once a pipeline has been run (or is running), you can do some post-processing on the results. In [`scripts/`](scripts/) are __accessory scripts__ that help with monitoring running pipelines, summarizing pipeline outputs, etc. These scripts are not required by the pipelines, but useful for post-processing (scripts used by the pipelines themselves **should go to** [`pipelines/tools/`](pipelines/tools/)). Here are some post-processing scripts:

* [scripts/flagCheck.sh](scripts/flagCheck.sh) - Summarize status flag to check on the status (running, completed, or failed) of pipelines.
* [scripts/make_trackhubs.py](scripts/make_trackhubs.py) - Builds a track hub. Just pass it your config file.
* [scripts/summarizePipelineStats.R](scripts/summarizePipelineStats.R) - Run this in the output folder and it will aggregate and summarize all key-value pairs reported in the `PIPE_stats` files, into tables for each pipeline, and a combined table across all pipelines run in this folder.

You can find other examples in [scripts/](scripts/).

# Developing pipelines

If you plan to create a new pipeline or develop existing pipelines, consider cloning this repo to your personal space, where you do the development. Push changes from there. Use this personal repo to run any tests or whatever, but consider making sure a project is run from a different (frozen) clone, to ensure uniform results.
