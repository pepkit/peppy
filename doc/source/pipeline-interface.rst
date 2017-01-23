
Pipeline interface YAML
**************************************************

The pipeline interface file describes how looper, which submits jobs, knows what arguments to pass to the pipeline and (possibly) what resources to request. For each pipeline (defined by the filename of the script itself), you specify some optional and required variables:

- **name (recommended)**: Name of the pipeline
- **arguments (required)**: List of key-value pairs of arguments, and attribute sources to pass to the pipeline (details below).
- **resources (required)**: A section outlining how much memory, CPU, and clock time to request, modulated by input file size (details below)
- **required_input_files (optional)**: A list of sample attributes (annotation sheets column names) that will point to input files that must exist.
- **all_input_files (optional)**: A list of sample attributes (annotation sheets column names) that will point to input files that are not required, but if they exist, should be counted in the total size calculation for requesting resources.
- **ngs_input_files (optional)**: A list of sample attributes (annotation sheets column names) that will point to input files to be used for automatic detection of read_length and read_type.

Example:

.. code-block:: yaml

	pipeline_script.py:  # this is variable (script filename)
	  name: value  # used for assessing pipeline flags (optional)
	  looper_args: True
	  arguments:
	    "-k" : value
	    "--key2" : value
	    "--key3" : null # value-less argument flags
	  resources:
	    default:
	      file_size: "0"
	      cores: "4"
	      mem: "6000"
	      time: "2-00:00:00"
	      partition: "longq"
	    resource_package_name:
	      file_size: "0"
	      cores: "4"
	      mem: "6000"
	      time: "2-00:00:00"
	      partition: "longq"

``arguments`` - the key corresponds verbatim to the string that will be passed on the command line to the pipeline. The value corresponds to an attribute of the sample, which will be derived from the sample_annotation csv file (in other words, it's a column name of your sample annotation sheet).

In addition to arguments you specify here, you may include ``looper_args: True`` and then looper will automatically add arguments for:

- **-C**: config_file (the pipeline config file specified in the project config file; or the default config file, if it exists)
- **-P**: cores (the number of cores specified by the resource package chosen)
- **-M**: mem (the memory limit)

``resources`` - You must define at least 1 option named 'default' with ``file_size`` = 0. Add as many additional resource sets as you want, with any names.
The looper will determine which resource package to use based on the ``file_size`` of the input file. It will select the lowest resource package whose ``file_size`` attribute does not exceed the size of the input file.

Example:

.. code-block:: yaml

	rrbs.py:
	  name: RRBS
	  looper_args: True
	  arguments:
	    "--sample-name": sample_name
	    "--genome": genome
	    "--input": data_path
	    "--single-or-paired": read_type
	  resources:
	    default:
	      file_size: "0"
	      cores: "4"
	      mem: "4000"
	      time: "2-00:00:00"
	      partition: "longq"
	    high:
	      file_size: "4"
	      cores: "6"
	      mem: "4000"
	      time: "2-00:00:00"
	      partition: "longq"

	rnaBitSeq.py:
	  looper_args: True
	  arguments:
	    "--sample-name": sample_name
	    "--genome": transcriptome
	    "--input": data_path
	    "--single-or-paired": read_type

	  resources:
	    default:
	      file_size: "0"
	      cores: "6"
	      mem: "6000"
	      time: "2-00:00:00"
	      partition: "longq"

	atacseq.py:
	  arguments:
	    "--sample-yaml": yaml_file
	    "-I": sample_name
	    "-G": genome
	  looper_args: True
	  resources:
	    default:
	      file_size: "0"
	      cores: "4"
	      mem: "8000"
	      time: "08:00:00"
	      partition: "shortq"
