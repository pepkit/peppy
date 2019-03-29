""" Tests regarding Project data tables """

from copy import deepcopy
import pytest
from peppy import METADATA_KEY, SAMPLE_ANNOTATIONS_KEY, \
    SAMPLE_SUBANNOTATIONS_KEY, NAME_TABLE_ATTR

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


@pytest.fixture(scope="function")
def prj(request, tmpdir):
    data = {
        METADATA_KEY: {}
    }
    return deepcopy({METADATA_KEY: {}})


@pytest.mark.skip("Not implemented")
def test_no_annotations_sheets():
    pass


@pytest.mark.skip("Not implemented")
def test_annotations_without_subannotations():
    pass


@pytest.mark.skip("Not implemented")
def test_subannotations_without_annotations():
    pass


@pytest.mark.skip("Not implemented")
def test_both_annotations_sheets():
    pass
