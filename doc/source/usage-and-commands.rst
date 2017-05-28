Usage and commands
******************************


Looper doesn't just run pipelines; it can also check and summarize the progress of your jobs, as well as remove all files created by them.

Each task is controlled by one of the five main commands ``run``, ``summarize``, ``destroy``, ``check``, ``clean``:


.. code-block:: bash

  usage: looper [-h] [-V] {run,summarize,destroy,check,clean} ...

  looper - Loop through samples and submit pipelines for them.

  positional arguments:
    {run,summarize,destroy,check,clean}
      run                 Main Looper function: Submit jobs for samples.
      summarize           Summarize statistics of project samples.
      destroy             Remove all files of the project.
      check               Checks flag status of current runs.
      clean               Runs clean scripts to remove intermediate files of
                          already processed jobs.

  optional arguments:
    -h, --help            show this help message and exit
    -V, --version         show program's version number and exit

  For subcommand-specific options, type: 'looper <subcommand> -h'
  https://github.com/epigen/looper


- ``looper run``:  Runs pipelines for each sample, for each pipeline. This will use your ``compute`` settings to build and submit scripts to your specified compute environment, or run them sequentially on your local computer.


.. code-block:: bash

  usage: looper run [-h] [-t TIME_DELAY] [--ignore-flags] [-pd PARTITION]
                    [--file-checks] [-d] [--sp SUBPROJECT]
                    config_file

  positional arguments:
    config_file           Project YAML config file.

  optional arguments:
    -h, --help            show this help message and exit
    -t TIME_DELAY, --time-delay TIME_DELAY
                          Time delay in seconds between job submissions.
    --ignore-flags        Ignore run status flags? Default: false. By default,
                          pipelines will not be submitted if a pypiper flag file
                          exists marking the run (e.g. as 'running' or
                          'failed'). Set this option to ignore flags and submit
                          the runs anyway.
    -pd PARTITION
    --file-checks         Perform input file checks. Default=True.
    -d, --dry-run         Don't actually submit.
    --sp SUBPROJECT       Supply subproject


- ``looper summarize``: Summarize your project results. This command parses all key-value results reported in the each sample `stats.tsv` and collates them into a large summary matrix, which it saves in the project output directory. This creates such a matrix for each pipeline type run on the project, and a combined master summary table.

.. code-block:: bash

  usage: looper summarize [-h] [--file-checks] [-d] [--sp SUBPROJECT]
                          config_file

  positional arguments:
    config_file      Project YAML config file.

  optional arguments:
    -h, --help       show this help message and exit
    --file-checks    Perform input file checks. Default=True.
    -d, --dry-run    Don't actually submit.
    --sp SUBPROJECT  Supply subproject


- ``looper check``: Checks the run progress of the current project. This will display a summary of job status; which pipelines are currently running on which samples, which have completed, which have failed, etc.

.. code-block:: bash

  usage: looper check [-h] [--file-checks] [-d] [--sp SUBPROJECT] config_file

  positional arguments:
    config_file      Project YAML config file.

  optional arguments:
    -h, --help       show this help message and exit
    --file-checks    Perform input file checks. Default=True.
    -d, --dry-run    Don't actually submit.
    --sp SUBPROJECT  Supply subproject


- ``looper destroy``: Deletes all output results for this project.

.. code-block:: bash

  usage: looper destroy [-h] [--file-checks] [-d] [--sp SUBPROJECT] config_file

  positional arguments:
    config_file      Project YAML config file.

  optional arguments:
    -h, --help       show this help message and exit
    --file-checks    Perform input file checks. Default=True.
    -d, --dry-run    Don't actually submit.
    --sp SUBPROJECT  Supply subproject


- ``looper monitor``: (in progress)

See https://github.com/epigen/looper/issues/4 for discussion.
