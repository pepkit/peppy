# Learn sample subannotations in `peppy`

This vignette will show you how and why to use the subsample table functionality of the `peppy` package.

 - basic information about the PEP concept visit the [project website](http://pep.databio.org/en/2.0.0/).
 
 - broader theoretical description in the subsample table [documentation section](http://pep.databio.org/en/2.0.0/specification/#project-attribute-subsample_table).

## Problem/Goal

This series of examples below demonstrates how and why to use sample subannoatation functionality in multiple cases to **provide multiple input files of the same type for a single sample**.

## Solutions

### Example 1: basic sample subannotation table

This example demonstrates how the sample subannotation functionality is used. In this example, 2 samples have multiple input files that need merging (`frog_1` and `frog_2`), while 1 sample (`frog_3`) does not. Therefore, `frog_3` specifies its file in the `sample_table.csv` file, while the others leave that field blank and instead specify several files in the `subsample_table.csv` file.

This example is made up of these components:

* Project config file:


```python
examples_dir = "../tests/data/example_peps-cfg2/example_subtable1/"
project_config = examples_dir + "project_config.yaml"
%cat $project_config
```

    pep_version: "2.0.0"
    sample_table: sample_table.csv
    subsample_table: subsample_table.csv
    output_dir: $HOME/example_results


* Sample table:


```python
sample_table = examples_dir + "sample_table.csv"
%cat $sample_table | column -t -s, | cat
```

    sample_name  protocol       file
    frog_1       anySampleType  multi
    frog_2       anySampleType  multi
    frog_3       anySampleType  multi


* Subsample table:


```python
subsample_table = examples_dir + "subsample_table.csv"
%cat $subsample_table | column -t -s, | cat
```

    column: line too long
    sample_name  subsample_name  file
    frog_1       sub_a           data/frog1a_data.txt
    frog_1       sub_b           data/frog1b_data.txt
    frog_1       sub_c           data/frog1c_data.txt
    frog_2       sub_a           data/frog2a_data.txt


Let's load the project config, create the Project object and see if multiple files are present 


```python
from peppy import Project
p = Project(project_config)
samples = p.sample_table
samples
```




<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>file</th>
      <th>protocol</th>
      <th>sample_name</th>
      <th>subsample_name</th>
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
      <th>frog_1</th>
      <td>[data/frog1a_data.txt, data/frog1b_data.txt, d...</td>
      <td>anySampleType</td>
      <td>frog_1</td>
      <td>[sub_a, sub_b, sub_c]</td>
    </tr>
    <tr>
      <th>frog_2</th>
      <td>[data/frog2a_data.txt, data/frog2b_data.txt]</td>
      <td>anySampleType</td>
      <td>frog_2</td>
      <td>[sub_a, sub_b]</td>
    </tr>
    <tr>
      <th>frog_3</th>
      <td>multi</td>
      <td>anySampleType</td>
      <td>frog_3</td>
      <td>NaN</td>
    </tr>
  </tbody>
</table>



### Example 2: subannotations and derived attributes

This example uses a `subsample_table.csv` file and a derived attributes to point to files. This is a rather complex example. Notice we must include the `file_id` column in the `sample_table.csv` file, and leave it blank; this is then populated by just some of the samples (`frog_1` and `frog_2`) in the `subsample_table.csv`, but is left empty for the samples that are not merged.

This example is made up of these components:

* Project config file:


```python
examples_dir = "../tests/data/example_peps-cfg2/example_subtable2/"
project_config = examples_dir + "project_config.yaml"
%cat $project_config
```

    pep_version: "2.0.0"
    sample_table: sample_table.csv
    subsample_table: subsample_table.csv
    output_dir: $HOME/hello_looper_results
    pipeline_interfaces: [../pipeline/pipeline_interface.yaml]
    
    sample_modifiers:
      derive:
        attributes: [file]
        sources:
          local_files: "../data/{identifier}{file_id}_data.txt"
          local_files_unmerged: "../data/{identifier}_data.txt"

* Sample table:


```python
sample_table = examples_dir + "sample_table.csv"
%cat $sample_table | column -t -s, | cat
```

    column: line too long
    sample_name  protocol       identifier  file
    frog_1       anySampleType  frog1       local_files
    frog_2       anySampleType  frog2       local_files
    frog_3       anySampleType  frog3       local_files_unmerged


* Subsample table:


```python
subsample_table = examples_dir + "subsample_table.csv"
%cat $subsample_table | column -t -s, | cat
```

    column: line too long
    sample_name  file_id  subsample_name
    frog_1       a        a
    frog_1       b        b
    frog_1       c        c
    frog_2       a        a


Let's load the project config, create the Project object and see if multiple files are present 


```python
p = Project(project_config)
samples = p.sample_table
samples
```




<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>file</th>
      <th>file_id</th>
      <th>identifier</th>
      <th>protocol</th>
      <th>sample_name</th>
      <th>subsample_name</th>
    </tr>
    <tr>
      <th>sample_name</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>frog_1</th>
      <td>[../data/frog1a_data.txt, ../data/frog1b_data....</td>
      <td>[a, b, c]</td>
      <td>frog1</td>
      <td>anySampleType</td>
      <td>frog_1</td>
      <td>[a, b, c]</td>
    </tr>
    <tr>
      <th>frog_2</th>
      <td>[../data/frog2a_data.txt, ../data/frog2b_data....</td>
      <td>[a, b]</td>
      <td>frog2</td>
      <td>anySampleType</td>
      <td>frog_2</td>
      <td>[a, b]</td>
    </tr>
    <tr>
      <th>frog_3</th>
      <td>../data/frog3_data.txt</td>
      <td>NaN</td>
      <td>frog3</td>
      <td>anySampleType</td>
      <td>frog_3</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>frog_4</th>
      <td>../data/frog4_data.txt</td>
      <td>NaN</td>
      <td>frog4</td>
      <td>anySampleType</td>
      <td>frog_4</td>
      <td>NaN</td>
    </tr>
  </tbody>
</table>



### Example 3: subannotations and expansion characters

This example gives the exact same results as Example 2, but in this case, uses a wildcard for `frog_2` instead of including it in the `subsample_table.csv` file. Since we can't use a wildcard and a subannotation for the same sample, this necessitates specifying a second data source class (`local_files_unmerged`) that uses an asterisk (`*`). The outcome is the same (`file` columns match).

This example is made up of these components:

* Project config file:


```python
examples_dir = "../tests/data/example_peps-cfg2/example_subtable3/"
# need to cd to the example dir so that the glob works as expected
%cd $examples_dir 
project_config = "project_config.yaml"
%cat $project_config
```

    /Users/mstolarczyk/Uczelnia/UVA/code/peppy/tests/data/example_peps-cfg2/example_subtable3
    pep_version: "2.0.0"
    sample_table: sample_table.csv
    subsample_table: subsample_table.csv
    output_dir: $HOME/hello_looper_results
    pipeline_interfaces: [../pipeline/pipeline_interface.yaml]
    
    sample_modifiers:
      derive:
        attributes: [file]
        sources:
          local_files: "../data/{identifier}{file_id}_data.txt"
          local_files_unmerged: "../data/{identifier}*_data.txt"
    


* Sample table:


```python
%cat sample_table.csv | column -t -s, | cat
```

    sample_name  protocol       identifier  file                  file_id
    frog_1       anySampleType  frog1       local_files
    frog_2       anySampleType  frog2       local_files_unmerged
    frog_3       anySampleType  frog3       local_files_unmerged
    frog_4       anySampleType  frog4       local_files_unmerged


* Subsample table:


```python
%cat subsample_table.csv | column -t -s, | cat
```

    sample_name  file_id
    frog_1       a
    frog_1       b
    frog_1       c


Let's load the project config, create the Project object and see if multiple files are present 


```python
p = Project(project_config)
samples = p.sample_table
samples
```




<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>file</th>
      <th>file_id</th>
      <th>identifier</th>
      <th>protocol</th>
      <th>sample_name</th>
      <th>subsample_name</th>
    </tr>
    <tr>
      <th>sample_name</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>frog_1</th>
      <td>[../data/frog1a_data.txt, ../data/frog1b_data....</td>
      <td>[a, b, c]</td>
      <td>frog1</td>
      <td>anySampleType</td>
      <td>frog_1</td>
      <td>[0, 1, 2]</td>
    </tr>
    <tr>
      <th>frog_2</th>
      <td>[../data/frog2_data.txt, ../data/frog2a_data.t...</td>
      <td>NaN</td>
      <td>frog2</td>
      <td>anySampleType</td>
      <td>frog_2</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>frog_3</th>
      <td>../data/frog3_data.txt</td>
      <td>NaN</td>
      <td>frog3</td>
      <td>anySampleType</td>
      <td>frog_3</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>frog_4</th>
      <td>../data/frog4_data.txt</td>
      <td>NaN</td>
      <td>frog4</td>
      <td>anySampleType</td>
      <td>frog_4</td>
      <td>NaN</td>
    </tr>
  </tbody>
</table>


