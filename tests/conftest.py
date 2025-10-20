""" Configuration for modules with independent tests of models. """

import os

import pandas as pd
import pytest
from peppy.project import Project

__author__ = "Michal Stolarczyk"
__email__ = "michal.stolarczyk@nih.gov"

# example_peps branch, see: https://github.com/pepkit/example_peps
EPB = "master"


@pytest.fixture
def data_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


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
def example_yaml_sample_file(request):
    return get_path_to_example_file(EPB, request.param, "sample.yaml")


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


@pytest.fixture
def schemas_path(data_path):
    return os.path.join(data_path, "schemas")


@pytest.fixture
def peps_path(data_path):
    return os.path.join(data_path, "peps")


@pytest.fixture
def project_file_path(peps_path):
    return os.path.join(peps_path, "test_pep", "test_cfg.yaml")


@pytest.fixture
def project_object(project_file_path):
    return Project(project_file_path)


@pytest.fixture
def schema_file_path(schemas_path):
    return os.path.join(schemas_path, "test_schema.yaml")


@pytest.fixture
def schema_samples_file_path(schemas_path):
    return os.path.join(schemas_path, "test_schema_samples.yaml")


@pytest.fixture
def schema_invalid_file_path(schemas_path):
    return os.path.join(schemas_path, "test_schema_invalid.yaml")


@pytest.fixture
def schema_imports_file_path(schemas_path):
    return os.path.join(schemas_path, "test_schema_imports.yaml")
