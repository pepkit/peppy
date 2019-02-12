# How to link a pipeline to your project

Looper runs samples through pipelines by according to a file called a ***pipeline interface***. 
How you use this depends on if you're using an existing pipeline or building a new pipeline. 

- **When using *existing* `looper`-compatible pipelines**, you don't need to create a new interface; point your project at the one that comes with the pipeline. 
For more information refer to ["Linking a compatible pipeline"](#existing-compatible-pipelines).
- **When creating *new* `looper`-compatible pipelines**, you'll need to create a new pipeline interface file. 
For more information refer to ["New pipelines"](#new-pipelines)


## Existing compatible pipelines

Many projects will require only existing pipelines that are already `looper`-compatible. 
We maintain a (growing) list of [publicly available compatible pipelines](https://github.com/pepkit/hello_looper/blob/master/looper_pipelines.md) to start. 
The list includes pipelines for experiments covering transcription (RNA-seq), 
chromatin accessibility (ATAC-seq), DNA methylation (RRBS and WGBS), and chromatin interaction and binding (HiChIP).

To use one of these pipelines, first clone the desired code repository. 
Then, using the `pipeline_interfaces` key in the `metadata` section of a project config file, 
point your project to that pipeline's `pipeline_interface` file:

```yaml
  metadata:
    pipeline_interfaces: /path/to/pipeline_interface.yaml
```

The value for the `pipeline_interfaces` key should be the *absolute* path to the pipeline interface file.
After that, you just need to make sure your project definition provides all the necessary sample metadata required by the pipeline you want to use. 
For example, you will need to make sure your sample annotation sheet specifies the correct value under `protocol` that your linked pipeline understands. 
Such details are specific to each pipeline and should be defined somewhere in the pipeline's documentation, e.g. in a `README` file.


## New pipelines

***HINT***: If you're strictly *using* a pipeline, you don't need to worry about this section. 
This is relevant only if you want to make a new or existing pipeline compatible with `looper`.

As long as a pipeline runs on the command line, `looper` can run samples through it. 
A pipeline may consist of script(s) in languages like Perl, Python, or bash, or it may be built with a particular framework. 
Typically, we use Python pipelines built using the [`pypiper` package](http://pypiper.readthedocs.io), 
which provides some additional power to `looper`, but that's optional.

Regardless of what pipelines you use, you will need to tell looper how to communicate with your pipeline. 
That communication protocol is defined in a **pipeline interface**, which is a `yaml` file with two sections:

1. `protocol_mapping` - maps sample `protocol` (the assay type, sometimes called "library" or "library strategy") to one or more pipeline program
2. `pipelines` -  describes the arguments and resources required by each pipeline

Let's start with a simple example. The pipeline interface file may look like this:

```yaml
protocol_mapping:
  RRBS: rrbs_pipeline

pipelines:
  rrbs_pipeline:
    name: RRBS
    path: path/to/rrbs.py
    arguments:
      "--sample-name": sample_name
      "--input": data_path
```

The first section specifies that samples of protocol `RRBS` will be mapped to the pipeline specified by key `rrbs_pipeline`. 
The second section describes where the pipeline with key `rrbs_pipeline` is located and what command-line arguments it requires. 
Pretty simple. Let's go through these 2 sections in more detail:

### Protocol mapping

The `protocol_mapping` section explains how looper should map from a sample protocol 
(like `RNA-seq`, which is a column in your annotation sheet) to a particular pipeline (like `rnaseq.py`), or group of pipelines. 
Here's how to build `protocol_mapping`:

**Case 1:** one protocol maps to one pipeline. Example: `RNA-seq: rnaseq.py`
Any samples that list "RNA-seq" under `library` will be run using the `rnaseq.py` pipeline. 
You can list as many library types as you like in the protocol mapping, 
mapping to as many pipelines as you configure in your `pipelines` section.

Example:
    
```yaml
protocol_mapping:
    RRBS: rrbs.py
    WGBS: wgbs.py
    EG: wgbs.py
    ATAC: atacseq.py
    ATAC-SEQ: atacseq.py
    CHIP: chipseq.py
    CHIP-SEQ: chipseq.py
    CHIPMENTATION: chipseq.py
    STARR: starrseq.py
    STARR-SEQ: starrseq.py
```

**Case 2:** one protocol maps to multiple *independent* pipelines. 
    
Example:

```yaml
protocol_mapping
    Drop-seq: quality_control.py, dropseq.py
```

You can map multiple pipelines to a single protocol if you want samples of a type to kick off more than one pipeline run.
The basic formats for independent pipelines (i.e., they can run concurrently):

Example A:
```yaml
protocol_mapping:
    SMART-seq:  >
      rnaBitSeq.py -f,
      rnaTopHat.py -f
```

Example B:
```yaml
protocol_mapping:
    PROTOCOL: [pipeline1, pipeline2, ...]
```

**Case 3:** a protocol runs one pipeline which depends on another.

*Warning*: This feature (pipeline dependency) is not implemented yet. This documentation describes a protocol that may be implemented in the future, if it is necessary to have dependency among pipeline submissions.

Use *semicolons to indicate dependency*.

Example:
```yaml
protocol_mapping:
    WGBSQC: >
      wgbs.py;
      (nnm.py, pdr.py)
```

### Pipeline configuration
The `pipelines` section defines important information about each pipeline, including its name, location on disk/web, and optional or required command-line arguments. 
In addition, if you're using a cluster resource manager, it also specifies which compute resources to request. 
For each pipeline, you specify values for a few specific keys. 

Let's start with a **single-pipeline example**:

```yaml
pipelines:
  pipeline_key:  # this is variable (script filename)
    name: pipeline_name  # used for assessing pipeline flags (optional)
    path: relative/path/to/pipeline_script.py
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
      resource_package_name:
        file_size: "2"
        cores: "4"
        mem: "6000"
        time: "2-00:00:00"
```

Each pipeline gets its own section (here there's just one: `pipeline_key`). 
The particular keys that you may specify for each pipeline are:

- `path` (required): Absolute or relative path to the script for this pipeline. Relative paths are considered **relative to your pipeline_interface file**. 
We strongly recommend using relative paths where possible to keep your pipeline interface file portable. You may also use shell environment variables (like `${HOME}`) in the `path`.
- `arguments` (required): List of key-value pairs of arguments required by the pipeline. 
The key corresponds verbatim to the string that will be passed on the command line to the pipeline (i.e., the absolute, quoted name of the argument, like `"--input"`). 
The value corresponds to an attribute of the sample, which will be derived from the sample_annotation csv file. 
In other words, it's a column name of your sample annotation sheet. Looper will find the value of this attribute for each sample and pass that to the pipeline as the value for that argument. 
For flag-like arguments that lack a value, you may specify `null` as the value (e.g. `"--quiet-mode": null`). 
These arguments are considered *required*, and `looper` will not submit a pipeline if a sample lacks an attribute that is specified as a value for an argument.
- `name` (recommended): Name of the pipeline. This is used to assess pipeline flags (if your pipeline employs them, like `pypiper` pipelines).
- `optional_arguments`: Any arguments listed in this section will be passed to the pipeline *if the specified attribute exists for the sample*. 
These are considered optional, and so the pipeline will still be submitted if they are not provided.
- `required_input_files` (optional): A list of sample attributes (annotation sheets column names) that will point to input files that must exist.
- `all_input_files` (optional): A list of sample attributes (annotation sheet column names) that will point to input files that are not required, but if they exist, should be counted in the total size calculation for requesting resources.
- `ngs_input_files` (optional): For pipelines using sequencing data, provide a list of sample attributes (annotation sheet column names) that will point to input files to be used for automatic detection of `read_length` and `read_type` sample attributes.
- `looper_args` (optional): Provide `True` or `False` to specify if this pipeline understands looper args, which are then automatically added for:
  - `-C`: config_file (the pipeline config file specified in the project config file; or the default config file, if it exists)
  - `-P`: cores (the number of processing cores specified by the chosen resource package)
  - `-M`: mem (memory limit)
- `resources` (recommended) A section outlining how much memory, CPU, and clock time to request, modulated by input file size
If the `resources` section is missing, looper will only be able to run the pipeline locally (not submit it to a cluster resource manager). 
If you provide a `resources` section, you must define at least 1 option named 'default' with `file_size: "0"`. 
Then, you define as many more resource "packages" or "bundles" as you want. 

**More on `resources`**

The `resources` section can be a bit confusing--think of it like a group of steps of increasing size. 
The first step (default) starts at 0, and this step will catch any files that aren't big enough to get to the next level. 
Each successive step is larger. 
Looper determines the size of your input file, and then iterates over the resource packages until it can't go any further; 
that is, the `file_size` of the package is bigger (in gigabytes) than the input file size of the sample. 
At this point, iteration stops and looper has selected the best-fit resource package for that sample--the smallest package that is still big enough. 

Add as many additional resource sets as you want, with any names. Looper will determine which resource package to use based on the `file_size` of the input file. 
It will select the lowest resource package whose `file_size` attribute does not exceed the size of the input file. 
Because the partition or queue name is relative to your environment, we don't usually specify this in the `resources` section, but rather, in the `pepenv` config. 
So, `file_size: "5"` means 5 GB. This means that resource package only will be used if the input files total size is greater than 5 GB.

**More extensive example:**

```yaml
pipelines:
  rrbs:
    name: RRBS
    looper_args: True
    path: path/to/rrbs.py
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
      high:
        file_size: "4"
        cores: "6"
        mem: "4000"
        time: "2-00:00:00"

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
```
