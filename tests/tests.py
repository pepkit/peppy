
from looper.models import copy, Paths, AttributeDict
from looper.models import Project, SampleSheet, Sample
from looper.models import PipelineInterface, ProtocolMapper, CommandChecker


import numpy as np
from pandas.util.testing import assert_frame_equal, assert_series_equal
import numpy.testing as npt


class ExampleObject():
    pass


def test_():
    assert 1 == 1


def test_copy():
    obj = ExampleObject()
    new_obj = copy(obj)
    assert obj is new_obj
    assert obj == new_obj


def test_Paths():
    paths = Paths()

    for attr in [None, "str", 1, 1.0, np.nan]:
        paths.example_attr = attr
        assert getattr(paths, "example_attr") is attr


def test_AttributeDict():
    attrs = [None, "str", 1, 1.0, np.nan, np.random.random(20)]
    # Set and retrieve attributes
    for attr in attrs:
        attrd = AttributeDict({"attr": attr})
        assert attrd["attr"] is attr
        assert getattr(attrd, "attr") is attr

    # Nested AttributeDict
    for attr in attrs:
        attrd.attrd = AttributeDict({"attr": attr})
        assert attrd.attrd["attr"] is attr
        assert getattr(attrd.attrd, "attr") is attr
