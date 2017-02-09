""" Tests for data type and function definitions in the `models` module. """

import numpy as np
import pytest
from looper.models import AttributeDict, Paths, copy


_ATTR_VALUES = ["str", 1, 1.0, np.nan]



class ExampleObject():
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
        assert getattr(paths, "example_attr") is attr


class AttributeDictTests:
    """ Tests for the AttributeDict ADT """


    @pytest.mark.parametrize(argnames="attval",
                             argvalues=_ATTR_VALUES + [np.random.random(20)])
    def test_AttributeDict_ctor_non_null_value(self, attval):
        """ Test attr fetch with both dictionary syntax and with object syntax. """
        # Set and retrieve attributes
        attrd = AttributeDict({"attr": attval})
        assert attrd["attr"] is attval
        assert getattr(attrd, "attr") is attval


    @pytest.mark.parametrize(argnames="attval",
                             argvalues=_ATTR_VALUES + [np.random.random(20)])
    def test_AttributeDict_nested_non_null_value(self, attval):
        """ Test AttributeDict nesting functionality. """
        attrd = AttributeDict({"attr": attval})
        attrd.attrd = AttributeDict({"attr": attval})
        assert attrd.attrd["attr"] is attval
        assert getattr(attrd.attrd, "attr") is attval
        assert attrd["attrd"].attr is attval


    def test_AttributeDict_ctor_null_value_getattr_access(self):
        attrd = AttributeDict({"attr": None})
        with pytest.raises(AttributeError):
            attrd.attr


    @pytest.mark.xfail(reason="__getitem__ access style uses getattr",
                       raises=AttributeError)
    def test_AttributeDict_ctor_null_value_getitem_access(self):
        key = "att"
        attrd = AttributeDict({key: None})
        with pytest.raises(KeyError):
            attrd[key]