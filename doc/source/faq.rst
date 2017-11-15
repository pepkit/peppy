FAQ
=========================

- Why isn't the ``looper`` executable in my path?
	By default, Python packages are installed to ``~/.local/bin``. You can add this location to your path by appending it (``export PATH=$PATH:~/.local/bin``).

- How can I run my jobs on a cluster?
	See :ref:`cluster resource managers <cluster-resource-managers>`.

- Which configuration file has which settings?
	Here's a list: :doc:`config files <config-files>`

- What's the difference between `looper` and `pypiper`?
	`Pypiper <http://pypiper.readthedocs.io/>`_ and `Looper <http://looper.readthedocs.io/>`_ work together as a comprehensive pipeline management system. `Pypiper <http://pypiper.readthedocs.io/>`_ builds individual, single-sample pipelines that can be run one sample at a time. `Looper <http://looper.readthedocs.io/>`_ then processes groups of samples, submitting appropriate pipelines to a cluster or server. The two projects are independent and can be used separately, but they are most powerful when combined.

- Why isn't looper submitting my pipeline: ``Not submitting, flag found: ['*_completed.flag']``?
	When using ``looper run``, looper first checks the sample output for flag files (which can be `_completed.flag`, or `_running.flag`, or `_failed.flag`). Typically, we don't want to resubmit a job that's already running or already finished, so by default, looper **will not submit a job when it finds a flag file**. This is what the message above is indicating. If you do in fact want to re-rerun a sample (maybe you've updated the pipeline, or you want to run restart a failed attempt), you can do so by just passing ``--ignore-flags`` to looper at startup. This will skip the flag check **for all samples**. If you only want to re-run or restart a few samples, it's best to just delete the flag files for the samples you want to restart, then use ``looper run`` as normal.

- How can I resubmit a subset of jobs that failed?
	By default, looper **will not submit a job that has already run**. If you want to re-rerun a sample (maybe you've updated the pipeline, or you want to run restart a failed attempt), you can do so by passing ``--ignore-flags`` to looper at startup, but this will **resubmit all samples**. If you only want to re-run or restart a few samples, it's best to just delete the flag files manually for the samples you want to restart, then use ``looper run`` as normal.	
