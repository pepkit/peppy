# How to initiate peppy using different methods

peppy supports multiple ways to initiate a project. The most common way is to use a configuration file. 
However, peppy also supports using a csv file (sample sheet), and a yaml file (sample sheet).
Additionally, peppy can be initiated using Python objects such as a pandas dataframe or a dictionary.

## 1. Using a configuration file
```python
import peppy
project = peppy.Project.from_pep_config("path/to/project/config.yaml")
```

## 2. Using csv file (sample sheet)
```python
import peppy
project = peppy.Project.from_pep_config("path/to/project/sample_sheet.csv")
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

## 6. Using a csv file from a url
```python
import peppy
project = peppy.Project("https://raw.githubusercontent.com/pepkit/example_peps/master/example_basic/sample_table.csv")
```
