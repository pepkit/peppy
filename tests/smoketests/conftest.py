""" Configuration for modules with independent tests of models. """

import os

import pytest

__author__ = "Michal Stolarczyk"
__email__ = "michal.stolarczyk@nih.gov"

# example_peps branch, see: https://github.com/pepkit/example_peps
EPB = "master"


@pytest.fixture
def example_pep_cfg_path(request):
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "example_peps-{}".format(EPB),
        "example_{}".format(request.param),
        "project_config.yaml",
    )


@pytest.fixture
def example_pep_csv_path(request):
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "example_peps-{}".format(EPB),
        "example_{}".format(request.param),
        "sample_table.csv",
    )


@pytest.fixture
def example_pep_cfg_noname_path(request):
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "example_peps-{}".format(EPB),
        "example_noname",
        request.param,
    )


@pytest.fixture
def example_peps_cfg_paths(request):
    """
    This is the same as the ficture above, however, it lets
    you return multiple paths (for comparing peps). Will return
    list of paths.
    """
    return [
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "example_peps-{}".format(EPB),
            "example_{}".format(p),
            "project_config.yaml",
        )
        for p in request.param
    ]


@pytest.fixture
def nextflow_sample_table_path():
    return "tests/data/example_peps-master/example_nextflow_samplesheet/samplesheet.csv"
