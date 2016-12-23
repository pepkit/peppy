Usage and commands
******************************

.. warning:: This usage block is outdated

.. code-block:: bash

   usage: looper.py [-h] [-c CONF_FILE] [--sp SUBPROJECT] [-d] [-t TIME_DELAY]
                    [--file-checks] [-pd PARTITION] [--cmd COMMAND]

   Looper

   optional arguments:
     -h, --help            show this help message and exit
     -c CONF_FILE, --config-file CONF_FILE       Supply config file [-c].
     --sp SUBPROJECT       Supply subproject
     -d, --dry-run         Don't actually submit.
     -t TIME_DELAY, --time-delay TIME_DELAY       Time delay in seconds between job submissions.
     --file-checks         Perform input file checks. Default=False.
     -pd PARTITION
     --cmd COMMAND


Looper doesn't just run pipelines, it can also do other things: 

- ``looper run``:  Runs pipelines for each sample, for each pipeline. This will use your ``compute`` settings to build and submit scripts to your specified compute environment, or run them sequentially on your local computer.

- ``looper destroy``: Deletes all output results for this project.

- ``looper summarize``: Summarize your project results. This command parses all key-value results reported in the each sample `stats.tsv` and collates them into a large summary matrix, which it saves in the project output directory. This creates such a matrix for each pipeline type run on the project, and a combined master summary table.

- ``looper check``: Checks the run progress of the current project. This will display a summary of job status; which pipelines are currently running on which samples, which have completed, which have failed, etc.

- ``looper monitor``: (in progress)

See https://github.com/epigen/looper/issues/4 for discussion.