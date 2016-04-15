# Pipelines

Note! Documentation is being migrated into the [/docs](/docs) subfolder, to be managed by sphinx.

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

# Post-pipeline processing (accessory scripts)

Once a pipeline has been run (or is running), you can do some post-processing on the results. In [`scripts/`](scripts/) are __accessory scripts__ that help with monitoring running pipelines, summarizing pipeline outputs, etc. These scripts are not required by the pipelines, but useful for post-processing (scripts used by the pipelines themselves **should go to** [`pipelines/tools/`](pipelines/tools/)). Here are some post-processing scripts:

* [scripts/flagCheck.sh](scripts/flagCheck.sh) - Summarize status flag to check on the status (running, completed, or failed) of pipelines.
* [scripts/make_trackhubs.py](scripts/make_trackhubs.py) - Builds a track hub. Just pass it your config file.
* [scripts/summarizePipelineStats.R](scripts/summarizePipelineStats.R) - Run this in the output folder and it will aggregate and summarize all key-value pairs reported in the `PIPE_stats` files, into tables for each pipeline, and a combined table across all pipelines run in this folder.

You can find other examples in [scripts/](scripts/).

# Developing pipelines

If you plan to create a new pipeline or develop existing pipelines, consider cloning this repo to your personal space, where you do the development. Push changes from there. Use this personal repo to run any tests or whatever, but consider making sure a project is run from a different (frozen) clone, to ensure uniform results.
