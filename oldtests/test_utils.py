""" Tests for utility functions """

import copy

import mock
import pytest
from attmap import PathExAttMap
from ubiquerg import powerset

from peppy import Sample
from peppy.const import *
from peppy.project import NEW_PIPES_KEY, RESULTS_FOLDER_VALUE, SUBMISSION_FOLDER_VALUE
from peppy.utils import add_project_sample_constants
from peppy.utils import copy as pepcopy
from peppy.utils import grab_project_data, has_null_value, non_null_value
from tests.helpers import compare_mappings, named_param

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


@pytest.fixture
def basic_project_data():
    """
    Provide a basic collection of Sample-independent data.

    :return dict[str, object]: Mapping from Project section name to
        value or collection of values.
    """
    return {
        METADATA_KEY: {
            NAME_TABLE_ATTR: "anns.csv",
            OUTDIR_KEY: "outdir",
            RESULTS_FOLDER_KEY: RESULTS_FOLDER_VALUE,
            SUBMISSION_FOLDER_KEY: SUBMISSION_FOLDER_VALUE,
        },
        DERIVATIONS_DECLARATION: [DATA_SOURCE_COLNAME],
        IMPLICATIONS_DECLARATION: {
            "organism": {"genomes": {"mouse": "mm10", "rat": "rn6", "human": "hg38"}}
        },
        "trackhubs": [],
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
        argvalues=powerset(SAMPLE_INDEPENDENT_PROJECT_SECTIONS, nonempty=True),
    )
    def test_does_not_need_all_sample_independent_data(
        self, sections, basic_project_data, sample_independent_data
    ):
        """ Subset of all known independent data that's present is grabbed. """
        p = PathExAttMap(sample_independent_data)
        expected = {s: data for s, data in basic_project_data.items() if s in sections}
        observed = grab_project_data(p)
        compare_mappings(expected, observed)

    @named_param(
        argnames="extra_data",
        argvalues=powerset(
            [{NEW_PIPES_KEY: [{"b": 1}, {"c": 2}]}, {"pipeline_config": {}}],
            nonempty=True,
        ),
    )
    def test_grabs_only_sample_independent_data(
        self, sample_independent_data, extra_data
    ):
        """ Only Project data defined as Sample-independent is retrieved. """

        # Create the data to pass the the argument to the call under test.
        data = copy.deepcopy(sample_independent_data)
        data_updates = {}
        for extra in extra_data:
            data_updates.update(extra)
        data.update(data_updates)

        # Convert to the correct argument type for this test case.
        p = PathExAttMap(data)

        # Make the equivalence assertion.
        expected = sample_independent_data
        observed = grab_project_data(p)
        compare_mappings(expected, observed)


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
        argnames="const", argvalues=[{"new_attr": 45}, {"a1": 0, "b2": "filepath"}]
    )
    def test_add_project_sample_constants(self, basic_sample, const):
        """ New attribute is added by the update. """
        mock_prj = mock.MagicMock(constant_attributes=const)
        for attr in const:
            assert attr not in basic_sample
            assert not hasattr(basic_sample, attr)
        basic_sample = add_project_sample_constants(basic_sample, mock_prj)
        for attr_name, attr_value in const.items():
            assert attr_value == basic_sample[attr_name]
            assert attr_value == getattr(basic_sample, attr_name)

    @named_param(
        argnames=["collision", "old_val", "new_val"],
        argvalues=[("coll_attr_1", 1, 2), ("coll_attr_2", 3, 4)],
    )
    def test_name_collision(self, basic_sample, collision, old_val, new_val):
        """ New value overwrites old value (no guarantee for null, though.) """
        basic_sample[collision] = old_val
        mock_prj = mock.MagicMock(constant_attributes={collision: new_val})
        assert old_val == basic_sample[collision]
        basic_sample = add_project_sample_constants(basic_sample, mock_prj)
        assert new_val == basic_sample[collision]


class NullValueHelperTests:
    """ Tests of accuracy of null value arbiter. """

    _DATA = {"a": 1, "b": [2]}

    @pytest.fixture(params=[lambda d: dict(d), lambda d: PathExAttMap().add_entries(d)])
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

    def test_none_is_null(self, kvs):
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


@pytest.mark.skip("not implemented")
def test_fetch_samples():
    """ Test selection of subset of samples from a Project. """
    pass


def _cmp_maps(m1, m2):
    m1, m2 = [m.to_map() if isinstance(m, PathExAttMap) else m for m in [m1, m2]]
    assert m1 == m2
