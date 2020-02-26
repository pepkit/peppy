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
ACTIVE_AMENDMENTS_KEY = "_" + AMENDMENTS_KEY
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
    "CFG_IMPORTS_KEY", "ACTIVE_AMENDMENTS_KEY"]
SNAKEMAKE_SAMPLE_COL = "sample"

# Sample-related
PROTOCOL_KEY = "protocol"
SAMPLE_NAME_ATTR = "sample_name"
SAMPLE_SHEET_KEY = "sample_sheet"
SUBSAMPLE_SHEET_KEY = "subsample_sheet"
CFG_SAMPLE_TABLE_KEY = "sample_table"
CFG_SUBSAMPLE_TABLE_KEY = "subsample_table"
SAMPLE_DF_KEY = "_sample_df"
SUBSAMPLE_DF_KEY = "_subsample_df"
PRJ_REF = "_project"
ATTR_KEY_PREFIX = "_key_"
SAMPLE_CONSTANTS = ["PROTOCOL_KEY", "SUBSAMPLE_SHEET_KEY", "SAMPLE_SHEET_KEY",
                    "PRJ_REF", "SAMPLE_NAME_ATTR", "ATTR_KEY_PREFIX",
                    "CFG_SAMPLE_TABLE_KEY", "CFG_SUBSAMPLE_TABLE_KEY",
                    "SAMPLE_DF_KEY", "SUBSAMPLE_DF_KEY"]

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
MAX_PROJECT_SAMPLES_REPR = 20
OTHER_CONSTANTS = ["MAX_PROJECT_SAMPLES_REPR", "PKG_NAME"]

__all__ = PROJECT_CONSTANTS + SAMPLE_CONSTANTS + OTHER_CONSTANTS + CLI_CONSTANTS
