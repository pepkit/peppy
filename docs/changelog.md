# Changelog

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) and [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

## [0.35.3] -- 2022-11-16
### Fixed
- Returning `NaN` value in initialization project from pandas df

## [0.35.2] -- 2022-09-13
### Fixed

- Returning `NaN` value within `to_dict` method was fixed and method now returns `None` instead
## [0.35.1] -- 2022-09-07
### Changed
- Organization of test files. Separated unittests from smoketests.

### Fixed
- The root cause of `np.nan` values showing up in Pandas dataframes. Replaced the values with None right after reading the database, which made it possible to remove all custom `np.nan` to `None` converters used later in the code.
- Typing in some methods.
- Code redundancy in fixtures in conftest.

### Added
- New test cases with test data

## [0.35.0] -- 2022-08-25

### Changed 

- Optimized converting Projects to and from dict. Now, `to_dict(extended=True)` returns only essential properties to save space and time.
- Small refactors.

### Fixed

- Initialization of `peppy.Project` from `pandas.DataFrame`. Now `from_pandas()` can receive sample table, subsample table and config file
- Multiple bugs introduced during initialization of the project with custom index column names

### Added
- New test cases and test data

## [0.34.0] -- 2022-08-17

### Changed 

- Way of initialization project from dictionary. Now it's possible as follows: `Project().from_dict()`
- 
### Fixed

- Fix error that was raised when duplicated sample in `sample_table` had different read types (single-end mixed with paired-end).

### Added

- Feature of initializing `peppy.Project` from `pandas.DataFrame`

## [0.33.0] -- 2022-07-25

### Changed

- `pep_version` is no longer a required parameter to create a `peppy.Project` instance from a configuration file.

### Fixed

- Performance issues during sample parsing. Two list comprehensions were combined to speed up this functionality.
- `KeyError` is thrown when attempting to access the `pep_version` of a `peppy.Project` instance instatiated from a sample table (`csv`)

### Added

- Implementation of `__eq__` for the `peppy.Project` class such that two instances of the class can be compared using python's equality operators (`==`, `!=`).
- New `from_dict` function that lets a user instatiate a new `peppy.Project` object using an in-memory representation of a PEP (a `dict`). This supports database storage of PEPs.
- New `extended` flag for the `to_dict` method on `peppy.Project` objects. This creates a **richer** dictionary representation of PEPs.
- Better sample parsing

## [0.32.0] -- 2022-05-03

### Changed

- Unify exceptions related to remote YAML file reading in `read_yaml` function. Now always a `RemoteYAMLError` is thrown.
- `Project` dict representation

### Added

- Support for PEP `2.1.0`, whichi includes support for no YAML configuration file component (CSV only), automatic sample merging if there are any duplicates in sample table index column, and new project attributes: `sample_table_index` and `subsample_table_index`.

### Fixed

- Project string representation; [Issue 368](https://github.com/pepkit/peppy/issues/368)

## [0.31.2] -- 2021-11-04
### Fixed
- Bug with setuptools 58

## [0.31.1] -- 2021-04-15

### Added

- Support for remote URL config files

### Fixed

- Error when accessing `Project.subsample_table` property when no subsample tables were defined

## [0.31.0] - 2020-10-07

### Added

- `to_dict` method in `Sample` class that can include or exclude `Project` reference

## [0.30.3] - 2020-09-22

### Changed

- If there's just one `subsample_table` specified, `Project.subsample_table` property will return an object of `pandas.DataFrame` class rather than a `list` of ones

### Fixed

- `TypeError` when `subsample_table` is set to `null`

## [0.30.2] - 2020-08-06

### Added

- Support for multiple subsample tables
- License file to the package source distribution

## [0.30.1] - 2020-05-26

### Changed

- Package authors list

## [0.30.0] - 2020-05-26

**This version introduced backwards-incompatible changes.**

### Added

- attribute duplication functionality
- config importing functionality
- attribute removal functionality
- possibility to define multi-attribute rules in attribute implication

### Changed

- Project configuration file to follow [PEP2.0.0](http://pep.databio.org/en/2.0.0/specification/) specification. Browse the specification for changes related to config format
- Do not require `sample_name` attribute in the sample table

## [0.22.3] - 2019-12-13

### Changed

- Remove `is_command_callable` from `utils` module; instead, refer to [`ubiquerg`](https://pypi.org/project/ubiquerg/).
- It's now exceptional (rather than just a warning) for a sample table file to be missing a valid name column.

### Fixed

- Empty columns in subsample tables are treated just as empty columns in sample tables (respective attributes are not included rather than populated with `nan`)

## [0.22.2] - 2019-06-20

### Changed

- Remove `ngstk` requirement.

## [0.22.1] - 2019-06-19

### Changed

- Prohibit storing reference to full `Project` object on a `Sample`.

## [0.22.0] -- (2019-06-06)

### Changed

- Deprecate `Project` `constants` in favor of `constant_attributes.`
- Improved `Project` text representation for interactive/terminal display (`__repr__`): [Issue 296](https://github.com/pepkit/peppy/issues/296)

### Fixed

- Properly use `constant_attributes` if present from subproject. [Issue 292](https://github.com/pepkit/peppy/issues/292)
- Fixed a bug with subproject activation paths
- Revert deprecation of `sample_name` to `name`; so `sample_name` is again approved.

## [0.21.0] -- (2019-05-02)

### Added

- Support for Snakemake projects (particularly `SnakeProject`)
- Hook for `get_arg_string` on `Project` to omit some pipeline options/arguments from the returned argument string
- `sample_table` and `subsample_table` functions, providing a functional syntax for requesting the respective attribute values from a `Project`
- Hook on `merge_sample` for specifying name of subannotation column that stores name for each sample

### Changed

- Improved messaging: ["Unmatched regex-like"](https://github.com/pepkit/peppy/issues/223), ["Missing and/or empty attribute(s)"](https://github.com/pepkit/peppy/issues/282)
- On `Project`, `sheet` is deprecated in favor of `sample_table`.
- On `Project`, `sample_subannotation` is deprecated in favor of `subsample_table`.
- On `Sample`, reference to `sample_name` is deprecated in favor of simply `name`.

## [0.20.0] -- (2019-04-17)

### Added

- `subsample_table` on a `Project` gives the table of sample subannotation / "units" if applicable.

### Changed

- Add `attribute` parameter to `fetch_samples` function to enable more general applicability.
  Additionally, the attribute value matching is more strict now -- requires perfect match.
- Remove Python 3.4 support.
- Use `attmap` for implementation of attribute-style access into a key-value collection.
- Deprecate `sample_annotation` and `sample_subannotation` in favor of `sample_table` and `subsample_table`, respectively.

## [0.19.0] -- (2019-01-16)

### New

- Added `activate_subproject` method to `Project`.

### Changed

- `Project` construction no longer requires sample annotations sheet.
- Specification of assembly/ies in project config outside of `implied_attributes` is deprecated.
- `implied_columns` and `derived_columns` are deprecated in favor of `implied_attributes` and `derived_attributes`.

## [0.18.2] -- (2018-07-23)

### Fixed

- Made requirements more lenient to allow for newer versions of required packages.

## [0.18.1] -- (2018-06-29)

### Fixed

- Fixed a bug that would cause sample attributes to lose order.
- Fixed a bug that caused an install error with newer `numexpr` versions.

### New

- Project names are now inferred with the `infer_name` function, which uses a priority lookup to infer the project name: First, the `name` attribute in the `yaml` file; otherwise, the containing folder unless it is `metadata`, in which case, it's the parent of that folder.
- Add `get_sample` and `get_samples` functions to `Project` objects.
- Add `get_subsamples`and `get_subsample` functions to both `Project` and `Sample` objects.
- Subsamples are now objects that can be retrieved individually by name, with the `subsample_name` as the index column header.

## [0.17.2] -- (2018-04-03)

## Fixed

- Ensure data source path relativity is with respect to project config file's folder.

## [0.17.1] -- (2017-12-21)

### Changed

- Version bump for first pypi release
- Fixed bug with packaging for pypi release

## [0.9.0] -- (2017-12-21)

### New

- Separation completed, `peppy` package is now standalone
- `looper` can now rely on `peppy`

### Changed

- `merge_table` renamed to `sample_subannotation`
- setup changed for compatibility with PyPI

## [0.8.1] -- (2017-11-16)

### New

- Separated from looper into its own python package (originally called `pep`)

## [0.7.2] -- (2017-11-16)

### Fixed

- Correctly count successful command submissions when not using `--dry-run`.

## [0.7.1] -- (2017-11-15)

### Fixed

- No longer falsely display that there's a submission failure.
- Allow non-string values to be unquoted in the `pipeline_args` section.

## [0.7.0] -- (2017-11-15)

### New

- Add `--lump` and `--lumpn` options
- Catch submission errors from cluster resource managers
- Implied columns can now be derived
- Now protocols can be specified on the command-line `--include-protocols`
- Add rudimentary figure summaries
- Allow wildcard protocol_mapping for catch-all pipeline assignment
- New sample_subtypes section in pipeline_interface

### Changed

- Sample child classes are now defined explicitly in the pipeline interface. Previously, they were guessed based on presence of a class extending Sample in a pipeline script.
- Changed 'library' key sample attribute to 'protocol'
- Improve user messages
- Simplifies command-line help display

## [0.6.0] -- (2017-07-21)

### New

- Add support for implied_column section of the project config file
- Add support for Python 3
- Merges pipeline interface and protocol mappings. This means we now allow direct pointers to `pipeline_interface.yaml` files, increasing flexibility, so this relaxes the specified folder structure that was previously used for `pipelines_dir` (with `config` subfolder).
- Allow URLs as paths to sample sheets.
- Allow tsv format for sample sheets.
- Checks that the path to a pipeline actually exists before writing the submission script.

### Changed

- Changed LOOPERENV environment variable to PEPENV, generalizing it to generic models
- Changed name of `pipelines_dir` to `pipeline_interfaces` (but maintained backwards compatibility for now).
- Changed name of `run` column to `toggle`, since `run` can also refer to a sequencing run.
- Relaxes many constraints (like resources sections, pipelines_dir columns), making project configuration files useful outside looper. This moves us closer to dividing models from looper, and improves flexibility.
- Various small bug fixes and dev improvements.
- Require `setuptools` for installation, and `pandas 0.20.2`. If `numexpr` is installed, version `2.6.2` is required.
- Allows tilde in `pipeline_interfaces`

## [0.5.0] -- (2017-03-01)

### New

- Add new looper version tracking, with `--version` and `-V` options and printing version at runtime
- Add support for asterisks in file paths
- Add support for multiple pipeline directories in priority order
- Revamp of messages make more intuitive output
- Colorize output
- Complete rehaul of logging and test infrastructure, using logging and pytest packages

### Changed

- Removes pipelines_dir requirement for models, making it useful outside looper
- Small bug fixes related to `all_input_files` and `required_input_files` attributes
- More robust installation and more explicit requirement of Python 2.7

## [0.4.0] -- (2017-01-12)

### New

- New command-line interface (CLI) based on sub-commands
- New subcommand (`looper summarize`) replacing the `summarizePipelineStats.R` script
- New subcommand (`looper check`) replacing the `flagCheck.sh` script
- New command (`looper destroy`) to remove all output of a project
- New command (`looper clean`) to remove intermediate files of a project flagged for deletion
- Support for portable and pipeline-independent allocation of computing resources with Looperenv.

### Changed

- Removed requirement to have `pipelines` repository installed in order to extend base Sample objects
- Maintenance of sample attributes as provided by user by means of reading them in as strings (to be improved further
- Improved serialization of Sample objects
