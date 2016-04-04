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

We use the Looper (`looper.py`) to run pipelines. This just requires a config file passed as an argument, which contains all the settings required. It submits each job to SLURM.

```bash
python ~/repo/pipelines/looper.py -c metadata/config.txt
```
or

```bash
looper -c metadata/config.txt
```

# Config files

Looper takes a single primary argument: a _project config file_ that specifies information about your project. Here's an example:

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

### Data sources section
The data sources can use regex-like commands to point to different spots on the filesystem for data. The variables (specified by `{variable}` are populated in this order:

The idea is: don't put absolute paths to files in your annotation sheet. Instead, specify a data source and then provide a regex in the config file. This way if your data changes locations (which happens more often than we would like), or you change servers, you just have to change the config file and not update paths in the annotation sheet. This makes the whole project more portable.

The `track_configurations` section is for making trackhubs (see below).

However, there are more options. See the [project config template](examples/example_project_config.yaml) for a more comprehensive list of options or the [microtest config template](examples/microtest_project_config.yaml) for a ready-to-run example. You can try out the microtest example like this (the `-d` option indicates a dry run, meaning submit scripts are created but not actually submitted).
```
./pipelines/looper.py -c pipelines/examples/microtest_project_config.yaml -d
```
We need better documentation on all the options for the config files.

### Pipeline-specific config files

# Post-pipeline processing (accessory scripts)

Once a pipeline has been run (or is running), you can do some post-processing on the results. In [`scripts/`](scripts/) are __accessory scripts__ that help with monitoring running pipelines, summarizing pipeline outputs, etc. These scripts are not required by the pipelines, but useful for post-processing (scripts used by the pipelines themselves **should go to** [`pipelines/tools/`](pipelines/tools/)). Here are some post-processing scripts:

* [scripts/flagCheck.sh](scripts/flagCheck.sh) - Summarize status flag to check on the status (running, completed, or failed) of pipelines.
* [scripts/make_trackhubs.py](scripts/make_trackhubs.py) - Builds a track hub. Just pass it your config file.
* [scripts/summarizePipelineStats.R](scripts/summarizePipelineStats.R) - Run this in the output folder and it will aggregate and summarize all key-value pairs reported in the `PIPE_stats` files, into tables for each pipeline, and a combined table across all pipelines run in this folder.

You can find other examples in [scripts/](scripts/).

# Developing pipelines

If you plan to create a new pipeline or develop existing pipelines, consider cloning this repo to your personal space, where you do the development. Push changes from there. Use this personal repo to run any tests or whatever, but consider making sure a project is run from a different (frozen) clone, to ensure uniform results.
