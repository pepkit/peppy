""" Tests for data type and function definitions in the `models` module. """

import itertools
import numpy as np
import pytest
from conftest import basic_entries, nested_entries
from looper.models import AttributeDict, Paths, copy


_ATTR_VALUES = [None, set(), [], {}, {"abc": 123}, (1, 'a'),
                "", "str", -1, 0, 1.0, np.nan]

_ENTRIES_PROVISION_MODES = ["gen", "dict", "zip", "list", "items"]
_COMPARISON_FUNCTIONS = ["__eq__", "__ne__", "__len__",
                         "keys", "values", "items"]


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
    This is to ensure that the implemented `collections.MutableMapping`
    or `collections.abc.MutableMapping` methods are valid.
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
            argnames="entries_gen,entries_provision_type",
            argvalues=itertools.product([basic_entries, nested_entries],
                                        _ENTRIES_PROVISION_MODES),
            ids=["{entries}-{mode}".format(entries=gen.__name__, mode=mode)
                 for gen, mode in
                 itertools.product([basic_entries, nested_entries],
                                    _ENTRIES_PROVISION_MODES)]
    )
    def test_construction_modes_supported(
            self, entries_gen, entries_provision_type):
        """ Construction wants key-value pairs; wrapping doesn't matter. """
        entries_mapping = dict(entries_gen())
        if entries_provision_type == "dict":
            entries = entries_mapping
        elif entries_provision_type == "zip":
            keys, values = zip(*entries_gen())
            entries = zip(keys, values)
        elif entries_provision_type == "items":
            entries = entries_mapping.items()
        elif entries_provision_type == "list":
            entries = list(entries_gen())
        elif entries_provision_type == "gen":
            entries = entries_gen
        else:
            raise ValueError("Unexpected entries type: {}".
                             format(entries_provision_type))
        expected = entries_mapping
        observed = AttributeDict(entries)
        assert expected == observed


    @pytest.mark.parametrize(
            argnames="comp_func", argvalues=_COMPARISON_FUNCTIONS)
    def test_abstract_mapping_method_implementations(self, entries, comp_func):
        """ AttributeDict can store mappings as values, no problem. """
        data = dict(basic_entries())
        attrdict = AttributeDict(data)
        if comp_func in ["__eq__", "__ne__"]:
            are_equal = getattr(attrdict, comp_func).__call__(data)
            assert are_equal if comp_func == "__eq__" else (not are_equal)
        else:
            raw_dict_comp_func = getattr(data, comp_func)
            attrdict_comp_func = getattr(attrdict, comp_func)
            expected = raw_dict_comp_func.__call__()
            observed = attrdict_comp_func.__call__()
            assert observed == expected


    # TODO: ensure that we cover tests cases for both merged and non-merged.

    def test_AttributeDict_values(self):
        """ An AttributeDict can store other AttributeDict instances. """
        pass


    def test_AttributeDict_values_nested(self):
        """ An AttributeDict can store nested AttributeDict instances. """
        pass



    def test_values_type_jambalaya(self):
        """ AttributeDict can store values of varies types. """
        # TODO -- Noah's ark here; make sure that there are at least two of each value type --> consider nesting also.
        pass


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



class AttributeDictUpdateTests:
    """Validate behavior of post-construction addition of entries.

    Though entries may and often will be provided at instantiation time,
    AttributeDict is motivated to support inheritance by domain-specific
    data types for which use cases are likely to be unable to provide
    all relevant data at construction time. So let's verify that we get the
    expected behavior when entries are added after initial construction.

    """
    pass


    def test_setattr_allowed(self):
        pass


    def test_delayed_item_insertion(self):
        # TODO: unmatched key, matched key, atomic, mapping, nested mapping,
        # TODO(continued): AttributeDict, non AttributeDict mapping value.
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


    def test_numeric_key(self):
        """ AttributeDict preserves the property that attribute request must be string. """
        ad = AttributeDict({1: 'a'})
        assert 'a' == ad[1]
        with pytest.raises(TypeError):
            getattr(ad, 1)



class AttributeDictSerializationTests:
    """ Ensure that we can make a file roundtrip for `AttributeDict` """
    pass



def _assert_entirely_equal(observed, expected):
    """ Accommodate equality assertion for varied data, including NaN. """
    try:
        assert observed == expected
    except AssertionError:
        assert np.isnan(observed) and np.isnan(expected)
    except ValueError:
        assert (observed == expected).all()


