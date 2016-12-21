# Looper

[![Documentation Status](http://readthedocs.org/projects/looper/badge/?version=latest)](http://looper.readthedocs.io/en/latest/?badge=latest)

__`Looper`__ is a pipeline submission engine that parses sample inputs and submits pipelines for each sample. Looper was conceived to use [pypiper](https://github.com/epigen/pypiper/) pipelines, but does not require this.

# Links

 * Public-facing permalink: http://databio.org/looper
 * Documentation: [Read the Docs](http://looper.readthedocs.org/) (still under heavy work)
 * Source code: http://github.com/epigen/looper


# Installing

```
pip install https://github.com/epigen/looper/zipball/master
```

You will have a `looper` executable and all accessory scripts (from [`scripts/`](scripts/)) in your `$PATH`.

# Running pipelines

`Looper` just requires a yaml format config file passed as an argument, which contains all the settings required. This can, for example, submit each job to SLURM (or SGE, or run them locally).

```bash
looper run metadata/config.yaml
```

# Looper commands

Looper can do more than just run your samples through pipelines. Once a pipeline has been run (or is running), you can do some post-processing on the results. These commands help with monitoring running pipelines, summarizing pipeline outputs, etc. This includes `looper clean`, `looper destroy`, `looper summarize`, and more. You can find details about these in the **Commands** section of the documentation.