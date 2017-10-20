""" Tests for the Sample. """

import os
import yaml
import mock
import numpy as np
from pandas import Series
import pytest
import looper
from looper.models import AttributeDict, Sample, SAMPLE_NAME_COLNAME


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



class ParseSampleImplicationsTests:
    """ Tests for appending columns/fields to a Sample based on a mapping. """

    IMPLIER_NAME = SAMPLE_NAME_COLNAME
    IMPLIER_VALUES = ["a", "b"]
    SAMPLE_A_IMPLICATIONS = {"genome": "hg38", "phenome": "hg72"}
    SAMPLE_B_IMPLICATIONS = {"genome": "hg38"}
    IMPLICATIONS = {"a": SAMPLE_A_IMPLICATIONS, "b": SAMPLE_B_IMPLICATIONS}
    IMPLICATIONS_MAP = {IMPLIER_NAME: IMPLICATIONS}


    @pytest.mark.parametrize(argnames="implications", argvalues=[None, {}, []])
    def test_project_no_implications(self, sample, implications):
        """ With no implications mapping, sample is unmodified. """
        before_inference = sample.__dict__
        sample.infer_columns(implications)
        after_inference = sample.__dict__
        assert before_inference == after_inference


    def test_null_intersection_between_sample_and_implications(self, sample):
        """ Sample with none of implications' fields --> no change. """
        before_inference = sample.__dict__
        sample.infer_columns(self.IMPLICATIONS_MAP)
        assert before_inference == sample.__dict__


    @pytest.mark.parametrize(
        argnames=["implier_value", "implications"],
        argvalues=IMPLICATIONS.items(),
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
        sample.infer_columns(self.IMPLICATIONS_MAP)

        # Validate updates to sample based on column implications & inference.
        for implied_name, implied_value in implications.items():
            assert implied_value == getattr(sample, implied_name)


    @pytest.mark.parametrize(
        argnames="unmapped_implier_value",
        argvalues=["totally-wacky-value", 62, None, np.nan])
    def test_sample_has_unmapped_value_for_implication(
            self, sample, unmapped_implier_value):
        """ Unknown value in implier field --> null inference. """

        # Negative control pre-/post-test.
        def no_implied_values():
            assert all([not hasattr(sample, implied_field_name)
                        for implied_field_name in self.IMPLICATIONS.keys()])

        no_implied_values()
        setattr(sample, self.IMPLIER_NAME, unmapped_implier_value)
        sample.infer_columns(self.IMPLICATIONS_MAP)
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
        data.setdefault(SAMPLE_NAME_COLNAME, "test-sample")

        # Mock the validation and return a new Sample.
        rubber_stamper = mock.MagicMock(return_value=[])
        with mock.patch(
                "looper.models.Sample.check_valid", new=rubber_stamper):
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
        sample_name = "test-sample"
        if has_name:
            data[SAMPLE_NAME_COLNAME] = sample_name
            sample = Sample(data_type(data))
            assert sample_name == getattr(sample, SAMPLE_NAME_COLNAME)
        else:
            with pytest.raises(ValueError):
                Sample(data_type(data))



@pytest.mark.parametrize(
    argnames="accessor", argvalues=["attr", "item"],
    ids=lambda access_mode: "accessor={}".format(access_mode))
@pytest.mark.parametrize(argnames="data_type", argvalues=[dict, Series])
def test_exception_type_matches_access_mode(data_type, accessor):
    """ Exception for attribute access failure reflects access mode. """
    data = {SAMPLE_NAME_COLNAME: "placeholder"}
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



@pytest.mark.parametrize(
        argnames="paths",
        argvalues=[["subfolder0a", "subfolder0b"],
                   [os.path.join("subfolder1", "subfolder2")]])
@pytest.mark.parametrize(
        argnames="preexists", argvalues=[False, True],
        ids=lambda exists: "preexists={}".format(exists))
def test_make_sample_dirs(paths, preexists, tmpdir):
    """ Existence guarantee Sample instance's folders is safe and valid. """

    # Derive full paths and assure nonexistence before creation.
    fullpaths = []
    for p in paths:
        fullpath = tmpdir.join(p).strpath
        assert not os.path.exists(fullpath)
        if preexists:
            os.makedirs(fullpath)
        fullpaths.append(fullpath)

    # Make the sample and assure paths preexistence.
    s = Sample({SAMPLE_NAME_COLNAME: "placeholder"})
    s.paths = fullpaths

    # Base the test's initial condition on the parameterization.
    if preexists:
        def precheck(flags):
            return all(flags)
    else:
        def precheck(flags):
            return not any(flags)
    assert precheck([os.path.exists(p) for p in s.paths])

    # The sample folders creation call should do nothing.
    s.make_sample_dirs()
    assert all([os.path.exists(p) for p in s.paths])



@pytest.mark.parametrize(
    argnames="files",
    argvalues=[[],
               ["dummy-input-file.bam"],
               ["input1_R1.fastq", "input1_R2.fastq"]])
@pytest.mark.parametrize(
    argnames="test_type", argvalues=["in_memory", "to_disk"])
def test_input_files(files, test_type, tmpdir):
    """ Test for access to Sample input files. """
    file_text = " ".join(files)
    sample_data = {"sample_name": "test-sample", "data_source": file_text}
    s = Sample(sample_data)
    assert file_text == s.data_source
    assert files == s.input_file_paths
    if test_type == "to_disk":
        path_sample_file = tmpdir.join("test-sample.yaml").strpath
        s.to_yaml(path_sample_file)
        with open(path_sample_file) as sf:
            reloaded_sample_data = yaml.load(sf)
        s_reloaded = Sample(reloaded_sample_data)
        assert files == s_reloaded.input_file_paths



class SetFilePathsTests:
    """ Tests for setting Sample file paths. """


    @pytest.fixture
    def sample_data(self):
        return {SAMPLE_NAME_COLNAME: "arbitrary_sample"}


    @pytest.mark.parametrize(
            argnames="prj_data", argvalues=[
                {"metadata": {"sample_annotation": "anns.csv",
                    "output_dir": "outdir", "submission_subdir": "submission"}},
                {"metadata": {"sample_annotation": "annotations.csv",
                    "output_dir": "outfolder", "results_subdir": "results"}}])
    @pytest.mark.parametrize(
            argnames="prj_type", argvalues=[dict, AttributeDict, Series])
    def test_accepts_its_own_project_context(
            self, sample_data, prj_data, prj_type):
        p = prj_type(prj_data)
        s = Sample(p)



    def test_infers_its_own_project_context(self):
        pass


    def test_prefers_foreign_project_context(self):
        pass


    def test_no_derived_columns(self):
        pass
