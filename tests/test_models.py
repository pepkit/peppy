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


class AttributeConstructionDictTests:
    """Tests for the AttributeDict ADT.

    Note that the implementation of the equality comparison operator
    is tested indirectly via the mechanism of many of the assertion
    statements used throughout these test cases. Some test cases are
    parameterized by comparison function to test for equivalence, rather
    than via input data as is typically the case. This avoids some overhead,
    This is both to ensure that the implemented `collections.MutableMapping`
    or `collections.abc.MutableMapping` methods are valid, and to more
    explicitly separate the data input type cases (entirely distinct test
    methods rather than parameterization of the same test). Another valid
    strategy implementation of these tests would be to take the product of
    the set of comparison methods and the set of all input data cases to
    test, but that would give way to somewhat of an unwieldy parameterization
    scheme, and it would sacrifice some of the readability that we get by
    separating distinct input data test cases into separate test methods.

    """

    # Refer to tail of class definition for
    # data and fixtures specific to this class.

    def test_null_construction(self):
        """ Null entries value creates empty AttributeDict. """
        assert {} == AttributeDict(None)


    def test_empty_construction(self, empty_collection):
        """ Empty entries container create empty AttributeDict. """
        assert {} == AttributeDict(empty_collection)


    @pytest.mark.parametrize(
            argnames="entries_type",
            argvalues=["gen", "dict", "zip", "list", "items"])
    def test_construction_modes_supported(self, _base_mapping, entries_type):
        """ Construction wants key-value pairs; wrapping doesn't matter. """
        if entries_type == "zip":
            entries = zip(self._BASE_KEYS, self._BASE_VALUES)
        else:
            entries = self._entries_stream
            if entries_type in ["dict", "items"]:
                entries = dict(entries())
                if entries_type == "items":
                    entries = entries.items()
            elif entries_type == "list":
                list(entries())
            elif entries_type == "gen":
                pass
            else:
                raise ValueError("Unexpected entries type: {}".
                                 format(entries_type))
        expected = _base_mapping
        observed = AttributeDict(entries)
        assert expected == observed


    # TODO: ensure that we cover tests cases for both merged and non-merged.

    @pytest.mark.parametrize(argnames="comp_func",
                             argvalues=["__eq__", "__ne__", "__len__",
                                        "keys", "values", "items"])
    def test_raw_dict_values(self, comp_func):
        """ AttributeDict can store mappings as values, no problem. """
        attrdict = AttributeDict(self._LOCATIONS_FLATMAP)
        if comp_func in ["__eq__", "__ne__"]:
            are_equal = getattr(attrdict, comp_func). \
                    __call__(self._LOCATIONS_FLATMAP)
            assert are_equal if comp_func == "__eq__" else (not are_equal)
        else:
            raw_dict_comp_func = getattr(self._LOCATIONS_FLATMAP, comp_func)
            attrdict_comp_func = getattr(attrdict, comp_func)
            expected = raw_dict_comp_func.__call__()
            observed = attrdict_comp_func.__call__()
            assert expected == observed


    def test_raw_dict_values_nested(self):
        """ AttributeDict can also store nested mappings as values. """
        assert self._SEASON_HIERARCHY == AttributeDict(self._SEASON_HIERARCHY)


    def test_numeric_key(self):
        """ AttributeDict enables dot-notation access to numeric key/attr. """
        pass


    def test_numeric_key_matching(self):
        pass


    def test_values_type_jambalaya(self):
        """ AttributeDict can store values of varies types. """
        # TODO -- Noah's ark here; make sure that there are at least two of each value type --> consider nesting also.
        pass


    def test_AttributeDict_values(self):
        """ An AttributeDict can store other AttributeDict instances. """
        pass


    def test_AttributeDict_values_nested(self):
        """ An AttributeDict can store nested AttributeDict instances. """
        pass


    @pytest.mark.parametrize(argnames="attval",
                             argvalues=_ATTR_VALUES + [np.random.random(20)])
    def test_ctor_non_nested(self, attval):
        """ Test attr fetch, with dictionary syntax and with object syntax. """
        # Set and retrieve attributes
        attrd = AttributeDict({"attr": attval})
        _assert_entirely_equal(attrd["attr"], attval)
        _assert_entirely_equal(getattr(attrd, "attr"), attval)


    def test_delayed_item_insertion(self):
        # TODO: unmatched key, matched key, atomic, mapping, nested mapping,
        # TODO(continued): AttributeDict, non AttributeDict mapping value.
        pass


    @pytest.mark.parametrize(argnames="attval",
                             argvalues=_ATTR_VALUES + [np.random.random(20)])
    def test_ctor_nested(self, attval):
        """ Test AttributeDict nesting functionality. """
        attrd = AttributeDict({"attr": attval})
        attrd.attrd = AttributeDict({"attr": attval})
        _assert_entirely_equal(attrd.attrd["attr"], attval)
        _assert_entirely_equal(getattr(attrd.attrd, "attr"), attval)
        _assert_entirely_equal(attrd["attrd"].attr, attval)


    # Provide some basic atomic-type data.
    _BASE_KEYS = ("epigenomics", "H3K", 2, 7,
                  "ac", "EWS", "FLI1")
    _BASE_VALUES = ("topic", "marker", 4, 14,
                    "acetylation", "RNA binding protein", "FLI1")
    _LOCATIONS_FLATMAP = {"BIG": 4, 6: "CPHG"}
    _SEASON_HIERARCHY = {
            "spring": {"February": 28, "March": 31, "April": 30, "May": 31},
            "summer": {"June": 30, "July": 31, "August": 31},
            "fall": {"September": 30, "October": 31, "November": 30},
            "winter": {"December": 31, "January": 31}
    }


    @pytest.fixture(scope="function")
    def _base_mapping(self):
        return dict(zip(self._BASE_KEYS, self._BASE_VALUES))


    @pytest.fixture(scope="function")
    def _entries_stream(self):
        for k, v in zip(self._BASE_KEYS, self._BASE_VALUES):
            yield k, v



class AttributeDictAddEntriesTests:
    """Validate behavior of post-construction addition of entries.

    Though entries may and often will be provided at instantiation time,
    AttributeDict is motivated to support inheritance by domain-specific
    data types for which use cases are likely to be unable to provide
    all relevant data at construction time. So let's verify that we get the
    expected behavior when entries are added after initial construction.

    """
    pass



class AttributeDictItemAccessTests:
    """ Tests for access of items (key- or attribute- style). """


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
    """ Accommodate equality assertion for varied data, including NaN. """
    try:
        assert observed == expected
    except AssertionError:
        assert np.isnan(observed) and np.isnan(expected)
    except ValueError:
        assert (observed == expected).all()


class SerializationTests:
    """ Ensure that  """
