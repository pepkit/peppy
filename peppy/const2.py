""" Package constants """

__author__ = "Michal Stolarczyk"
__email__ = "michal@virginia.edu"

# Project-related
CONFIG_VERSION_KEY = "config_version"
CONFIG_FILE_KEY = "_config_file"
CONFIG_KEY = "_config"
PROJECT_TYPENAME = "Project"
MODIFIERS_KEY = "sample_modifiers"
NAME_TABLE_ATTR = "sample_table"
CONSTANT_KEY = "constant"
DUPLICATED_KEY = "duplicated"
DERIVED_SOURCES_KEY = "derived_sources"
DERIVED_KEY = "derived"
IMPLIED_KEY = "implied"
METADATA_KEY = "metadata"
OUTDIR_KEY = "output_dir"
CFG_IMPORTS_KEY = "imports"
AMENDMENTS_KEY = "amendments"
PIPE_ARGS_SECTION = "pipeline_args"
SUBMISSION_FOLDER_KEY = "submission_subdir"
RESULTS_FOLDER_KEY = "results_subdir"
SAMPLE_EDIT_FLAG_KEY = "_samples_touched"
PROJECT_CONSTANTS = [
    "CONSTANT_KEY", "DERIVED_SOURCES_KEY", "DERIVED_KEY", "MODIFIERS_KEY",
    "IMPLIED_KEY", "METADATA_KEY", "NAME_TABLE_ATTR", "OUTDIR_KEY",
    "PIPE_ARGS_SECTION", "RESULTS_FOLDER_KEY", "CONFIG_FILE_KEY", "CONFIG_KEY",
    "SUBMISSION_FOLDER_KEY", "AMENDMENTS_KEY", "PROJECT_TYPENAME",
    "CONFIG_VERSION_KEY", "DUPLICATED_KEY", "SAMPLE_EDIT_FLAG_KEY",
    "CFG_IMPORTS_KEY"]
SNAKEMAKE_SAMPLE_COL = "sample"

# Sample-related
PROTOCOL_KEY = "protocol"
SAMPLE_NAME_ATTR = "sample_name"
SAMPLE_TABLE_KEY = "sample_table"
SUBSAMPLE_TABLE_KEY = "subsample_table"
PRJ_REF = "_project"
ATTR_KEY_PREFIX = "_key_"
SAMPLE_CONSTANTS = ["PROTOCOL_KEY", "SAMPLE_TABLE_KEY", "SUBSAMPLE_TABLE_KEY",
                    "PRJ_REF", "SAMPLE_NAME_ATTR", "ATTR_KEY_PREFIX"]

# CLI
VALIDATE_CMD = "validate"
INSPECT_CMD = "inspect"
SUBPARSER_MSGS = {
    VALIDATE_CMD: "Validate the PEP or its components.",
    INSPECT_CMD: "Inspect a PEP."
}

CLI_CONSTANTS = ["VALIDATE_CMD", "INSPECT_CMD", "SUBPARSER_MSGS"]

# Other
PKG_NAME = "peppy"
MAX_PROJECT_SAMPLES_REPR = 2
OTHER_CONSTANTS = ["MAX_PROJECT_SAMPLES_REPR", "PKG_NAME"]

__all__ = PROJECT_CONSTANTS + SAMPLE_CONSTANTS + OTHER_CONSTANTS + CLI_CONSTANTS
