""" Tests for data type and function definitions in the `models` module. """

import mock
import numpy as np
from pandas import Series
import pytest

import looper
from looper.models import AttributeDict, Paths, Sample, copy
from tests.utils import assert_entirely_equal



class ExampleObject:
    pass



def test_copy():
    """ Test reference and equivalence comparison operators. """
    obj = ExampleObject()
    new_obj = copy(obj)
    assert obj is new_obj
    assert obj == new_obj



class PathsTests:
    """ Tests for the `Paths` ADT. """

    @pytest.mark.parametrize(
            argnames="attr",
            argvalues=[None, set(), [], {}, {"abc": 123},
                       (1, 'a'), "", "str", -1, 0, 1.0, np.nan])
    def test_Paths(self, attr):
        """ Check that Paths attribute can be set and returned as expected. """
        paths = Paths()
        paths.example_attr = attr
        assert_entirely_equal(getattr(paths, "example_attr"), attr)



@pytest.mark.usefixtures("write_project_files", "pipe_iface_config_file")
class PipelineInterfaceTests:
    """ Test cases specific to PipelineInterface """

    def test_missing_input_files(self, proj):
        # This should not throw an error
        assert proj.samples[0].get_attr_values("all_input_files") is None
