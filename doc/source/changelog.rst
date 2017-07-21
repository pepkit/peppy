Changelog
******************************

- **v0.6** (*2017-07-21*):

  - New

    - Add support for implied_column section of the project config file

    - Add support for Python 3

    - Merges pipeline interface and protocol mappings. This means we now allow direct pointers to ``pipeline_interface.yaml`` files, increasing flexibility, so this relaxes the specified folder structure that was previously used for ``pipelines_dir`` (with ``config`` subfolder).

    - Allow URLs as paths to sample sheets.

    - Allow tsv format for sample sheets.
  
    - Checks that the path to a pipeline actually exists before writing the submission script. 

  - Changed

    - Changed LOOPERENV environment variable to PEPENV, generalizing it to generic models

    - Changed name of ``pipelines_dir`` to ``pipeline_interfaces`` (but maintained backwards compatibility for now).

    - Changed name of ``run`` column to ``toggle``, since ``run`` can also refer to a sequencing run.

    - Relaxes many constraints (like resources sections, pipelines_dir columns), making project configuration files useful outside looper. This moves us closer to dividing models from looper, and improves flexibility.

    - Various small bug fixes and dev improvements.

    - Require `setuptools` for installation, and `pandas 0.20.2`. If `numexpr` is installed, version `2.6.2` is required.

    - Allows tilde in ``pipeline_interfaces``

- **v0.5** (*2017-03-01*):

  - New

    - Add new looper version tracking, with `--version` and `-V` options and printing version at runtime

    - Add support for asterisks in file paths

    - Add support for multiple pipeline directories in priority order

    - Revamp of messages make more intuitive output

    - Colorize output

    - Complete rehaul of logging and test infrastructure, using logging and pytest packages

  - Changed

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

  - Changed

    - Removed requirement to have ``pipelines`` repository installed in order to extend base Sample objects

    - Maintenance of sample attributes as provided by user by means of reading them in as strings (to be improved further)

    - Improved serialization of Sample objects
