# Advanced features

## Handling multiple input files
Sometimes you have multiple input files that you want to merge for one sample. 
For example, a common use case is a single library that was spread across multiple sequencing lanes, 
yielding multiple input files that need to be merged and then run through the pipeline as one unit. 
Rather than putting multiple lines in your sample annotation sheet, which causes conceptual and analytical challenges, 
we introduce **two ways to merge inputs**:

1. Use *shell expansion characters* (`*` or `[]`) in your `data_source` definition or filename; 
for relatively simple merge cases this works well.
2. Specify a *merge table*, which maps input files to samples for samples with more than one input file. 
To accommodate complex merger use cases, this is infinitely customizable.

To do the first option, simply change data source specification:

```yaml
data_sources:
  data_R1: "${DATA}/{id}_S{nexseq_num}_L00*_R1_001.fastq.gz"
  data_R2: "${DATA}/{id}_S{nexseq_num}_L00*_R2_001.fastq.gz"
```

For the second option, provide *in the `metadata` section* of your project config file a path to merge table file:

```yaml
metadata:
  merge_table: mergetable.csv
```

Make sure the `sample_name` column of this table matches, and then include any columns needed to point to the data. 
Looper will automatically include all of these files as input passed to the pipelines. 

***Warning***: do not use *both* of these options for the same sample at the same time; that will lead to multiple mergers.

**Note**: mergers are *not* the way to handle different functional/conceptual *kinds* of input files (e.g., `read1` and `read2` for a sample sequenced with a paired-end protocol). 
Such cases should be handled as *separate derived columns* in the main sample annotation sheet if they're different arguments to the pipeline.


## Connecting to multiple pipelines

If you have a project that contains samples of different types, then you may need to specify multiple pipeline repositories to your project. 
Starting in version 0.5, looper can handle a priority list of pipelines. 
Starting with version 0.6, each path should be directly to a pipeline interface file.

**Example**:

```yaml
metadata:
  pipeline_interfaces: [pipeline_iface1.yaml, pipeline_iface2.yaml]
```

In this case, for a given sample, `looper` will first look in `pipeline_iface1.yaml` 
to see if an appropriate (i.e., protocol-matched) pipeline exists for this sample type. 
If one is found, `looper` will use that pipeline (or set of pipelines, as specified in the `protocol_mapping`). 
Once a pipeline is submitted any remaining interface files will be ignored. 
Until an appropriate pipeline is found, each interface file will be considered in succession. 
If no suitable pipeline is found in any interface, the sample will be skipped. 
In other words, the `pipeline_interfaces` value specifies a *prioritized* search list.
