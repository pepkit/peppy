# Looper

[![Documentation Status](http://readthedocs.org/projects/looper/badge/?version=latest)](http://looper.readthedocs.io/en/latest/?badge=latest)

__`Looper`__ is a pipeline submission engine that parses sample inputs and submits pipelines for each sample. It also has several accompanying scripts that use the same infrastructure to do other processing for projects. Looper was conceived to use [`pypiper`](https://github.com/epigen/pypiper/) pipelines, but does not require this.

# Links

 * Public-facing permalink: http://databio.org/looper
 * Documentation: [Read the Docs](http://looper.readthedocs.org/) (still under heavy work)
 * Source code: http://github.com/epigen/looper


# Installing

```
pip install https://github.com/epigen/looper/zipball/master
```

You will have a `looper` executable and all accessory scripts (from [`scripts/`](scripts/), see below) in your `$PATH`.

# Running pipelines

`Looper` just requires a yaml format config file passed as an argument, which contains all the settings required. This can, for example, submit each job to SLURM (or SGE, or run them locally).

```bash
looper -c metadata/config.yaml
```

# Post-pipeline processing (accessory scripts)

Once a pipeline has been run (or is running), you can do some post-processing on the results. In [`scripts/`](scripts/) are __accessory scripts__ that help with monitoring running pipelines, summarizing pipeline outputs, etc. These scripts are not required by the pipelines, but useful for post-processing. Here are some post-processing scripts:

* [scripts/flagCheck.sh](scripts/flagCheck.sh) - Summarize status flag to check on the status (running, completed, or failed) of pipelines.
* [scripts/make_trackhubs.py](scripts/make_trackhubs.py) - Builds a track hub. Just pass it your config file.
* [scripts/summarizePipelineStats.R](scripts/summarizePipelineStats.R) - Run this in the output folder and it will aggregate and summarize all key-value pairs reported in the `PIPE_stats` files, into tables for each pipeline, and a combined table across all pipelines run in this folder.

You can find other examples in [scripts/](scripts/).
