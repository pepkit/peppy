
# Subprojects

The PEP that this example is based on is available in the [`example_peps` repsitory](https://github.com/pepkit/example_peps) 
in the [`example_subprojects1` folder](https://github.com/pepkit/example_peps/tree/master/example_subprojects1).

The example below demonstrates how and why to use implied attributes functionality to **define numerous similar projects in a single project config file**. This functionality is extremely convenient when one has to define projects with small settings discreptancies, like different attributes in the annotation sheet. For example libraries `ABCD` and `EFGH` instead of the original `RRBS`.

Import libraries and set the working directory:


```python
import os
import peppy
os.chdir("/Users/mstolarczyk/Uczelnia/UVA/")
```

## Code

Read in the project metadata by specifying the path to the `project_config.yaml`


```python
p_subproj = peppy.Project("example_peps/example_subprojects1/project_config.yaml")
```

To see whether there are any subprojects available within the `project_config.yaml` file run the following command:

Let's inspect the sample annotation sheet.


```python
p_subproj.sheet
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>sample_name</th>
      <th>library</th>
      <th>organism</th>
      <th>time</th>
      <th>file_path</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>pig_0h</td>
      <td>RRBS</td>
      <td>pig</td>
      <td>0</td>
      <td>source1</td>
    </tr>
    <tr>
      <th>1</th>
      <td>pig_1h</td>
      <td>RRBS</td>
      <td>pig</td>
      <td>1</td>
      <td>source1</td>
    </tr>
    <tr>
      <th>2</th>
      <td>frog_0h</td>
      <td>RRBS</td>
      <td>frog</td>
      <td>0</td>
      <td>source1</td>
    </tr>
    <tr>
      <th>3</th>
      <td>frog_1h</td>
      <td>RRBS</td>
      <td>frog</td>
      <td>1</td>
      <td>source1</td>
    </tr>
  </tbody>
</table>
</div>




```python
p_subproj.subprojects
```




    {'newLib': {'metadata': {'sample_annotation': 'sample_annotation_newLib.csv'}}, 'newLib2': {'metadata': {'sample_annotation': 'sample_annotation_newLib2.csv'}}}



As you can see, there are two subprojects available: `newLib` and `newLib2`. Nonetheless, only the main opne is "active".

Each of subprojects can be activated with the following command:


```python
p_subproj.activate_subproject("newLib")
p_subproj.activate_subproject("newLib2")
```

Let's inspect the sample annotation sheet when the `newLib2` subproject is active.


```python
p_subproj.sheet
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>sample_name</th>
      <th>library</th>
      <th>organism</th>
      <th>time</th>
      <th>file_path</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>pig_0h</td>
      <td>EFGH</td>
      <td>pig</td>
      <td>0</td>
      <td>source1</td>
    </tr>
    <tr>
      <th>1</th>
      <td>pig_1h</td>
      <td>EFGH</td>
      <td>pig</td>
      <td>1</td>
      <td>source1</td>
    </tr>
    <tr>
      <th>2</th>
      <td>frog_0h</td>
      <td>EFGH</td>
      <td>frog</td>
      <td>0</td>
      <td>source1</td>
    </tr>
    <tr>
      <th>3</th>
      <td>frog_1h</td>
      <td>EFGH</td>
      <td>frog</td>
      <td>1</td>
      <td>source1</td>
    </tr>
  </tbody>
</table>
</div>



## The PEP

The `library` attribute in each sample has changed from `RRBS` to `EFGH`. This behavior was specified in the `project_config.yaml` that points to a different `sample_annotation_newLib2.csv` with changed `library` attribute.


```python
with open("example_peps/example_subprojects1/project_config.yaml") as f:
    print(f.read())
```

    metadata:
        sample_annotation: sample_annotation.csv
        output_dir: $HOME/hello_looper_results
    
    derived_attributes: [file_path]
    data_sources:
        source1: /data/lab/project/{organism}_{time}h.fastq
        source2: /path/from/collaborator/weirdNamingScheme_{external_id}.fastq
    
    subprojects:
        newLib:
            metadata:
                sample_annotation: sample_annotation_newLib.csv
        newLib2:
            metadata:
                sample_annotation: sample_annotation_newLib2.csv
    
    



```python
with open("example_peps/example_subprojects1/sample_annotation_newLib2.csv") as f:
    print(f.read())
```

    sample_name,library,organism,time,file_path
    pig_0h,EFGH,pig,0,source1
    pig_1h,EFGH,pig,1,source1
    frog_0h,EFGH,frog,0,source1
    frog_1h,EFGH,frog,1,source1
    

