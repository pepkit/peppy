""" Tests for utility functions """

import copy
import random
import string
import sys

import mock
import pytest

from attmap import AttributeDict
from peppy import Project, Sample
from peppy.const import SAMPLE_INDEPENDENT_PROJECT_SECTIONS, SAMPLE_NAME_COLNAME
from peppy.utils import \
    add_project_sample_constants, coll_like, copy as pepcopy, \
    grab_project_data, has_null_value, non_null_value
from tests.helpers import named_param, nonempty_powerset


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



class _DummyProject(Project):
    """ Get just the methods and data-access portions of Project. """
    def __init__(self, data):
        self.add_entries(data)



@pytest.fixture
def basic_project_data():
    """
    Provide a basic collection of Sample-independent data.

    :return dict[str, object]: Mapping from Project section name to
        value or collection of values.
    """
    return {
        "metadata": {
            "sample_annotation": "anns.csv",
            "output_dir": "outdir",
            "results_subdir": "results_pipeline",
            "submission_subdir": "submission"},
        "derived_attributes": ["data_source"],
        "implied_attributes": {"organism": {"genomes": {
            "mouse": "mm10", "rat": "rn6", "human": "hg38"}}},
        "trackhubs": []
    }



@pytest.fixture
def sample_independent_data(request, basic_project_data):
    """
    Build a collection of Sample-independent data for a test case.

    :param pytest.fixture.FixtureRequest request: test case requesting
        parameterization with Project data
    :param dict[str, object] basic_project_data: collection of predefined
        project data, to use either in its entirety or from which to
        return a subset
    :return dict[str, object]: data for test case to
        use as Sample-independent Project data
    """
    if "sections" in request.fixturenames:
        sections = request.getfixturevalue("sections")
    else:
        sections = SAMPLE_INDEPENDENT_PROJECT_SECTIONS
    return {s: basic_project_data[s] for s in sections}



class GrabProjectDataTests:
    """ Tests for grabbing Sample-independent Project configuration data. """


    @named_param(argnames="data", argvalues=[None, [], {}])
    def test_no_data(self, data):
        """ Parsing empty Project/data yields empty data subset. """
        assert {} == grab_project_data(data)


    @named_param(
        argnames="sections",
        argvalues=nonempty_powerset(SAMPLE_INDEPENDENT_PROJECT_SECTIONS))
    @named_param(argnames="data_type",
                 argvalues=[dict, AttributeDict, _DummyProject])
    def test_does_not_need_all_sample_independent_data(
            self, sections, data_type,
            basic_project_data, sample_independent_data):
        """ Subset of all known independent data that's present is grabbed. """
        p = data_type(sample_independent_data)
        expected = {s: data for s, data in basic_project_data.items()
                    if s in sections}
        observed = grab_project_data(p)
        assert expected == observed


    @named_param(
        argnames="extra_data",
        argvalues=nonempty_powerset(
            [{"pipeline_interfaces": [{"b": 1}, {"c": 2}]},
             {"pipeline_config": {}}]))
    @named_param(
        argnames="data_type", argvalues=[dict, AttributeDict, _DummyProject])
    def test_grabs_only_sample_independent_data(
            self, sample_independent_data, extra_data, data_type):
        """ Only Project data defined as Sample-independent is retrieved. """

        # Create the data to pass the the argument to the call under test.
        data = copy.deepcopy(sample_independent_data)
        data_updates = {}
        for extra in extra_data:
            data_updates.update(extra)
        data.update(data_updates)

        # Convert to the correct argument type for this test case.
        p = data_type(data)

        # Make the equivalence assertion.
        expected = sample_independent_data
        observed = grab_project_data(p)
        try:
            assert expected == observed
        except AssertionError:
            # If the test fails, make the diff easier to read.
            print("EXPECTED: {}".format(expected))
            print("OBSERVED: {}".format(observed))
            raise



class AddProjectSampleConstantsTests:
    """ Utility function can add a Project's constant to Sample. """


    @pytest.fixture
    def basic_sample(self):
        """ Provide test cases with a simple Sample instance. """
        return Sample({SAMPLE_NAME_COLNAME: "arbitrarily_named_sample"})


    def test_no_constants(self, basic_sample):
        """ No constants declared means the Sample is unchanged. """
        mock_prj = mock.MagicMock(constants=dict())
        sample = add_project_sample_constants(basic_sample, mock_prj)
        assert basic_sample == sample


    @named_param(
        argnames="constants",
        argvalues=[{"new_attr": 45}, {"a1": 0, "b2": "filepath"}])
    def test_add_project_sample_constants(self, basic_sample, constants):
        """ New attribute is added by the update. """
        mock_prj = mock.MagicMock(constants=constants)
        for attr in constants:
            assert attr not in basic_sample
            assert not hasattr(basic_sample, attr)
        basic_sample = add_project_sample_constants(basic_sample, mock_prj)
        for attr_name, attr_value in constants.items():
            assert attr_value == basic_sample[attr_name]
            assert attr_value == getattr(basic_sample, attr_name)


    @named_param(argnames=["collision", "old_val", "new_val"],
                 argvalues=[("coll_attr_1", 1, 2), ("coll_attr_2", 3, 4)])
    def test_name_collision(self, basic_sample, collision, old_val, new_val):
        """ New value overwrites old value (no guarantee for null, though.) """
        basic_sample[collision] = old_val
        mock_prj = mock.MagicMock(constants={collision: new_val})
        assert old_val == basic_sample[collision]
        basic_sample = add_project_sample_constants(basic_sample, mock_prj)
        assert new_val == basic_sample[collision]



def _randcoll(pool, dt):
    """
    Generate random collection of 1-10 elements.
    
    :param Iterable pool: elements from which to choose
    :param type dt: type of collection to create
    :return Iterable[object]: collection of randomly generated elements
    """
    valid_types = [tuple, list, set, dict]
    if dt not in valid_types:
        raise TypeError("{} is an invalid type; choose from {}".
                        format(str(dt), ", ".join(str(t) for t in valid_types)))
    rs = [random.choice(pool) for _ in range(random.randint(1, 10))]
    return dict(enumerate(rs)) if dt == dict else rs



@pytest.mark.parametrize(
    ["arg", "exp"],
    [(random.randint(-sys.maxsize - 1, sys.maxsize), False),
     (random.random(), False),
     (random.choice(string.ascii_letters), False),
     ([], True), (set(), True), (dict(), True), (tuple(), True),
     (_randcoll(string.ascii_letters, list), True),
     (_randcoll(string.ascii_letters, dict), True),
     (_randcoll([int(d) for d in string.digits], tuple), True),
     (_randcoll([int(d) for d in string.digits], set), True)]
)
def test_coll_like(arg, exp):
    """ Test arbiter of whether an object is collection-like. """
    assert exp == coll_like(arg)


def _get_empty_attrdict(data):
    ad = AttributeDict()
    ad.add_entries(data)
    return ad


class NullValueHelperTests:
    """ Tests of accuracy of null value arbiter. """

    _DATA = {"a": 1, "b": [2]}

    @pytest.mark.skip("Not implemented")
    @pytest.fixture(
        params=[lambda d: dict(d),
                lambda d: AttributeDict().add_entries(d),
                lambda d: _DummyProject(d)],
        ids=["dict", AttributeDict.__name__, _DummyProject.__name__])
    def kvs(self, request):
        """ For test cases provide KV pair map of parameterized type."""
        return request.param(self._DATA)

    def test_missing_key_neither_null_nor_non_null(self, kvs):
        """ A key not in a mapping has neither null nor non-null value. """
        k = "new_key"
        assert k not in kvs
        assert not has_null_value(k, kvs)
        assert not non_null_value(k, kvs)

    @pytest.mark.parametrize("coll", [list(), set(), tuple(), dict()])
    def test_empty_collection_is_null(self, coll, kvs):
        """ A key with an empty collection instance as its value is null. """
        ck = "empty"
        assert ck not in kvs
        kvs[ck] = coll
        assert has_null_value(ck, kvs)
        assert not non_null_value(ck, kvs)

    def test_None_is_null(self, kvs):
        """ A key with None as value is null. """
        bad_key = "nv"
        assert bad_key not in kvs
        kvs[bad_key] = None
        assert has_null_value(bad_key, kvs)
        assert not non_null_value(bad_key, kvs)

    @pytest.mark.parametrize("k", _DATA.keys())
    def test_non_nulls(self, k, kvs):
        """ Keys with non-None atomic or nonempty collection are non-null. """
        assert k in kvs
        assert non_null_value(k, kvs)



def test_copy():
    """ Test reference and equivalence comparison operators. """
    class ExampleObject:
        pass
    obj = ExampleObject()
    new_obj = pepcopy(obj)
    assert obj is new_obj
    assert obj == new_obj
