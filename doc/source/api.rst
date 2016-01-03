API
===

This page contains a comprehensive list of all functions within ``pipelines``.
Docstrings should provide sufficient understanding for any individual function.

pipelines.Models
-----------------------

models.AttributeDict
***********************

.. currentmodule:: pipelines.models.AttributeDict
.. autosummary::
   add_entries

models.Project
***********************

.. currentmodule:: pipelines.models.Project
.. autosummary::
   parse_config_file
   make_project_dirs
   set_project_permissions
   add_sample_sheet
   add_sample


models.SampleSheet
***********************

.. currentmodule:: pipelines.models.SampleSheet
.. autosummary::
   check_sheet
   make_sample
   make_samples
   as_data_frame
   to_csv

models.Sample
***********************

.. currentmodule:: pipelines.models.Sample
.. autosummary::
   update
   check_valid
   generate_name
   as_series
   to_yaml
   locate_data_source
   get_genome
   set_file_paths
   make_sample_dirs
   check_input_exists
   get_read_type

models.PipelineInterface
************************

.. currentmodule:: pipelines.models.PipelineInterface
.. autosummary::
   select_pipeline
   get_pipeline_name
   choose_resource_package
   get_arg_string

models.ProtocolMapper
***********************

.. currentmodule:: pipelines.models.ProtocolMapper
.. autosummary::
   build_pipeline
   parse_parallel_jobs
   register_job

models.CommandChecker
***********************

.. currentmodule:: pipelines.models.CommandChecker
.. autosummary::
	check_command


Definitions
-----------------------

.. automodule:: pipelines
   :members:

.. automodule:: pipelines.models
   :members:
