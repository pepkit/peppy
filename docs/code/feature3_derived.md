# Learn derived attributes in `peppy`

This vignette will show you how and why to use the derived attributes functionality of the `peppy` package.

 - basic information about the PEP concept on the [project website](https://pepkit.github.io/).

 - broader theoretical description in the derived attributes [documentation section](http://pep.databio.org/en/2.0.0/specification/#sample_modifiersderive).

## What are derived attributes?

Derived attributes allow you to construct sample attributes dynamically using patterns and variables from other columns in your sample table. This is especially useful for building file paths without having to repeat directory structures for every sample.

## Quick Start - Simple Example

Let's say you have samples with names like `sample1`, `sample2`, etc., and your data files follow a pattern like `/data/{sample_name}.fastq`. Instead of typing out the full path for each sample, you can use derived attributes.

**Your sample table (sample_table.csv):**
```csv
sample_name
sample1
sample2
sample3
```

**Your project config (project_config.yaml):**
```yaml
pep_version: "2.0.0"
sample_table: sample_table.csv
sample_modifiers:
  derive:
    attributes: [file_path]
    sources:
      my_source: /data/{sample_name}.fastq
```

**In your sample table, add the file_path column:**
```csv
sample_name,file_path
sample1,my_source
sample2,my_source
sample3,my_source
```

When peppy loads this PEP, it will automatically expand `my_source` using the pattern from your config, replacing `{sample_name}` with the actual sample name. The result:
- `sample1` → `/data/sample1.fastq`
- `sample2` → `/data/sample2.fastq`
- `sample3` → `/data/sample3.fastq`

That's it! The `my_source` identifier gets replaced with the pattern defined in your config, and any variables in curly braces (like `{sample_name}`) get replaced with values from that sample's row.

## Advanced Example - Multiple Sources

The example below demonstrates how to use derived attributes in a more complex scenario with **multiple data sources and multiple variables**. Please consider the example below for reference:


```python
examples_dir = "../tests/data/example_peps-cfg2/example_derive/"
sample_table_pre = examples_dir + "sample_table_pre.csv"
%cat $sample_table_pre | column -t -s, | cat
```

    sample_name  protocol  organism  time  file_path
    pig_0h       RRBS      pig       0     data/lab/project/pig_0h.fastq
    pig_1h       RRBS      pig       1     data/lab/project/pig_1h.fastq
    frog_0h      RRBS      frog      0     data/lab/project/frog_0h.fastq
    frog_1h      RRBS      frog      1     data/lab/project/frog_1h.fastq


## Solution
As the name suggests the attributes in the specified attributes (here: `file_path`) can be derived from other ones. The way how this process is carried out is indicated explicitly in the `project_config.yaml` file (presented below). The name of the column is determined in the `sample_modifiers.derive.attributes` key-value pair, whereas the pattern for the attributes construction - in the `sample_modifiers.derive.sources` one. Note that the second level key (here: `source`) has to exactly match the attributes in the `file_path` column of the modified `sample_annotation.csv` (presented below).


```python
project_config = examples_dir + "project_config.yaml"
%cat $project_config | column -t -s, | cat
```

    pep_version: "2.0.0"
    sample_table: sample_table.csv
    output_dir: "$HOME/hello_looper_results"
    sample_modifiers:
      derive:
        attributes: [file_path]
        sources:
          source1: $HOME/data/lab/project/{organism}_{time}h.fastq
          source2: /path/from/collaborator/weirdNamingScheme_{external_id}.fastq


Let's introduce a few modifications to the original `sample_annotation.csv` file to map the appropriate data sources from the `project_config.yaml` with attributes in the derived column - `[file_path]`:


```python
examples_dir = "../tests/data/example_peps-cfg2/example_derive/"
sample_table = examples_dir + "sample_table.csv"
%cat $sample_table | column -t -s, | cat
```

    sample_name  protocol  organism  time  file_path
    pig_0h       RRBS      pig       0     source1
    pig_1h       RRBS      pig       1     source1
    frog_0h      RRBS      frog      0     source1
    frog_1h      RRBS      frog      1     source1


## Code
Import `peppy` and read in the project metadata by specifying the path to the `project_config.yaml`:


```python
from peppy import Project
p = Project(project_config)
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
      <td>/Users/mstolarczyk/data/lab/project/pig_0h.fastq</td>
      <td>pig</td>
      <td>RRBS</td>
      <td>pig_0h</td>
      <td>0</td>
    </tr>
    <tr>
      <th>pig_1h</th>
      <td>/Users/mstolarczyk/data/lab/project/pig_1h.fastq</td>
      <td>pig</td>
      <td>RRBS</td>
      <td>pig_1h</td>
      <td>1</td>
    </tr>
    <tr>
      <th>frog_0h</th>
      <td>/Users/mstolarczyk/data/lab/project/frog_0h.fastq</td>
      <td>frog</td>
      <td>RRBS</td>
      <td>frog_0h</td>
      <td>0</td>
    </tr>
    <tr>
      <th>frog_1h</th>
      <td>/Users/mstolarczyk/data/lab/project/frog_1h.fastq</td>
      <td>frog</td>
      <td>RRBS</td>
      <td>frog_1h</td>
      <td>1</td>
    </tr>
  </tbody>
</table>



As you can see, the resulting samples are annotated the same way as if they were read from the original, unwieldy, annotations file.
