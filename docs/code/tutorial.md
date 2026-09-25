# Basic PEP example

This vignette will show you a simple example PEP-formatted project, and how to read it into python using the `peppy` package. This example comes from the [example_peps repository](https://github.com/pepkit/example_peps) in the [example_basic](https://github.com/pepkit/example_peps/tree/master/example_basic) folder.


Start by importing `peppy`, and then let's take a look at the configuration file that defines our project:


```python
import peppy
examples_dir = "../tests/data/example_peps-cfg2/"
```


```python
project_config_file = examples_dir + "example_basic/project_config.yaml"
%cat $project_config_file
```

    pep_version: "2.0.0"
    sample_table: sample_table.csv

It's a basic YAML-formatted file with couple of sections:
- `pep_version` (required; indicates with PEP spec version this config subscribes to)
- `sample_table` (suggested; a pointer to sample annotation sheet. It is stored in the same folder as `project_config.yaml`)

Now, let's now glance at that annotation file: 


```python
sample_table = examples_dir + "example_basic/sample_table.csv"
%cat $sample_table | column -t -s, | cat
```

    sample_name  protocol       file
    frog_1       anySampleType  data/frog1_data.txt
    frog_2       anySampleType  data/frog2_data.txt


This `sample_table.csv` file is a basic CSV file, with rows corresponding to samples, and columns corresponding to sample attributes. Let's read this simple example project into Python using `peppy`:


```python
project = peppy.Project(examples_dir + "example_basic/project_config.yaml")
```

Now, we have access to all the project metadata in easy-to-use form using python objects. We can browse the samples in the project like this:


```python
project.samples[0].file
```




    'data/frog1_data.txt'


