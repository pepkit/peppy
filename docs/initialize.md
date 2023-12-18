# How to initiate peppy using different methods

The primary use case of `peppy` is to create a `peppy.Project` object, which will give you an API for interacting with your project and sample metadata. There are multiple ways to instantiate a `peppy.Project`. 
The most common is to use a configuration file; however, you can also use a `CSV` file (sample sheet), or a sample `YAML` file (sample sheet), or use Python objects directly, such as a `pandas` DataFrame, or a Python `dict`.


<figure>
<img src="../img/format_convert.svg" width="475">
<figcaption>peppy can read from and produce various metadata formats</figcaption>
</figure>


## 1. From PEP configuration file

```python
import peppy
project = peppy.Project.from_pep_config("path/to/project/config.yaml")
```

## 2. FROM `CSV` file (sample sheet)

```python
import peppy
project = peppy.Project.from_pep_config("path/to/project/sample_sheet.csv")
```

You can also instantiate directly from a URL to a CSV file:

```python
import peppy
project = peppy.Project("https://raw.githubusercontent.com/pepkit/example_peps/master/example_basic/sample_table.csv")
```


## 3. From `YAML` sample sheet

```python
import peppy

project = peppy.Project.from_sample_yaml("path/to/project/sample_sheet.yaml")
```


## 4. From a `pandas` DataFrame

```python
import pandas as pd
import peppy
df = pd.read_csv("path/to/project/sample_sheet.csv")
project = peppy.Project.from_pandas(df)
```

## 5. From a `peppy`-generated `dict`

Store a `peppy.Project` object as a dict using `prj.to_dict()`. Then, load it with `Project.from_dict()`:

```python
import peppy

project = peppy.Project("https://raw.githubusercontent.com/pepkit/example_peps/master/example_basic/sample_table.csv")
project_dict = project.to_dict(extended=True)
project_copy = peppy.Project.from_dict(project_dict)

# now you can check if this project is the same as the original project
print(project_copy == project)
```

Or, you could generate an equivalent dictionary in some other way:


```python
import peppy
project = peppy.Project.from_dict(
    {'_config': {'description': None,
                 'name': 'example_basic',
                 'pep_version': '2.0.0',
                 'sample_table': 'sample_table.csv',},
    '_sample_dict': [{'organism': 'pig', 'sample_name': 'pig_0h', 'time': '0'},
                     {'organism': 'pig', 'sample_name': 'pig_1h', 'time': '1'},
                     {'organism': 'frog', 'sample_name': 'frog_0h', 'time': '0'},
                     {'organism': 'frog', 'sample_name': 'frog_1h', 'time': '1'}],
    '_subsample_list': [[{'read1': 'frog1a_data.txt',
                       'read2': 'frog1a_data2.txt',
                       'sample_name': 'frog_0h'},
                      {'read1': 'frog1b_data.txt',
                       'read2': 'frog1b_data2.txt',
                       'sample_name': 'pig_0h'},
                      {'read1': 'frog1c_data.txt',
                       'read2': 'frog1b_data2.txt',
                       'sample_name': 'pig_0h'}]]})
```
