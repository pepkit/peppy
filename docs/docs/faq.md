# FAQ

- Why isn't the `looper` executable available (on `PATH`)?
	
	By default, Python packages are installed to `~/.local/bin`. 
	You can add that location to your path by appending it (`export PATH=$PATH:~/.local/bin`).

- How can I run my jobs on a **cluster**?
	
	See the page about [cluster computing](cluster-computing.md)

- Which configuration file has which settings?
	
	There's a list on the [config files page](config-files.md)

- What's the difference between `looper` and `pypiper`?
	
	They complement one another, constituting a comprehensive pipeline management system. 
	
	[`pypiper`](http://pypiper.readthedocs.io) builds pipelines to process individual samples. 
	[`looper`](http://looper.readthedocs.io) operates groups of samples (as in a project), 
	submitting the appropriate pipeline(s) to a cluster or server (or running them locally). 
	
	The two projects are independent and can be used separately, but they are most powerful when combined.

- Why isn't a sample being processed by a pipeline (`Not submitting, flag found: ['*_<status>.flag']`)?
	
	When using the `run` subcommand, for each sample being processed `looper` first checks for *"flag" files* in the 
	sample's designated output folder for flag files (which can be `_completed.flag`, or `_running.flag`, or `_failed.flag`). 
	Typically, we don't want to resubmit a job that's already running or already finished, so by default, 
	`looper` **will *not* submit a job when it finds a flag file**. This is what the message above is indicating. 
	
	If you do in fact want to re-rerun a sample (maybe you've updated the pipeline, or you want to run restart a failed attempt), 
	you can do so by just passing to `looper` at startup the `--ignore-flags` option; this will skip the flag check **for *all* samples**.
	If you only want to re-run or restart a few samples, it's best to just delete the flag files for the samples you want to restart, then use `looper run` as normal.

- How can I **resubmit a *subset* of jobs** that failed?
	
	By default, `looper` **will *not* submit a job that has already run**. 
	If you want to re-rerun a sample (maybe you've updated the pipeline, or you want to restart a failed attempt), 
	you can do so by passing `--ignore-flags` to `looper` at startup. That will **resubmit *all* samples**, though. 
	If you only want to re-run or restart just a few samples, it's best to manually delete the "flag" files for the samples 
	you want to restart, then use `looper run` as normal.
