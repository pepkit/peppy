""" Package constants """

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"

__all__ = ["ALL_INPUTS_ATTR_NAME", "COL_KEY_SUFFIX", "COMPUTE_SETTINGS_VARNAME",
           "DATA_SOURCE_COLNAME", "DATA_SOURCES_SECTION",
           "DEFAULT_COMPUTE_RESOURCES_NAME", "FLAGS",
           "GENERIC_PROTOCOL_KEY", "REQUIRED_INPUTS_ATTR_NAME",
           "SAMPLE_ANNOTATIONS_KEY", "SAMPLE_EXECUTION_TOGGLE",
           "SAMPLE_NAME_COLNAME", "SAMPLE_INDEPENDENT_PROJECT_SECTIONS",
           "VALID_READ_TYPES"]


COMPUTE_SETTINGS_VARNAME = "PEPENV"
DEFAULT_COMPUTE_RESOURCES_NAME = "default"
SAMPLE_NAME_COLNAME = "sample_name"
DATA_SOURCE_COLNAME = "data_source"
SAMPLE_ANNOTATIONS_KEY = "sample_annotation"
DATA_SOURCES_SECTION = "data_sources"
SAMPLE_EXECUTION_TOGGLE = "toggle"
VALID_READ_TYPES = ["single", "paired"]
REQUIRED_INPUTS_ATTR_NAME = "required_inputs_attr"
ALL_INPUTS_ATTR_NAME = "all_inputs_attr"
FLAGS = ["completed", "running", "failed", "waiting", "partial"]
GENERIC_PROTOCOL_KEY = "*"
SAMPLE_INDEPENDENT_PROJECT_SECTIONS = \
        ["metadata", "derived_columns", "implied_columns", "trackhubs"]

