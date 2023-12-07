# How to initiate peppy using different methods

peppy supports multiple ways to initiate a project. The most common way is to use a configuration file. 
However, peppy also supports using a csv file (sample sheet), and a yaml file (sample sheet).
Additionally, peppy can be initiated using Python objects such as a pandas dataframe or a dictionary.

## 1. Using a configuration file
```python
import peppy
project = peppy.Project("path/to/project/config.yaml")
```

## 2. Using csv file (sample sheet)
```python
import peppy
project = peppy.Project("path/to/project/sample_sheet.csv")
```

## 3. Using yaml sample sheet
```python
import peppy
project = peppy.Project.from_yaml("path/to/project/sample_sheet.yaml")
```


## 4. Using a pandas dataframe
```python
import pandas as pd
import peppy
df = pd.read_csv("path/to/project/sample_sheet.csv")
project = peppy.Project.from_pandas(df)
```

## 5. Using a peppy generated dict
```python
import peppy
project = peppy.Project.from_dict({`_config`: str,
                                   `_samples`: list | dict,
                                   `_subsamples`: list[list | dict]})
```

## 6. Using a csv file from a url
```python
import peppy
project = peppy.Project("example_url.csv")
```
