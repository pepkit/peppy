# Learn amendments in `peppy`

This vignette will show you how and why to use the amendments functionality of the `peppy` package. 

 - basic information about the PEP concept on the [project website](http://pep.databio.org/en/2.0.0/).

 - broader theoretical description in the amendments [documentation section](http://pep.databio.org/en/2.0.0/specification/#project-attribute-amendments).


## Problem/Goal

The example below demonstrates how and why to use amendments project attribute to, e.g. **define numerous similar projects in a single project config file**. This functionality is extremely convenient when one has to define projects with small settings discreptancies, like different attributes in the annotation sheet. For example libraries `ABCD` and `EFGH` instead of the original `RRBS`.


```python
examples_dir = "../tests/data/example_peps-cfg2/example_amendments1/"
sample_table = examples_dir + "sample_table.csv"
%cat $sample_table | column -t -s, | cat
```

    sample_name  protocol  organism  time  file_path

    pig_0h       RRBS      pig       0     source1

    pig_1h       RRBS      pig       1     source1

    frog_0h      RRBS      frog      0     source1

    frog_1h      RRBS      frog      1     source1


## Solution

This can be achieved by using amendments section of `project_config.yaml` file (presented below). The attributes specified in the lowest levels of this section (here: `sample_table`) overwrite the original ones. Consequently, a completely new set of settings is determined with just this value changed. Moreover, multiple amendments can be defined in a single config file *and* activated at the same time. Based on the file presented below, two subprojects will be defined: `newLib` and `newLib2`.


```python
project_config_file = examples_dir + "project_config.yaml"
%cat $project_config_file
```

    pep_version: "2.0.0"
    sample_table: sample_table.csv
    output_dir: $HOME/hello_looper_results
    
    sample_modifiers:
      derive:
        attributes: [file_path]
        sources:
          source1: /data/lab/project/{organism}_{time}h.fastq
          source2: /path/from/collaborator/weirdNamingScheme_{external_id}.fastq
    project_modifiers:
      amend:
        newLib:
          sample_table: sample_table_newLib.csv
        newLib2:
          sample_table: sample_table_newLib2.csv


Obviously, the amendments functionality can be combined with other `peppy` package options, e.g. imply and derive sample modifiers. The derive modifier is used in the example considered here (`derive` key in the `sample_modifiers` section of the config file).


Files `sample_table_newLib.csv` and `sample_table_newLib2.csv` introduce different the `library` attributes. They are used in the subprojects `newLib` and `newLib2`, respectively


```python
sample_table = examples_dir + "sample_table_newLib.csv"
%cat $sample_table | column -t -s, | cat
```

    sample_name  protocol  organism  time  file_path
    pig_0h       ABCD      pig       0     source1
    pig_1h       ABCD      pig       1     source1
    frog_0h      ABCD      frog      0     source1
    frog_1h      ABCD      frog      1     source1



```python
sample_table = examples_dir + "sample_table_newLib2.csv"
%cat $sample_table | column -t -s, | cat
```

    sample_name  protocol  organism  time  file_path
    pig_0h       EFGH      pig       0     source1
    pig_1h       EFGH      pig       1     source1
    frog_0h      EFGH      frog      0     source1
    frog_1h      EFGH      frog      1     source1


## Code

Import `peppy` and read in the project metadata by specifying the path to the `project_config.yaml`


```python
from peppy import Project
p = Project(project_config_file)
```

An appropriate message is displayed, which informs you what are the names of the amendments that you have defined in the `project_config.yaml` file. Nonetheless, just the main project is "active".

Let's inspect it:


```python
p.sample_table
```




<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>file_path</th>
      <th>organism</th>
      <th>protocol</th>
      <th>sample_name</th>
      <th>time</th>
    </tr>
    <tr>
      <th>sample_name</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>pig_0h</th>
      <td>/data/lab/project/pig_0h.fastq</td>
      <td>pig</td>
      <td>RRBS</td>
      <td>pig_0h</td>
      <td>0</td>
    </tr>
    <tr>
      <th>pig_1h</th>
      <td>/data/lab/project/pig_1h.fastq</td>
      <td>pig</td>
      <td>RRBS</td>
      <td>pig_1h</td>
      <td>1</td>
    </tr>
    <tr>
      <th>frog_0h</th>
      <td>/data/lab/project/frog_0h.fastq</td>
      <td>frog</td>
      <td>RRBS</td>
      <td>frog_0h</td>
      <td>0</td>
    </tr>
    <tr>
      <th>frog_1h</th>
      <td>/data/lab/project/frog_1h.fastq</td>
      <td>frog</td>
      <td>RRBS</td>
      <td>frog_1h</td>
      <td>1</td>
    </tr>
  </tbody>
</table>



The column `file_path` was derived and the `library` column holds the original attributes: `RRBS` for each sample.

To "activate" any of the amendments just pass the names of the desired amendments to the `amendments` argument in the `Project` object constructor. 

In case you don't remember the subproject names run the `listAmendments()` metohods on the `Project` object, just like that:


```python
p.list_amendments
```




    ['newLib', 'newLib2']




```python
p_new_lib = Project(project_config_file, amendments = "newLib")
```

Let's inspect it:


```python
p_new_lib.sample_table
```




<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>file_path</th>
      <th>organism</th>
      <th>protocol</th>
      <th>sample_name</th>
      <th>time</th>
    </tr>
    <tr>
      <th>sample_name</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>pig_0h</th>
      <td>/data/lab/project/pig_0h.fastq</td>
      <td>pig</td>
      <td>ABCD</td>
      <td>pig_0h</td>
      <td>0</td>
    </tr>
    <tr>
      <th>pig_1h</th>
      <td>/data/lab/project/pig_1h.fastq</td>
      <td>pig</td>
      <td>ABCD</td>
      <td>pig_1h</td>
      <td>1</td>
    </tr>
    <tr>
      <th>frog_0h</th>
      <td>/data/lab/project/frog_0h.fastq</td>
      <td>frog</td>
      <td>ABCD</td>
      <td>frog_0h</td>
      <td>0</td>
    </tr>
    <tr>
      <th>frog_1h</th>
      <td>/data/lab/project/frog_1h.fastq</td>
      <td>frog</td>
      <td>ABCD</td>
      <td>frog_1h</td>
      <td>1</td>
    </tr>
  </tbody>
</table>



As you can see, the `library` column consists of new attributes (`ABCD`), which were defined in the `sample_table_newLib.csv` file.

Amendments can be also activated interactively, after `Project` object has been crated. Let's activate the second amendment this way:


```python
p_new_lib2 = p.activate_amendments("newLib2")
p_new_lib2.sample_table
```




<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>file_path</th>
      <th>organism</th>
      <th>protocol</th>
      <th>sample_name</th>
      <th>time</th>
    </tr>
    <tr>
      <th>sample_name</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>pig_0h</th>
      <td>/data/lab/project/pig_0h.fastq</td>
      <td>pig</td>
      <td>EFGH</td>
      <td>pig_0h</td>
      <td>0</td>
    </tr>
    <tr>
      <th>pig_1h</th>
      <td>/data/lab/project/pig_1h.fastq</td>
      <td>pig</td>
      <td>EFGH</td>
      <td>pig_1h</td>
      <td>1</td>
    </tr>
    <tr>
      <th>frog_0h</th>
      <td>/data/lab/project/frog_0h.fastq</td>
      <td>frog</td>
      <td>EFGH</td>
      <td>frog_0h</td>
      <td>0</td>
    </tr>
    <tr>
      <th>frog_1h</th>
      <td>/data/lab/project/frog_1h.fastq</td>
      <td>frog</td>
      <td>EFGH</td>
      <td>frog_1h</td>
      <td>1</td>
    </tr>
  </tbody>
</table>


