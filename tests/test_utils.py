""" Tests for utility functions """

import copy
import pytest
from looper import \
    IMPLICATIONS_DECLARATION, SAMPLE_INDEPENDENT_PROJECT_SECTIONS
from looper.models import AttributeDict, Project
from looper.utils import grab_project_data
from helpers import named_param, nonempty_powerset


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"




class _DummyProject(Project):
    """ Get just the methods and data-access portions of Project. """
    def __init__(self, data):
        self.add_entries(data)



@pytest.fixture
def basic_project_data():
    return {
        "metadata": {
            "sample_annotation": "anns.csv",
            "output_dir": "outdir",
            "results_subdir": "results_pipeline",
            "submission_subdir": "submission"},
        "derived_columns": ["data_source"],
        IMPLICATIONS_DECLARATION: {"organism": {"genomes": {
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

        # DEBUG
        print("type(extra_data): {}".format(type(extra_data)))
        print("list(map(type, extra_data)): {}".format(list(map(type, extra_data))))

        data = copy.deepcopy(sample_independent_data)
        data_updates = {}
        for extra in extra_data:
            data_updates.update(extra)
        data.update(data_updates)
        p = data_type(data)
        expected = sample_independent_data
        observed = grab_project_data(p)
        try:
            assert expected == observed
        except AssertionError:
            print("EXPECTED: {}".format(expected))
            print("OBSERVED: {}".format(observed))
            # Determine what the data look like.
            print("P: {}".format(p))
            raise
