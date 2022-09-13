""" Configuration for modules with independent tests of models. """

import os

import pandas as pd
import pytest
import json

__author__ = "Michal Stolarczyk"
__email__ = "michal.stolarczyk@nih.gov"

# example_peps branch, see: https://github.com/pepkit/example_peps
EPB = "master"


def merge_paths(pep_branch, directory_name):
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "tests",
        "data",
        "example_peps-{}".format(pep_branch),
        "example_{}".format(directory_name),
    )


def get_path_to_example_file(branch, directory_name, file_name):
    return os.path.join(merge_paths(branch, directory_name), file_name)


@pytest.fixture
def example_pep_cfg_path(request):
    return get_path_to_example_file(EPB, request.param, "project_config.yaml")


@pytest.fixture
def example_pep_csv_path(request):
    return get_path_to_example_file(EPB, request.param, "sample_table.csv")


@pytest.fixture
def example_pep_nextflow_csv_path():
    return get_path_to_example_file(EPB, "nextflow_taxprofiler_pep", "samplesheet.csv")


@pytest.fixture
def example_pep_cfg_noname_path(request):
    return get_path_to_example_file(EPB, "noname", request.param)


@pytest.fixture
def example_peps_cfg_paths(request):
    """
    This is the same as the ficture above, however, it lets
    you return multiple paths (for comparing peps). Will return
    list of paths.
    """
    return [
        get_path_to_example_file(EPB, p, "project_config.yaml") for p in request.param
    ]


@pytest.fixture
def config_with_pandas_obj(request):
    return pd.read_csv(
        get_path_to_example_file(EPB, request.param, "sample_table.csv"), dtype=str
    )
