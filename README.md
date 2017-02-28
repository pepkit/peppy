# Looper

[![Documentation Status](http://readthedocs.org/projects/looper/badge/?version=latest)](http://looper.readthedocs.io/en/latest/?badge=latest)
[![Build Status](https://travis-ci.org/vreuter/looper.svg?branch=master)](https://travis-ci.org/vreuter/looper)

__`Looper`__ is a pipeline submission engine that parses sample inputs and submits pipelines for each sample. Looper was conceived to use [pypiper](https://github.com/epigen/pypiper/) pipelines, but does not require this.

You can download the latest version from the [releases page](https://github.com/epigen/looper/releases).



# Links

 * Public-facing permalink: http://databio.org/looper
 * Documentation: [Read the Docs](http://looper.readthedocs.org/)
 * Source code: http://github.com/epigen/looper


# Installing
Looper supports Python 2.7 only and has been tested only in Linux.

```
pip install https://github.com/epigen/looper/zipball/master
```

To have the `looper` executable in your `$PATH`, add the following line to your .bashrc file:

```
export PATH=$PATH:~/.local/bin
```


# Running pipelines

`Looper` just requires a yaml format config file passed as an argument, which contains all the settings required. This can, for example, submit each job to SLURM (or SGE, or run them locally).

```bash
looper run project_config.yaml
```


# Looper commands

Looper can do more than just run your samples through pipelines. Once a pipeline has been run (or is running), you can do some post-processing on the results. These commands help with monitoring running pipelines, summarizing pipeline outputs, etc. This includes `looper clean`, `looper destroy`, `looper summarize`, and more. You can find details about these in the **Commands** section of the documentation.
