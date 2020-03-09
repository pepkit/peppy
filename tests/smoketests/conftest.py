""" Configuration for modules with independent tests of models. """

import pytest
import os

__author__ = "Michal Stolarczyk"
__email__ = "michal@virginia.edu"

# example_peps branch, see: https://github.com/pepkit/example_peps
EB = "cfg2"


@pytest.fixture
def example_pep_cfg_path(request):
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data",
                        "example_peps-{}".format(EB),
                        "example_{}".format(request.param),
                        "project_config.yaml")

