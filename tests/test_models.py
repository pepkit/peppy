""" Tests for data type and function definitions in the `models` module. """

import numpy as np
import pytest
from looper.models import AttributeDict, Paths, copy


_ATTR_VALUES = [None, set(), [], {}, {"abc": 123}, (1, 'a'),
                "", "str", -1, 0, 1.0, np.nan]



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

    @pytest.mark.parametrize(argnames="attr", argvalues=[None] + _ATTR_VALUES)
    def test_Paths(self, attr):
        """ Check that Paths attribute can be set and returned as expected. """
        paths = Paths()
        paths.example_attr = attr
        _assert_entirely_equal(getattr(paths, "example_attr"), attr)


class AttributeDictTests:
    """ Tests for the AttributeDict ADT """


    @pytest.mark.parametrize(argnames="attval",
                             argvalues=_ATTR_VALUES + [np.random.random(20)])
    def test_ctor_non_nested(self, attval):
        """ Test attr fetch, with dictionary syntax and with object syntax. """
        # Set and retrieve attributes
        attrd = AttributeDict({"attr": attval})
        _assert_entirely_equal(attrd["attr"], attval)
        _assert_entirely_equal(getattr(attrd, "attr"), attval)


    @pytest.mark.parametrize(argnames="attval",
                             argvalues=_ATTR_VALUES + [np.random.random(20)])
    def test_ctor_nested(self, attval):
        """ Test AttributeDict nesting functionality. """
        attrd = AttributeDict({"attr": attval})
        attrd.attrd = AttributeDict({"attr": attval})
        _assert_entirely_equal(attrd.attrd["attr"], attval)
        _assert_entirely_equal(getattr(attrd.attrd, "attr"), attval)
        _assert_entirely_equal(attrd["attrd"].attr, attval)


    @pytest.mark.parametrize(argnames="missing", argvalues=["att", ""])
    def test_missing_getattr(self, missing):
        attrd = AttributeDict()
        with pytest.raises(AttributeError):
            getattr(attrd, missing)


    @pytest.mark.parametrize(argnames="missing",
                             argvalues=["", "b", "missing"])
    def test_missing_getitem(self, missing):
        attrd = AttributeDict()
        with pytest.raises(KeyError):
            attrd[missing]


def _assert_entirely_equal(observed, expected):
    try:
        assert (observed == expected) or \
               (np.isnan(observed) and np.isnan(expected))
    except ValueError:
        assert (observed == expected).all()
