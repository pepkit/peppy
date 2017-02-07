""" Tests for data type and function definitions in the `models` module. """

import numpy as np
import pytest
from looper.models import AttributeDict, Paths, copy


_ATTR_VALUES = [None, "str", 1, 1.0, np.nan]


class ExampleObject():
    pass


def test_copy():
    """ Test reference and equivalence comparison operators. """
    obj = ExampleObject()
    new_obj = copy(obj)
    assert obj is new_obj
    assert obj == new_obj


@pytest.mark.parametrize(argnames="attr", argvalues=_ATTR_VALUES)
def test_Paths(attr):
    """ Check that Paths attribute can be set and returned as expected. """
    paths = Paths()
    paths.example_attr = attr
    assert getattr(paths, "example_attr") is attr


@pytest.mark.parametrize(argnames="attval",
                         argvalues=_ATTR_VALUES + [np.random.random(20)])
def test_AttributeDict_setret(attval):
    """ Test attr fetch with both dictionary syntax and with object syntax. """
    # Set and retrieve attributes
    attrd = AttributeDict({"attr": attval})
    assert attrd["attr"] is attval
    assert getattr(attrd, "attr") is attval


@pytest.mark.parametrize(argnames="attval",
                         argvalues=_ATTR_VALUES + [np.random.random(20)])
def test_AttributeDict_nested(attval):
    """ Test AttributeDict nesting functionality. """
    attrd = AttributeDict({"attr": attval})
    attrd.attrd = AttributeDict({"attr": attval})
    assert attrd.attrd["attr"] is attval
    assert getattr(attrd.attrd, "attr") is attval
    assert attrd["attrd"].attr is attval

