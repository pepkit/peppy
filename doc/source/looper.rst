
Looper
=========================

``Looper`` is a program designed to run pipelines using the configuration files and the pipelines.

Once you have a project configuration file, you're ready to run your samples in an automated way in loop.

Looper supports submitting jobs in computing enviroonment (from a single computer to a high-performance cluster) through configuration of its config files (see :doc:`config-files`).


Usage
------------------------

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
