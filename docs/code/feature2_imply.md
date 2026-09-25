# Learn implied sample modifier in `peppy`

This vignette will show you how and why to use the implied attributes functionality of the `peppy` package. 

 - basic information about the PEP concept on the [project website](http://pep.databio.org/en/2.0.0)
 
 - broader theoretical description in the implied attributes [documentation section](http://pep.databio.org/en/2.0.0/specification/#sample_modifiersimply).

## Problem/Goal
The example below demonstrates how and why to use implied attributes functionality to **save your time and effort** in case multiple sample attributes need to be defined for many samples and they **follow certain patterns**. Please consider the example below for reference:


```python
examples_dir = "../tests/data/example_peps-cfg2/example_imply/"
sample_table_ori = examples_dir + "sample_table_pre.csv"
%cat $sample_table_ori | column -t -s, | cat
```

    sample_name  organism  time  file_path                        genome  genome_size
    frog_0h      frog      0     data/lab/project/frog_0h.fastq
    frog_1h      frog      1     data/lab/project/frog_1h.fastq
    human_1h     human     1     data/lab/project/human_1h.fastq  hg38    hs
    human_0h     human     0     data/lab/project/human_0h.fastq  hg38    hs
    mouse_1h     mouse     1     data/lab/project/mouse_1h.fastq  mm10    mm
    mouse_0h     mouse     0     data/lab/project/mouse_1h.fastq  mm10    mm


## Solution
Noticeably, the samples with attributes `human` and `mouse` (in the `organism` column) follow two distinct patterns here. They have additional attributes in attributes `genome` and `genome_size` in the `sample_table.csv` file. Consequently you can use implied attributes to add those attributes to the sample annotations (set global, species-level attributes at the project level instead of duplicating that information for every sample that belongs to a species). The way how this process is carried out is indicated explicitly in the `project_config.yaml` file (presented below).


```python
project_config_file = examples_dir + "project_config.yaml"
%cat $project_config_file
```

    pep_version: '2.0.0'
    sample_table: sample_table.csv
    looper:
      output_dir: $HOME/hello_looper_results
    
    sample_modifiers:
      imply:
        - if:
            organism: human
          then:
            genome: hg38
            macs_genome_size: hs
        - if:
            organism: mouse
          then:
            genome: mm10
            macs_genome_size: mm

Consequently, you can design `sample_modifiers.imply` - a multi-level key-value section in the `project_config.yaml` file. Note that the keys must match the column names and attributes in the `sample_annotations.csv` file. 

Let's introduce a few modifications to the original `sample_table.csv` file to use the `sample_modifiers.imply` section of the config. Simply skip the attributes that will be implied and let the `peppy` do the work for you.


```python
sample_table = examples_dir + "sample_table.csv"
%cat $sample_table | column -t -s, | cat
```

    sample_name  organism  time  file_path
    frog_0h      frog      0     data/lab/project/frog_0h.fastq
    frog_1h      frog      1     data/lab/project/frog_1h.fastq
    human_1h     human     1     data/lab/project/human_1h.fastq
    human_0h     human     0     data/lab/project/human_0h.fastq
    mouse_1h     mouse     1     data/lab/project/mouse_1h.fastq
    mouse_0h     mouse     0     data/lab/project/mouse_1h.fastq


## Code
Load `peppy` and read in the project metadata by specifying the path to the `project_config.yaml`:


```python
from peppy import Project
p = Project(project_config_file)
```

And inspect it:


```python
print(p)
p.sample_table
```

    Project 'example_imply' (/Users/mstolarczyk/Uczelnia/UVA/code/peppy/tests/data/example_peps-cfg2/example_imply/project_config.yaml)
    6 samples: frog_0h, frog_1h, human_1h, human_0h, mouse_1h, mouse_0h
    Sections: pep_version, sample_table, looper, sample_modifiers





<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>file_path</th>
      <th>organism</th>
      <th>sample_name</th>
      <th>time</th>
      <th>genome</th>
      <th>macs_genome_size</th>
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
      <th>frog_0h</th>
      <td>data/lab/project/frog_0h.fastq</td>
      <td>frog</td>
      <td>frog_0h</td>
      <td>0</td>
      <td>NaN</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>frog_1h</th>
      <td>data/lab/project/frog_1h.fastq</td>
      <td>frog</td>
      <td>frog_1h</td>
      <td>1</td>
      <td>NaN</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>human_1h</th>
      <td>data/lab/project/human_1h.fastq</td>
      <td>human</td>
      <td>human_1h</td>
      <td>1</td>
      <td>hg38</td>
      <td>hs</td>
    </tr>
    <tr>
      <th>human_0h</th>
      <td>data/lab/project/human_0h.fastq</td>
      <td>human</td>
      <td>human_0h</td>
      <td>0</td>
      <td>hg38</td>
      <td>hs</td>
    </tr>
    <tr>
      <th>mouse_1h</th>
      <td>data/lab/project/mouse_1h.fastq</td>
      <td>mouse</td>
      <td>mouse_1h</td>
      <td>1</td>
      <td>mm10</td>
      <td>mm</td>
    </tr>
    <tr>
      <th>mouse_0h</th>
      <td>data/lab/project/mouse_1h.fastq</td>
      <td>mouse</td>
      <td>mouse_0h</td>
      <td>0</td>
      <td>mm10</td>
      <td>mm</td>
    </tr>
  </tbody>
</table>



As you can see, the resulting samples are annotated the same way as if they were read from the original annotations file with attributes in the two last columns manually determined.
