""" Tests for data type and function definitions in the `models` module. """

import numpy as np
import pytest
from pep.models import Paths, copy
from tests.helpers import assert_entirely_equal



def test_copy():
    """ Test reference and equivalence comparison operators. """
    class ExampleObject:
        pass
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
        """ We're interested here in lack of exception, not return value. """
        proj.samples[0].get_attr_values("all_input_files")



@pytest.mark.skip("Not implemented")
class LooperProjectTests:
    """ Tests for looper-specific version of Project. """
    pass
