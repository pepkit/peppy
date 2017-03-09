Changelog
******************************

- **v0.5** (*2017-03-01*):

  - New

    - Add new looper version tracking, with `--version` and `-V` options and printing version at runtime

    - Add support for asterisks in file paths

    - Add support for multiple pipeline directories in priority order

    - Revamp of messages make more intuitive output

    - Colorize output

    - Complete rehaul of logging and test infrastructure, using logging and pytest packages

  - Fixes

    - Removes pipelines_dir requirement for models, making it useful outside looper

    - Small bug fixes related to `all_input_files` and `required_input_files` attributes
    
    - More robust installation and more explicit requirement of Python 2.7


- **v0.4** (*2017-01-12*):

  - New

    - New command-line interface (CLI) based on sub-commands

    - New subcommand (``looper summarize``) replacing the ``summarizePipelineStats.R`` script

    - New subcommand (``looper check``) replacing the ``flagCheck.sh`` script

    - New command (``looper destroy``) to remove all output of a project

    - New command (``looper clean``) to remove intermediate files of a project flagged for deletion

    - Support for portable and pipeline-independent allocation of computing resources with Looperenv.

  - Fixes

    - Removed requirement to have ``pipelines`` repository installed in order to extend base Sample objects

    - Maintenance of sample attributes as provided by user by means of reading them in as strings (to be improved further)

    - Improved serialization of Sample objects
