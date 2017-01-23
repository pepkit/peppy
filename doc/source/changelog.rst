Changelog
******************************

- **v0.4** (*2017-01-12*):

  - New

    - New command-line interface (CLI) based on sub-commands

    - New subcommand (``looper summarize``) replacing the ``summarizePipelineStats.R`` script

    - New subcommand (``looper check``) replacing the ``flagCheck.sh`` script

    - New command (``looper destroy``) to remove all output of a project

    - Support for portable and pipeline-independent allocation of computing resources with Looperenv.

  - Fixes

    - Removed requirement to have ``pipelines`` repository installed in order to extend base Sample objects

    - Maintenance of sample attributes as provided by user by means of reading them in as strings (to be improved further)

    - Improved serialization of Sample objects
