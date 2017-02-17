
Features
******************************

Simplicity for the beginning, power when you need to expand.

- **Flexible pipelines:**  Use looper with any pipeline, any library, in any domain. We designed it to work with `Pypiper <http://pypiper.readthedocs.io/>`_, but looper has an infinitely flexible command-line argument system that will let you configure it to work with  any script (pipeline) that accepts command-line arguments. You can also configure looper to submit multiple pipelines per sample.

- **Flexible compute:**  If you don't change any settings, looper will simply run your jobs serially. But Looper includes a templating system that will let you process your pipelines on any cluster resource manager (SLURM, SGE, etc.). We include default templates for SLURM and SGE, but it's easy to add your own as well. Looper also gives you a way to determine which compute queue/partition to submit on-the-fly, by passing the ``--compute`` parameter to your call to ``looper run``, making it simple to use by default, but very flexible if you have complex resource needs.

- **Standardized project definition:** Looper defines a flexible standard format for describing projects, and there are other tools that can read these same formats. For example, we are working on an R package that will read the same project definition and provide all your sample metadata (and pipeline results) in an R analysis environment, with no additional effort. With a standardized project definition, the possibilities are endless.

- **Subprojects:** Subprojects make it easy to define two very similar projects without duplicating project metadata.

- **Job completion monitoring:**  Looper is job-aware and will not submit new jobs for samples that are already running or finished, making it easy to add new samples to existing projects, or re-run failed samples.

- **Flexible input files:** Looper's *derived column* feature lets you easily use samples with input files on different file systems or from different projects, with different naming conventions. This also makes it easy to share projects across compute environments without having to change sample annotations.

- **Flexible resources:**  Looper has an easy-to-use resource requesting scheme. With a few lines to define CPU, memory, clock time, or anything else, pipeline authors can specify different computational resources depending on the size of the input sample and pipeline to run. Or, just use a default if you don't want to mess with setup.
