""" Tests for data type and function definitions in the `models` module. """

from copy import deepcopy
import itertools
import numpy as np
import pytest
from conftest import basic_entries, nested_entries, COMPARISON_FUNCTIONS
from looper.exceptions import MetadataOperationException
from looper.models import AttributeDict, Paths, copy, ATTRDICT_METADATA


_ATTR_VALUES = [None, set(), [], {}, {"abc": 123}, (1, 'a'),
                "", "str", -1, 0, 1.0, np.nan]
_ENTRIES_PROVISION_MODES = ["gen", "dict", "zip", "list", "items"]
ADDITIONAL_NON_NESTED = {"West Complex": {"CPHG": 6}, "BIG": {"MR-4": 6}}
ADDITIONAL_NESTED = {"JPA": {"West Complex": {"CPHG": 6}},
                     "Lane": {"BIG": {"MR-4": 6}}}
ADDITIONAL_VALUES_BY_NESTING = {
    False: ADDITIONAL_NON_NESTED,
    True: ADDITIONAL_NESTED
}



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
            argnames="entries,comp_func",
            argvalues=itertools.product([basic_entries, nested_entries],
                                        COMPARISON_FUNCTIONS),
            ids=["{}-{}".format(gen.__name__, name_comp_func)
                 for gen, name_comp_func in itertools.product(
                     [basic_entries, nested_entries], COMPARISON_FUNCTIONS)]
    )
    def test_abstract_mapping_method_implementations_basic(
            self, comp_func, entries):
        """ AttributeDict can store mappings as values, no problem. """
        if entries.__name__ == nested_entries.__name__ and \
                        comp_func in ("values", "items"):
            pytest.xfail("Nested AD values involve behavioral metadata")
        self._validate_mapping_function_implementation(
            entries_gen=entries, name_comp_func=comp_func)


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


    @staticmethod
    def _validate_mapping_function_implementation(entries_gen, name_comp_func):
        data = dict(entries_gen())
        attrdict = AttributeDict(data)
        if __name__ == '__main__':
            if name_comp_func in ["__eq__", "__ne__"]:
                are_equal = getattr(attrdict, name_comp_func).__call__(data)
                assert are_equal if name_comp_func == "__eq__" \
                        else (not are_equal)
            else:
                raw_dict_comp_func = getattr(data, name_comp_func)
                attrdict_comp_func = getattr(attrdict, name_comp_func)
                expected = raw_dict_comp_func.__call__()
                observed = attrdict_comp_func.__call__()
                try:
                    # Most comparison methods are returning iterables.
                    assert set(expected) == set(observed)
                except TypeError:
                    # Could be int or other non-iterable that we're comparing.
                    assert expected == observed



class AttributeDictUpdateTests:
    """Validate behavior of post-construction addition of entries.

    Though entries may and often will be provided at instantiation time,
    AttributeDict is motivated to support inheritance by domain-specific
    data types for which use cases are likely to be unable to provide
    all relevant data at construction time. So let's verify that we get the
    expected behavior when entries are added after initial construction.

    """

    # TODO: ensure that we cover tests cases for both merged and non-merged.

    _TOTALLY_ARBITRARY_VALUES = [
        "abc", 123,
        (4, "text", ("nes", "ted")), list("-101")
    ]
    _GETTERS = ["__getattr__", "__getitem__"]
    _SETTERS = ["__setattr__", "__setitem__"]


    @pytest.mark.parametrize(
            argnames="setter_name,getter_name,is_novel",
            argvalues=itertools.product(_SETTERS, _GETTERS, (False, True)))
    def test_set_get_atomic(self, setter_name, getter_name, is_novel):
        """ For new and existing items, validate set/get behavior. """

        # Establish the AttributeDict for the test case.
        data = dict(basic_entries())
        ad = AttributeDict(basic_entries())

        # Establish a ground truth and select name/value(s) based on
        # whether or not the test case wants to test a new or existing item.
        if is_novel:
            item_name = "awesome_novel_attribute"
            assert item_name not in ad
            with pytest.raises(AttributeError):
                getattr(ad, item_name)
            item_values = self._TOTALLY_ARBITRARY_VALUES
        else:
            item_name = np.random.choice(a=data.keys(), size=1)[0]
            item_value = data[item_name]
            assert ad[item_name] == item_value
            assert getattr(ad, item_name) == item_value
            item_values = [item_value]

        # Determine which functions to use to make the set/get calls.
        setter = getattr(ad, setter_name)
        getter = getattr(ad, getter_name)

        # Validate set/get for each value.
        for value in item_values:
            setter(item_name, value)
            assert getter(item_name) == value


    @pytest.mark.parametrize(
            argnames="funcname,name_metadata_item",
            argvalues=itertools.product(_GETTERS + _SETTERS,
                                        ATTRDICT_METADATA),
            ids=["{}, '{}'".format(func.strip("_"), attr)
                 for func, attr in itertools.product(_GETTERS + _SETTERS,
                                                     ATTRDICT_METADATA)])
    def test_touch_privileged_metadata_item(self, funcname,
                                            name_metadata_item):
        """ AttributeDict has a few metadata members that may not be set. """

        # Create AttributeDict and ensure it has the target item.
        ad = AttributeDict(dict(basic_entries()))
        assert hasattr(ad, name_metadata_item)

        # If current test parameter is a setter, it needs a value argument.
        dummy_value = "this_will_fail"
        touch = getattr(ad, funcname)
        args = (name_metadata_item, )

        # Make the actual call under test.
        if funcname in ["__setattr__", "__setitem__"]:
            pytest.xfail(
                    "Since {} is recursive, it's difficult to prohibit "
                    "post-construction attempts to set metadata. It may "
                    "not even be desirable".format(AttributeDict.__name__))
            args += (dummy_value, )
        with pytest.raises(MetadataOperationException):
            touch.__call__(*args)


    @pytest.mark.parametrize(
            argnames=["initial_entries", "name_update_func",
                      "is_update_attrdict", "nested", "validation_getter"],
            argvalues=itertools.product([basic_entries, nested_entries],
                                        _SETTERS + ["add_entries"],
                                        [False, True],
                                        [False, True],
                                        ["__getitem__", "__getattr__"]),
            ids=lambda arg: arg.__name__ if callable(arg) else str(arg)
    )
    def test_new_entries_mappings(
            self, initial_entries, name_update_func,
            is_update_attrdict, nested, validation_getter):
        """ Raw mapping for previously-unknown key becomes AttributeDict. """
        ad = AttributeDict(dict(initial_entries()))
        setter = getattr(ad, name_update_func)
        new_entries_data = ADDITIONAL_VALUES_BY_NESTING[nested]
        if name_update_func == "add_entries":
            setter({k: (AttributeDict(v) if is_update_attrdict else v)
                    for k, v in new_entries_data.items()})
        else:
            for k, v in new_entries_data.items():
                setter(k, AttributeDict(v) if is_update_attrdict else v)
        validation_getter = getattr(ad, validation_getter)
        for item_name, expected_value in new_entries_data.items():
            # A value that's a mapping is inserted as AttributeDict.
            observed_value = validation_getter(item_name)
            assert isinstance(observed_value, AttributeDict)
            # Check equality on the mapping's contents.
            assert expected_value == observed_value




class AttributeDictCollisionTests:
    """ Tests for proper merging and type conversion of mappings. 
     AttributeDict converts a mapping being inserted as a value to an 
     AttributeDict. If assigning to a key that already contains a mapping, 
     the existing value (mapping) for the key merges with the new one. """


    CPHG_DATA = {"CPHG": 6}
    WEST_COMPLEX_DATA = {"West Complex": CPHG_DATA}

    BIG_DATA = {"BIG": 4}
    INITIAL_MR_DATA = {"MR": BIG_DATA}
    NEW_MR_DATA = {"MR": {"BME": 5, "Carter-Harrison": 6}}
    PINN_DATA =  {"Pinn": ["SOM", "Jordan", 1340]}


    @pytest.mark.parametrize(argnames="name_setter_func",
                             argvalues=["__setattr__", "__setitem__"])
    @pytest.mark.parametrize(argnames="name_getter_func", 
                             argvalues=["__getattr__", "__getitem__"])
    def test_merge_mappings(
                self, name_setter_func, name_getter_func):

        attrdict = AttributeDict()
        raw_data = {}
        setter = getattr(attrdict, name_setter_func)
        getter = getattr(attrdict, name_getter_func)

        setter("JPA", self.WEST_COMPLEX_DATA)
        raw_data.update({"JPA": self.WEST_COMPLEX_DATA})
        observed = getter("JPA")
        assert isinstance(observed, AttributeDict)
        assert self.WEST_COMPLEX_DATA == observed

        setter("Lane", self.INITIAL_MR_DATA)
        raw_data.update({"Lane": self.INITIAL_MR_DATA})
        assert isinstance(getter("Lane"), AttributeDict)
        assert raw_data == attrdict

        setter("JPA", self.PINN_DATA)
        observed = getter("JPA")
        assert isinstance(observed, AttributeDict)
        tempdict = deepcopy(self.WEST_COMPLEX_DATA)
        tempdict.update(self.INITIAL_MR_DATA)
        tempdict.update(self.PINN_DATA)
        assert tempdict == observed

        setter("Lane", self.NEW_MR_DATA)
        higher_level_tempdict = {"JPA": self.WEST_COMPLEX_DATA}
        higher_level_tempdict["JPA"].update(self.PINN_DATA)
        higher_level_tempdict["Lane"] = {"MR": self.BIG_DATA}
        higher_level_tempdict["Lane"]["MR"].update(self.NEW_MR_DATA["MR"])
        assert higher_level_tempdict == attrdict


    @pytest.mark.parametrize(
            argnames="name_update_func",
            argvalues=["add_entries", "__setattr__", "__setitem__"])
    def test_squash_existing(self, name_update_func):
        """ When a value that's a mapping is assigned to existing key with 
        non-mapping value, the new value overwrites the old. """
        ad = AttributeDict({"MR": 4})
        assert 4 == ad.MR
        assert 4 == ad["MR"]
        new_value = [4, 5, 6]
        args = ("MR", new_value)
        setter = getattr(ad, name_update_func)
        if name_update_func == "add_entries":
            setter([args])
        else:
            setter(*args)
        assert new_value == ad.MR
        assert new_value == ad["MR"]



class AttributeDictSerializationTests:
    """ Ensure that we can make a file roundtrip for `AttributeDict` """
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



def _assert_entirely_equal(observed, expected):
    """ Accommodate equality assertion for varied data, including NaN. """
    try:
        assert observed == expected
    except AssertionError:
        assert np.isnan(observed) and np.isnan(expected)
    except ValueError:
        assert (observed == expected).all()


