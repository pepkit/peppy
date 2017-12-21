""" Tests for Sample's collection of paths. """

import numpy as np
import pytest

from peppy.sample import Paths
from tests.helpers import assert_entirely_equal



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
