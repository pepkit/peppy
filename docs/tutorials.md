# Extended tutorial

The best way to learn is by example, so here's an extended tutorial to get you started using looper to run pre-made pipelines on a pre-made project.

First, install looper and pypiper. [`pypiper`](http://pypiper.readthedocs.io) is our pipeline development framework. While `pypiper` is not required to use `looper` (which can work with any command-line tool), we install it now since this tutorial uses `pypiper` pipelines:

```bash
pip install --user https://github.com/epigen/looper/zipball/master
pip install --user https://github.com/epigen/pypiper/zipball/master
```

Now, you will need to grab a project to run, and some pipelines to run on it. We have a functional working project example and an open source pipeline repository on github.


```bash
git clone https://github.com/epigen/microtest.git
git clone https://github.com/epigen/open_pipelines.git
```

Now you can run this project with looper! Just use `looper run`:

```bash
looper run microtest/config/microtest_config.tutorial.yaml
```

***Hint:*** You can add the `looper` executable to your shell path:
```bash
export PATH=~/.local/bin:$PATH
```


## Pipeline outputs

Outputs of pipeline runs will be under the directory specified in the `output_dir` variable under the `paths` section 
in the project config file (see the [config files page](config-files.md)).

Inside of an `output_dir` there will be two directories:
- `results_pipeline` - a directory with output of the pipeline(s), for each sample/pipeline combination (often one per sample)
- `submissions` - which holds a YAML representation of each sample and a log file for each submitted job

In this example, we just ran one example sample (an amplicon sequencing library) through a pipeline that processes amplicon data 
(to determine percentage of indels in amplicon)

From here to running hundreds of samples of various sample types is virtually the same effort!


## On your own
To use `looper` on your own, you will need to prepare 2 things: a **project** (metadata that define *what* you want to process), and **pipelines** (*how* to process data). 
The next sections provide detailed instructions on how to define these:
1. **Project**. To link your project to `looper`, you will need to [define your project](project-config.md) using a standard format. 
2. **Pipelines**. You will want to either use pre-made `looper`-compatible pipelines or link your own custom-built pipelines. 
Either way, the next section includes detailed instructions on how to [connect your pipeline](pipeline-interface.md) to `looper`.
