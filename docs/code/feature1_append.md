# Learn append sample modifier in `peppy`

This vignette will show you how and why to use the append functionality of the `pepr` package. 

 - basic information about this concept on the [specification website](http://pep.databio.org/en/2.0.0/specification/#sample_modifiersappend).

## Problem/Goal
The example below demonstrates how to use the constant attributes to **define the samples attributes in the `read_type` column** of the `sample_table.csv` file. This functionality is extremely useful when there are many samples that are characterized by identical values of certain attribute (here: value `SINGLE` in `read_type` attribute). Please consider the example below for reference:


```python
examples_dir = "../tests/data/example_peps-cfg2/example_append/"
sample_table_ori = examples_dir + "sample_table_pre.csv"
%cat $sample_table_ori | column -t -s, | cat
```

    sample_name  organism  time  read_type

    pig_0h       pig       0     SINGLE

    pig_1h       pig       1     SINGLE

    frog_0h      frog      0     SINGLE

    frog_1h      frog      1     SINGLE


## Solution
As the name suggests the attributes in the specified attributes (here: `read_type`) can be defined as constant ones. The way how this process is carried out is indicated explicitly in the `project_config.yaml` file (presented below). The name of the column is determined in the `sample_modifiers.append` key-value pair. Note that definition of more than one constant attribute is possible.



```python
project_config_file = examples_dir + "project_config.yaml"
%cat $project_config_file
```

    pep_version: "2.0.0"
    sample_table: sample_table.csv
    
    sample_modifiers:
      append:
        read_type: SINGLE
    


Let's introduce a few modifications to the original `sample_table.csv` file to use the `sample_modifiers.append` section of the config. Simply skip the attributes that are set constant and let the `pepr` do the work for you.


```python
sample_table = examples_dir + "sample_table.csv"
%cat $sample_table | column -t -s, | cat
```

    sample_name  organism  time 

    pig_0h       pig       0

    pig_1h       pig       1

    frog_0h      frog      0

    frog_1h      frog      1



## Code
Import `peppy` and read in the project metadata by specifying the path to the `project_config.yaml`:


```python
from peppy import Project
p = Project(project_config_file)
```

And inspect it:


```python
print(p)
p.sample_table
```

    Project 'example_append' (/Users/mstolarczyk/Uczelnia/UVA/code/peppy/tests/data/example_peps-cfg2/example_append/project_config.yaml)
    4 samples: pig_0h, pig_1h, frog_0h, frog_1h
    Sections: pep_version, sample_table, sample_modifiers





<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>organism</th>
      <th>read_type</th>
      <th>sample_name</th>
      <th>time</th>
    </tr>
    <tr>
      <th>sample_name</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>pig_0h</th>
      <td>pig</td>
      <td>SINGLE</td>
      <td>pig_0h</td>
      <td>0</td>
    </tr>
    <tr>
      <th>pig_1h</th>
      <td>pig</td>
      <td>SINGLE</td>
      <td>pig_1h</td>
      <td>1</td>
    </tr>
    <tr>
      <th>frog_0h</th>
      <td>frog</td>
      <td>SINGLE</td>
      <td>frog_0h</td>
      <td>0</td>
    </tr>
    <tr>
      <th>frog_1h</th>
      <td>frog</td>
      <td>SINGLE</td>
      <td>frog_1h</td>
      <td>1</td>
    </tr>
  </tbody>
</table>



As you can see, the resulting samples are annotated the same way as if they were read from the original annotations file with attributes in the last column manually determined.
