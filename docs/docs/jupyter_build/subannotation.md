
# Sample subannotation

The PEPs that this examples are based on are available in the [example_peps repsitory](https://github.com/pepkit/example_peps).

This vignette will show you how sample subannotations work in a series of examples.

Import libraries and set the working directory


```python
import os
import peppy
os.chdir("/Users/mstolarczyk/Uczelnia/UVA/")
```

## Example 1: basic sample subannotation table

Example 1 demonstrates how a `sample_subannotation` is used. In this example, 2 samples have multiple input files that need merging (`frog_1` and `frog_2`), while 1 sample (`frog_3`) does not. Therefore, `frog_3` specifies its file in the `sample_annotation` table, while the others leave that field blank and instead specify several files in the `sample_subannotation`.


```python
p1 = peppy.Project("example_peps/example_subannotation1/project_config.yaml")
p1.samples[0].file
```




    'data/frog1a_data.txt data/frog1b_data.txt data/frog1c_data.txt'




```python
ss = p1.get_subsample(sample_name="frog_1", subsample_name="sub_a")
print(type(ss))
print(ss)
```

    <class 'peppy.sample.Subsample'>
    Subsample: {'sample_name': 'frog_1', 'subsample_name': 'sub_a', 'file': 'data/frog1a_data.txt'}


## Example 2: subannotations and derived columns

Example 2 uses a `sample_subannotation` table and a derived column to point to files. This is a rather complex example. Notice we must include the `file_id` column in the `sample_annotation` table, and leave it blank; this is then populated by just some of the samples (`frog_1` and `frog_2`) in the `sample_subannotation`, but is left empty for the samples that are not merged.


```python
import peppy
p2 = peppy.Project("example_peps/example_subannotation2/project_config.yaml")
p2.samples[0].file
```




    '/Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation2/../data/frog1a_data.txt /Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation2/../data/frog1b_data.txt /Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation2/../data/frog1c_data.txt'




```python
p2.samples[1].file
```




    '/Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation2/../data/frog2a_data.txt /Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation2/../data/frog2b_data.txt'




```python
p2.samples[2].file
```




    '/Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation2/../data/frog3_data.txt'




```python
p2.samples[3].file
```




    '/Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation2/../data/frog4_data.txt'



## Example 3: subannotations and expansion characters

This example gives the exact same results as example 2, but in this case, uses a wildcard for `frog_2` instead of including it in the `sample_subannotation` table. Since we can't use a wildcard and a subannotation for the same sample, this necessitates specifying a second data source class (`local_files_unmerged`) that uses an asterisk. The outcome is the same.



```python
p3 = peppy.Project("example_peps/example_subannotation3/project_config.yaml")
p3.samples[0].file
```




    '/Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation3/../data/frog1a_data.txt /Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation3/../data/frog1b_data.txt /Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation3/../data/frog1c_data.txt'




```python
p3.samples[1].file
```




    '/Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation3/../data/frog2_data.txt /Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation3/../data/frog2a_data.txt /Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation3/../data/frog2b_data.txt'




```python
p3.samples[2].file
```




    '/Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation3/../data/frog3_data.txt'




```python
p3.samples[3].file
```




    '/Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation3/../data/frog4_data.txt'



## Example 4: subannotations and multiple (separate-class) inputs

Merging is for same class inputs (like, multiple files for read1). Different-class inputs (like read1 vs read2) are handled by different attributes (or columns). This example shows you how to handle paired-end data, while also merging within each.


```python
p4 = peppy.Project("example_peps/example_subannotation4/project_config.yaml")
p4.samples[0].read1
```




    'frog1a_data.txt frog1b_data.txt frog1c_data.txt'




```python
p4.samples[0].read2
```




    'frog1a_data2.txt frog1b_data2.txt frog1b_data2.txt'



## Example 5: subannotations and multiple (separate-class) inputs with derived columns

Merging is for same class inputs (like, multiple files for read1). Different-class inputs (like read1 vs read2) are handled by different attributes (or columns). This example shows you how to handle paired-end data, while also merging within each.


```python
p5 = peppy.Project("example_peps/example_subannotation5/project_config.yaml")
p5.samples[0].read1
```




    '/Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation5/../data/frog1a_R1.fq.gz /Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation5/../data/frog1b_R1.fq.gz /Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation5/../data/frog1c_R1.fq.gz'




```python
p5.samples[0].read2
```




    '/Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation5/../data/frog1a_R2.fq.gz /Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation5/../data/frog1b_R2.fq.gz /Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation5/../data/frog1c_R2.fq.gz'




```python
p5.samples[1].read1
```




    '/Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation5/../data/frog2_R1.fq.gz'




```python
p5.samples[1].read2
```




    '/Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation5/../data/frog2_R2.fq.gz'




```python
p5.samples[2].read1
```




    '/Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation5/../data/frog3_R1.fq.gz'




```python
p5.samples[2].read2
```




    '/Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation5/../data/frog3_R2.fq.gz'




```python
p5.samples[3].read1
```




    '/Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation5/../data/frog4_R1.fq.gz'




```python
p5.samples[3].read2
```




    '/Users/mstolarczyk/Uczelnia/UVA/example_peps/example_subannotation5/../data/frog4_R2.fq.gz'


