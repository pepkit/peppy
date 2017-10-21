""" Tests for the Sample. """

import copy
import os
import yaml
import mock
import numpy as np
from pandas import Series
import pytest
import looper
from looper.models import \
    AttributeDict, Sample, DATA_SOURCE_COLNAME, \
    DATA_SOURCES_SECTION, SAMPLE_NAME_COLNAME
from tests.helpers import named_param


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
        """ Construction of sample requires data with sample name. """
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
    sample_data = {"sample_name": "test-sample",
                   DATA_SOURCE_COLNAME: file_text}
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


    SOURCE_KEYS = ["src1", "src2"]
    DATA_SOURCES = {"src1": "pathA", "src2": "pathB"}


    @pytest.fixture
    def prj_data(self, request):
        """ Provide test case with some basic Project data. """
        if "data_src_attr" in request.fixturenames:
            data_src = request.getfixturevalue("data_src_attr")
        else:
            data_src = DATA_SOURCE_COLNAME
        return {
            "metadata": {
                "sample_annotation": "anns.csv", "output_dir": "outdir",
                "results_subdir": "results_pipeline",
                "submission_subdir": "submission"},
            DATA_SOURCES_SECTION: self.DATA_SOURCES,
            "derived_columns": [data_src]}


    @named_param(
        argnames="data_src_attr",
        argvalues=[DATA_SOURCE_COLNAME, "src", "filepath", "data"])
    @named_param(argnames="src_key", argvalues=SOURCE_KEYS)
    @named_param(argnames="explicit", argvalues=[False, True])
    def test_equivalence_between_implicit_and_explicit_prj(
            self, prj_data, data_src_attr, src_key, explicit):
        """ Passing Sample's project is equivalent to its inference. """
        
        # Explicitly-passed object needs to at least be an AttributeDict.
        sample_data = AttributeDict(
                {SAMPLE_NAME_COLNAME: "arbitrary_sample", "prj": prj_data,
                 data_src_attr: src_key, "derived_columns": [data_src_attr]})
        
        # Create the samples and make the calls under test.
        s = Sample(sample_data)
        if explicit:
            s.set_file_paths(sample_data.prj)
        else:
            s.set_file_paths()
        
        # Check results.
        expected = self.DATA_SOURCES[src_key]
        observed = getattr(s, data_src_attr)
        assert expected == observed


    def test_prefers_explicit_project_context(self, prj_data):
        """ Explicit project data overrides any pre-stored project data. """
        prj_data_modified = AttributeDict(copy.deepcopy(prj_data))
        new_src = "src3"
        new_src_val = "newpath"
        assert new_src not in prj_data[DATA_SOURCES_SECTION]
        prj_data_modified[DATA_SOURCES_SECTION][new_src] = new_src_val
        sample_data = AttributeDict(
            {SAMPLE_NAME_COLNAME: "random-sample",
             "prj": prj_data, DATA_SOURCE_COLNAME: new_src})
        s = Sample(sample_data)
        s.set_file_paths(prj_data_modified)
        assert new_src_val == getattr(s, DATA_SOURCE_COLNAME)


    @named_param(argnames="exclude_derived_columns", argvalues=[False, True])
    def test_no_derived_columns(self, prj_data, exclude_derived_columns):
        """ Passing Sample's project is equivalent to its inference. """

        # Here we're disinterested in parameterization w.r.t. data source key,
        # so make it constant.
        src_key = self.SOURCE_KEYS[0]

        # Explicitly-passed object needs to at least be an AttributeDict.
        if exclude_derived_columns:
            prj_data.pop("derived_columns")
        sample_data = {
                SAMPLE_NAME_COLNAME: "arbitrary_sample", "prj": prj_data,
                DATA_SOURCE_COLNAME: src_key}
        sample_data = AttributeDict(sample_data)
        s = Sample(sample_data)

        assert not hasattr(s, src_key)
        assert src_key not in s

        # Create the samples and make the calls under test.
        s = Sample(sample_data)
        s.set_file_paths()

        # Check results.
        putative_new_attr = self.DATA_SOURCES[src_key]
        if exclude_derived_columns:
            # The value to which the source key maps won't have been added.
            assert not hasattr(s, putative_new_attr)
            assert putative_new_attr not in s
        else:
            # The value to which the source key maps will have been added.
            assert putative_new_attr == getattr(s, DATA_SOURCE_COLNAME)
            assert putative_new_attr == s[DATA_SOURCE_COLNAME]



class LocateDataSourceTests:
    """ Tests for determining data source filepath. """

    SOURCE_KEYS = ["src1", "src2"]
    PATH_BY_KEY = {"src1": "pathA", "src2": "pathB"}


    @pytest.fixture
    def prj_data(self):
        """ Provide basic Project data to test case. """
        data = {"metadata": {"sample_annotation": "anns.csv"}}
        data.update({DATA_SOURCES_SECTION: self.PATH_BY_KEY})
        return data


    @named_param(
        argnames="colname",
        argvalues=[DATA_SOURCE_COLNAME, "data", "src", "input", "filepath"])
    @named_param(argnames="src_key", argvalues=SOURCE_KEYS)
    @named_param(argnames="data_type", argvalues=[dict, AttributeDict])
    @named_param(argnames="include_data_sources", argvalues=[False, True])
    def test_accuracy_and_allows_empty_data_sources(
            self, colname, src_key, prj_data, data_type, include_data_sources):
        """ Locator is accurate and does not require data source map. """
        sample_data = data_type(
            {SAMPLE_NAME_COLNAME: "random-sample",
             "prj": prj_data, colname: src_key})
        s = Sample(sample_data)
        data_sources = s.prj.data_sources if include_data_sources else None
        path = s.locate_data_source(
                data_sources, column_name=colname, source_key=src_key)
        if include_data_sources:
            assert self.PATH_BY_KEY[src_key] == path
        else:
            assert path is None
