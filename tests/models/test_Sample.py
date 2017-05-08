""" Tests for the Sample. """

import mock
import numpy as np
from pandas import Series
import pytest
import looper
from looper.models import Sample


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



class ParseSampleImplicationsTests:
    """ Tests for appending columns/fields to a Sample based on a mapping. """

    IMPLIER_NAME = "sample_name"
    IMPLIER_VALUES = ["a", "b"]
    SAMPLE_A_IMPLICATIONS = {"genome": "hg38", "phenome": "hg72"}
    SAMPLE_B_IMPLICATIONS = {"genome": "hg38"}
    IMPLICATIONS = [SAMPLE_A_IMPLICATIONS, SAMPLE_B_IMPLICATIONS]
    IMPLICATIONS_MAP = {
        IMPLIER_NAME: IMPLICATIONS
    }


    def test_project_lacks_implications(self, sample):
        """ With no implications mapping, sample is unmodified. """
        before_inference = sample.__dict__
        with mock.patch.object(sample, "prj", create=True):
            sample.infer_columns()
        after_inference = sample.__dict__
        assert before_inference == after_inference


    def test_empty_implications(self, sample):
        """ Empty implications mapping --> unmodified sample. """
        before_inference = sample.__dict__
        implications = mock.MagicMock(implied_columns={})
        with mock.patch.object(sample, "prj", create=True, new=implications):
            sample.infer_columns()
        assert before_inference == sample.__dict__


    def test_null_intersection_between_sample_and_implications(self, sample):
        """ Sample with none of implications' fields --> no change. """
        before_inference = sample.__dict__
        implications = mock.MagicMock(implied_columns=self.IMPLICATIONS_MAP)
        with mock.patch.object(sample, "prj", create=True, new=implications):
            sample.infer_columns()
        assert before_inference == sample.__dict__


    @pytest.mark.parametrize(
        argnames=["implier_value", "implications"],
        argvalues=zip(IMPLIER_VALUES, IMPLICATIONS),
        ids=lambda implier_and_implications:
        "implier='{}', implications={}".format(
            implier_and_implications[0], str(implier_and_implications[1])))
    def test_intersection_between_sample_and_implications(
            self, sample, implier_value, implications):
        """ Intersection between implications and sample fields --> append. """

        # Negative control pretest
        for implied_field_name in implications.keys():
            assert not hasattr(sample, implied_field_name)

        # Set the parameterized value for the implications source field.
        setattr(sample, self.IMPLIER_NAME, implier_value)

        # Perform column inference based on mocked implications.
        implications = mock.MagicMock(implied_columns=self.IMPLICATIONS_MAP)
        with mock.patch.object(sample, "prj", create=True, new=implications):
            sample.infer_columns()

        # Validate updates to sample based on column implications & inference.
        for implied_name, implied_value in implications.items():
            assert implied_value == getattr(sample, implied_name)


    @pytest.mark.parametrize(
        argnames="unmapped_implier_value",
        argvalues=["totally-wacky-value", 62, None, np.nan])
    @pytest.mark.parametrize(
        argnames="implications", argvalues=IMPLICATIONS,
        ids=lambda implications: "implied={}".format(str(implications)))
    def test_sample_has_unmapped_value_for_implication(
            self, sample, unmapped_implier_value, implications):
        """ Unknown value in implier field --> null inference. """


        # Negative control pre-/post-test.
        def no_implied_values():
            assert all([not hasattr(sample, implied_field_name)
                        for implied_field_name in implications.keys()])


        no_implied_values()

        # Set the parameterized value for the implications source field.
        setattr(sample, self.IMPLIER_NAME, unmapped_implier_value)

        # Perform column inference based on mocked implications.
        implications = mock.MagicMock(implied_columns=self.IMPLICATIONS_MAP)
        with mock.patch.object(sample, "prj", create=True, new=implications):
            sample.infer_columns()
        no_implied_values()


    @pytest.fixture(scope="function")
    def sample(self, request):
        """
        Provide a Sample test case, with always-true validation.

        :param _pytest.fixtures.SubRequest request: test case requesting 
            a Sample instance.
        :return looper.models.Sample: basic Sample instance for a test case, 
            with the constructor's required attributes validator mocked 
            to ensure that an exception isn't raised.
        """

        # Provide name (required) for Sample, and any data that the
        # test case have via parameterization.
        if "data" in request.fixturenames:
            data = request.getfixturevalue("data")
        else:
            data = {}
        data.setdefault("sample_name", "test-sample")

        # Mock the validation and return a new Sample.
        rubber_stamper = mock.MagicMock(return_value=[])
        with mock.patch("looper.models.Sample.check_valid",
                        new=rubber_stamper):
            mocked_sample = looper.models.Sample(data)
        return mocked_sample



class SampleRequirementsTests:
    """ Test what a Sample requires. """

    @pytest.mark.parametrize(
        argnames="data_type", argvalues=[dict, Series],
        ids=lambda data_type: "data_type={}".format(data_type.__name__))
    @pytest.mark.parametrize(
        argnames="has_name", argvalues=[False, True],
        ids=lambda has_name: "has_name: {}".format(has_name))
    def test_requires_sample_name(self, has_name, data_type):
        data = {}
        sample_name_key = "sample_name"
        sample_name = "test-sample"
        if has_name:
            data[sample_name_key] = sample_name
            sample = Sample(data_type(data))
            assert sample_name == getattr(sample, sample_name_key)
        else:
            with pytest.raises(ValueError):
                Sample(data_type(data))



@pytest.mark.parametrize(
    argnames="accessor", argvalues=["attr", "item"],
    ids=lambda access_mode: "accessor={}".format(access_mode))
@pytest.mark.parametrize(argnames="data_type", argvalues=[dict, Series])
def test_exception_type_matches_access_mode(self, data_type, accessor):
    """ Exception for attribute access failure reflects access mode. """
    data = {"sample_name": "placeholder"}
    sample = Sample(data_type(data))
    if accessor == "attr":
        with pytest.raises(AttributeError):
            sample.undefined_attribute
    elif accessor == "item":
        with pytest.raises(KeyError):
            sample["not-set"]
    else:
        # Personal safeguard against unexpected behavior
        pytest.fail("Unknown access mode for exception type test: {}".
                    format(accessor))
