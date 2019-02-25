Changelog
******************************

- **v0.20** (*unreleased*):

  - Changed

    - Make the attribute value matching more strict (require perfect match.)
    
    - Change the parameter names: ``exclude_samples`` and ``include_samples`` to ``selector_exclude`` and ``selector_include``, respectively.

    - Remove Python 3.4 support.

    - Begin using the ``attmap`` project for implementation of what's been called ``AttributeDict``.

  - New
  
    - Add ``selector_attribute`` parameter to ``fetch_samples`` function to enable more general applicability.


- **v0.19** (*2019-01-16*):

  - Changed

    - ``Project`` construction no longer requires sample annotations sheet.

    - Specification of assembly/ies in project config outside of ``implied_attributes``  is deprecated.

    - ``implied_columns`` and ``derived_columns`` are deprecated in favor of ``implied_attributes`` and ``derived_attributes``.

    - use ``divvy`` for computing environment configuration

  - New
    
    - Added ``activate_subproject`` method to ``Project``.


- **v0.18.2** (*2018-07-23*):

  - Fixed

    - Made requirements more lenient to allow for newer versions of required packages.


- **v0.18.1** (*2018-06-29*):

  - Fixed

    - Fixed a bug that would cause sample attributes to lose order.

    - Fixed a bug that caused an install error with newer ``numexpr`` versions.

  - New

    - Project names are now inferred with the ``infer_name`` function, which uses a priority lookup to infer the project name: First, the ``name`` attribute in the ``yaml`` file; otherwise, the containing folder unless it is ``metadata``, in which case, it's the parent of that folder.

    - Add ``get_sample`` and ``get_samples`` functions to ``Project`` objects.

    - Add ``get_subsamples`` and ``get_subsample`` functions to both ``Project`` and ``Sample`` objects.

    - Subsamples are now objects that can be retrieved individually by name, with the ``subsample_name`` as the index column header.

- **v0.17.2** (*2018-04-03*):

  - Fixed

    - Ensure data source path relativity is with respect to project config file's folder.

- **v0.17.1** (*2017-12-21*):

  - Changed

    - Version bump for first pypi release

    - Fixed bug with packaging for pypi release


- **v0.9** (*2017-12-21*):

  - New

    - Separation completed, ``peppy`` package is now standalone

    - ``looper`` can now rely on ``peppy``

  - Changed

    - ``merge_table`` renamed to ``sample_subannotation``

    - setup changed for compatibility with Pypi

- **v0.8.1** (*2017-11-16*):

  - New

    - Separated from looper into its own python package (originally called `pep`).

- **v0.7.2** (*2017-11-16*):

  - Fixed
  
    - Correctly count successful command submissions when not using `--dry-run`.

- **v0.7.1** (*2017-11-15*):

  - Fixed
  
    - No longer falsely display that there's a submission failure.
      
    - Allow non-string values to be unquoted in the ``pipeline_args`` section.

- **v0.7** (*2017-11-15*):

  - New
      
    - Add ``--lump`` and ``--lumpn`` options
    
    - Catch submission errors from cluster resource managers
    
    - Implied columns can now be derived
    
    - Now protocols can be specified on the command-line `--include-protocols`
    
    - Add rudimentary figure summaries
    
    - Simplifies command-line help display
    
    - Allow wildcard protocol_mapping for catch-all pipeline assignment
    
    - Improve user messages
    
    - New sample_subtypes section in pipeline_interface
    
  - Changed
  
    - Sample child classes are now defined explicitly in the pipeline interface. Previously, they were guessed based on presence of a class extending Sample in a pipeline script.
    
    - Changed 'library' key sample attribute to 'protocol'

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
