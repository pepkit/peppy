# Derived columns

On your sample sheet, you will need to point to the input file or files for each sample. 
Of course, you could just add a column with the file path, like `/path/to/input/file.fastq.gz`. For example:

A ***bad* example**:

```CSV
sample_name,library,organism,time,file_path
pig_0h,RRBS,pig,0,/data/lab/project/pig_0h.fastq
pig_1h,RRBS,pig,1,/data/lab/project/pig_1h.fastq
frog_0h,RRBS,frog,0,/data/lab/project/frog_0h.fastq
frog_1h,RRBS,frog,1,/data/lab/project/frog_1h.fastq
```

This is common, and it works in a pinch with Looper, but what if the data get moved, or your filesystem changes, or you switch servers or move institutes? 
Will this data still be there in 2 years? Do you want long file paths cluttering your annotation sheet? 
What if you have 2 or 3 input files? Do you want to manually manage these unwieldy absolute paths?

Looper makes it really easy to do better. You can make one or your annotation columns into a flexible *derived column* 
that will be populated based on a source template you specify in the project configuration file. 
What was originally `/long/path/to/sample.fastq.gz` would instead contain just a key, like `source1`. 
Columns that use a key like this are called *derived columns*. 
Here's an example of the same sheet using a derived column (`file_path`):

A ***good* example**:
```CSV
sample_name,library,organism,time,file_path
pig_0h,RRBS,pig,0,source1
pig_1h,RRBS,pig,1,source1
frog_0h,RRBS,frog,0,source1
frog_1h,RRBS,frog,1,source1
```

For this to succeed, your project config file must specify two things:
- Which columns are to be derived (in this case, ``file_path``)
- A `data_sources` section mapping keys to strings that will construct your path, like this:
    ```yaml
    derived_columns: [file_path]
    data_sources:
      source1: /data/lab/project/{sample_name}.fastq
      source2: /path/from/collaborator/weirdNamingScheme_{external_id}.fastq
    ```

That's it! The source string can use other sample attributes (columns) using braces, as in `{sample_name}`. 
The attributes will be automatically populated separately for each sample. 
To take this a step further, you'd get the same result with this config file, 
which substitutes `{sample_name}` for other sample attributes, `{organism}` and `{time}`:

```yaml
derived_columns: [file_path]
data_sources:
  source1: /data/lab/project/{organism}_{time}h.fastq
  source2: /path/from/collaborator/weirdNamingScheme_{external_id}.fastq
```

As long as your file naming system is systematic, you can easily deal with any external naming scheme, no problem at all. 
The idea is this: don't put *absolute* paths to files in your annotation sheet. 
Instead, specify a data source and then provide a regex in the config file. 

Then if your data change locations (which happens more often than we would like), or you change servers, 
or you want to share or publish the project, you just have to change the config file and not update paths in the annotation sheet. 
This makes the annotation sheet universal across environments, users, publication, etc. The whole project is now portable.

You can specify as many derived columns as you want. An expression including any sample attributes (using `{attribute}`) will be populated for each of those columns. 

Think of each sample as belonging to a certain type (for simple experiments, the type will be the same). 
Then define the location of these samples in the project configuration file. 
As a side bonus, you can easily include samples from different locations, and you can also use the same sample annotation sheet on different environments 
(i.e. servers or users) by having multiple project config files (or, better yet, by defining a `subproject` for each environment). 
The only thing you have to change is the project-level expression describing the location, not any sample attributes. 
Plus, you get to eliminate those annoying `long/path/arguments/in/your/sample/annotation/sheet`.

Check out the complete working example in the [`microtest` repository](https://github.com/databio/microtest/tree/master/config).
