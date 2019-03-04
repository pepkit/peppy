
# Basic PEP example

The PEP that this example is based on is available in the [`example_peps` repsitory](https://github.com/pepkit/example_peps) in the [example_basic](https://github.com/pepkit/example_peps/tree/master/example_basic) folder.

This vignette will show you a simple example PEP-formatted project, and how to read it into python using the `peppy` package.


Start by importing `peppy`, and then let's take a look at the configuration file that defines our project:


```python
import peppy
```


```python
project_config_file = "example_basic/project_config.yaml"
with open(project_config_file) as f:
    print(f.read())
```

    metadata:
      sample_annotation: sample_annotation.csv
      output_dir: $HOME/hello_looper_results
    


It's a basic `yaml` file with one section, *metadata*, with just two variables. This is about the simplest possible PEP project configuration file. The *sample_annotation* points at the annotation file, which is stored in the same folder as `project_config.yaml`. Let's now glance at that annotation file: 


```python
project_config_file = "example_basic/sample_annotation.csv"
with open(project_config_file) as f:
    print(f.read())
```

    sample_name,library,file
    frog_1,anySampleType,data/frog1_data.txt
    frog_2,anySampleType,data/frog2_data.txt
    


This *sample_annotation* file is a basic *csv* file, with rows corresponding to samples, and columns corresponding to sample attributes. Let's read this simple example project into python using `peppy`:


```python
proj = peppy.Project("example_basic/project_config.yaml")
```

Now, we have access to all the project metadata in easy-to-use form using python objects. We can browse the samples in the project like this:


```python
proj.samples[0].file
```




    'data/frog1_data.txt'




```python

```
