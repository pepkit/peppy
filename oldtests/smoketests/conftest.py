""" Configuration for modules with independent tests of models. """

import os

import pytest

__author__ = "Michal Stolarczyk"
__email__ = "michal@virginia.edu"

# example_peps branch, see: https://github.com/pepkit/example_peps
EB = "cfg2"


@pytest.fixture
def example_data_path():
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "example_peps-{}".format(EB)
    )
