""" Tests for the Sample. """

from collections import Mapping
import copy
import pickle
import tempfile
import os


import mock
import numpy as np
from pandas import Series
import pytest
import yaml
from yaml import SafeLoader

from attmap import AttMap, EchoAttMap, PathExAttMap as PXAM
import peppy
from peppy import Project, Sample, SnakeProject
from peppy.const import *
from peppy.const import SNAKEMAKE_SAMPLE_COL
from peppy.project import RESULTS_FOLDER_VALUE, SUBMISSION_FOLDER_VALUE
from peppy.sample import PRJ_REF
from tests.helpers import named_param


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


def pytest_generate_tests(metafunc):
    """ Dynamic test case generation and parameterization for this module. """
    if "proj_type" in metafunc.fixturenames:
        metafunc.parametrize("proj_type", [Project, SnakeProject])


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
        sample.infer_attributes(implications)
        after_inference = sample.__dict__
        assert before_inference == after_inference

    def test_null_intersection_between_sample_and_implications(self, sample):
        """ Sample with none of implications' fields --> no change. """
        before_inference = sample.__dict__
        sample.infer_attributes(self.IMPLICATIONS_MAP)
        assert before_inference == sample.__dict__

    @pytest.mark.parametrize(
        argnames=["implier_value", "implications"],
        argvalues=IMPLICATIONS.items())
    def test_intersection_between_sample_and_implications(
            self, sample, implier_value, implications):
        """ Intersection between implications and sample fields --> append. """

        # Negative control pretest
        for implied_field_name in implications.keys():
            assert not hasattr(sample, implied_field_name)

        # Set the parameterized value for the implications source field.
        setattr(sample, self.IMPLIER_NAME, implier_value)
        sample.infer_attributes(self.IMPLICATIONS_MAP)

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
        sample.infer_attributes(self.IMPLICATIONS_MAP)
        no_implied_values()

    @pytest.fixture(scope="function")
    def sample(self, request):
        """
        Provide a Sample test case, with always-true validation.

        :param _pytest.fixtures.SubRequest request: test case requesting 
            a Sample instance.
        :return peppy.Sample: basic Sample instance for a test case,
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
                "peppy.sample.Sample.check_valid", new=rubber_stamper):
            mocked_sample = peppy.sample.Sample(data)
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
    sample_data = {SAMPLE_NAME_COLNAME: "test-sample",
                   DATA_SOURCE_COLNAME: file_text}
    s = Sample(sample_data)
    assert file_text == s.data_source
    assert files == s.input_file_paths
    if test_type == "to_disk":
        path_sample_file = tmpdir.join("test-sample.yaml").strpath
        s.to_yaml(path_sample_file)
        print("Sample items: {}".format(s.items()))
        with open(path_sample_file) as sf:
            reloaded_sample_data = yaml.load(sf, SafeLoader)
        print("reloaded keys: {}".format(list(reloaded_sample_data.keys())))
        try:
            s_reloaded = Sample(reloaded_sample_data)
        except Exception:
            with open(path_sample_file) as sf:
                print("LINES (below):\n{}".format("".join(sf.readlines())))
            raise
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
            METADATA_KEY: {
                NAME_TABLE_ATTR: "anns.csv", OUTDIR_KEY: "outdir",
                RESULTS_FOLDER_KEY: RESULTS_FOLDER_VALUE,
                SUBMISSION_FOLDER_KEY: SUBMISSION_FOLDER_VALUE},
            DATA_SOURCES_SECTION: self.DATA_SOURCES,
            DERIVATIONS_DECLARATION: [data_src]}

    @named_param(
        argnames="data_src_attr",
        argvalues=[DATA_SOURCE_COLNAME, "src", "filepath", "data"])
    @named_param(argnames="src_key", argvalues=SOURCE_KEYS)
    @named_param(argnames="explicit", argvalues=[False, True])
    def test_equivalence_between_implicit_and_explicit_prj(
            self, prj_data, data_src_attr, src_key, explicit):
        """ Passing Sample's project is equivalent to its inference. """
        
        # Explicitly-passed object needs to at least be an AttMap.
        sample_data = AttMap(
                {SAMPLE_NAME_COLNAME: "arbitrary_sample", "prj": prj_data,
                 data_src_attr: src_key, "derived_attributes": [data_src_attr]})
        
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
        prj_data_modified = AttMap(copy.deepcopy(prj_data))
        new_src = "src3"
        new_src_val = "newpath"
        assert new_src not in prj_data[DATA_SOURCES_SECTION]
        prj_data_modified[DATA_SOURCES_SECTION][new_src] = new_src_val
        sample_data = AttMap(
            {SAMPLE_NAME_COLNAME: "random-sample",
             "prj": prj_data, DATA_SOURCE_COLNAME: new_src})
        s = Sample(sample_data)
        s.set_file_paths(prj_data_modified)
        assert new_src_val == getattr(s, DATA_SOURCE_COLNAME)

    @named_param(argnames="exclude_derived_attributes", argvalues=[False, True])
    def test_no_derived_attributes(self, prj_data, exclude_derived_attributes):
        """ Passing Sample's project is equivalent to its inference. """

        # Here we're disinterested in parameterization w.r.t. data source key,
        # so make it constant.
        src_key = self.SOURCE_KEYS[0]

        # Explicitly-passed object needs to at least be an AttMap.
        if exclude_derived_attributes:
            prj_data.pop("derived_attributes")
        sample_data = {
                SAMPLE_NAME_COLNAME: "arbitrary_sample", "prj": prj_data,
                DATA_SOURCE_COLNAME: src_key}
        sample_data = AttMap(sample_data)
        s = Sample(sample_data)

        assert not hasattr(s, src_key)
        assert src_key not in s

        # Create the samples and make the calls under test.
        s = Sample(sample_data)
        s.set_file_paths()

        # Check results.
        putative_new_attr = self.DATA_SOURCES[src_key]
        if exclude_derived_attributes:
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

    def prj(self, tmpdir):
        fp = tmpdir.join("simple-prj-cfg.yaml").strpath
        with open(fp, 'w') as f:
            yaml.dump({METADATA_KEY: {OUTDIR_KEY: tmpdir.strpath}}, f)
        return Project(fp)

    @pytest.fixture
    def prj_data(self):
        """ Provide basic Project data to test case. """
        data = {METADATA_KEY: {NAME_TABLE_ATTR: "anns.csv"}}
        data.update({DATA_SOURCES_SECTION: self.PATH_BY_KEY})
        return data

    @named_param(
        argnames="colname",
        argvalues=[DATA_SOURCE_COLNAME, "data", "src", "input", "filepath"])
    @named_param(argnames="src_key", argvalues=SOURCE_KEYS)
    @named_param(argnames="data_type", argvalues=[dict, AttMap])
    @named_param(argnames="include_data_sources", argvalues=[False, True])
    def test_accuracy_and_allows_empty_data_sources(
            self, colname, src_key, prj_data, data_type, include_data_sources):
        """ Locator is accurate and does not require data source map. """
        sample_data = data_type(
            {SAMPLE_NAME_COLNAME: "random-sample",
             "prj": prj_data, colname: src_key})
        s = Sample(sample_data)
        assert isinstance(s.prj, AttMap)
        data_sources = s.prj.data_sources if include_data_sources else None
        path = s.locate_data_source(
                data_sources, column_name=colname, source_key=src_key)
        if include_data_sources:
            assert self.PATH_BY_KEY[src_key] == path
        else:
            assert path is None


class SampleConstructorTests:
    """ Basic tests of Sample's constructor """

    @pytest.mark.parametrize("name_attr", [SAMPLE_NAME_COLNAME, "name"])
    @pytest.mark.parametrize("fetch", [getattr, lambda s, k: s[k]])
    def test_only_peppy_name(self, fetch, name_attr):
        """ name and sample_name access Sample's name and work with varied syntax. """
        name = "testsample"
        s = Sample({SAMPLE_NAME_COLNAME: name})
        assert name == fetch(s, name_attr)

    @pytest.mark.parametrize("name_attr", [SAMPLE_NAME_COLNAME, "name"])
    @pytest.mark.parametrize(["fetch", "exp_err"], [
        (getattr, AttributeError), (lambda s, k: s[k], KeyError)])
    def test_only_snakemake_name(self, fetch, name_attr, exp_err):
        """ Snakemake --> peppy <--> sample --> sample_name. """
        name = "testsample"
        s = Sample({SNAKEMAKE_SAMPLE_COL: name})
        with pytest.raises(exp_err):

            fetch(s, SNAKEMAKE_SAMPLE_COL)
        assert name == fetch(s, name_attr)

    @pytest.mark.parametrize("name_attr", [SAMPLE_NAME_COLNAME, "name"])
    @pytest.mark.parametrize(["fetch", "exp_err"], [
        (getattr, AttributeError), (lambda s, k: s[k], KeyError)])
    @pytest.mark.parametrize(["data", "expect_result"], [
        ({SNAKEMAKE_SAMPLE_COL: "testsample", SAMPLE_NAME_COLNAME: "testsample"},
         "testsample"),
        ({SNAKEMAKE_SAMPLE_COL: "nameA", SAMPLE_NAME_COLNAME: "nameB"},
         Exception)
    ])
    def test_peppy_and_snakemake_names(
            self, fetch, name_attr, data, expect_result, exp_err):
        """ Original peppy naming of sample name is favored; exception iff values differ. """
        if isinstance(expect_result, type) and issubclass(expect_result, Exception):
            with pytest.raises(expect_result):
                Sample(data)
        else:
            s = Sample(data)
            assert expect_result == fetch(s, name_attr)
            with pytest.raises(exp_err):
                fetch(s, SNAKEMAKE_SAMPLE_COL)

    @pytest.mark.parametrize(["has_ref", "get_ref"], [
        (lambda s: hasattr(s, PRJ_REF), lambda s: getattr(s, PRJ_REF)),
        (lambda s: PRJ_REF in s, lambda s: s[PRJ_REF])])
    def test_no_prj_ref(self, has_ref, get_ref):
        """ Construction of a Sample without project ref --> null value """
        s = Sample({SAMPLE_NAME_COLNAME: "test-sample"})
        assert has_ref(s)
        assert get_ref(s) is None

    @pytest.mark.parametrize(
        "fetch", [lambda s: getattr(s, PRJ_REF), lambda s: s[PRJ_REF]])
    @pytest.mark.parametrize(["prj_ref_val", "expect"], [
        (None, None), ({}, None), (AttMap(), None), (EchoAttMap(), None),
        ({"a": 1}, PXAM({"a": 1})), (AttMap({"b": 2}), PXAM({"b": 2})),
        (PXAM({"c": 3}), PXAM({"c": 3})), (EchoAttMap({"d": 4}), EchoAttMap({"d": 4}))])
    def test_non_project_prj_ref(self, fetch, prj_ref_val, expect):
        """ Project reference is null, or a PathExAttMap. """
        s = Sample({SAMPLE_NAME_COLNAME: "testsample", PRJ_REF: prj_ref_val})
        assert expect == fetch(s)

    @pytest.mark.parametrize(
        "fetch", [lambda s: getattr(s, PRJ_REF), lambda s: s[PRJ_REF]])
    @pytest.mark.parametrize(["prj_ref_val", "expect"], [
        (None, None), ({}, None), (AttMap(), None), (EchoAttMap(), None),
        ({"a": 1}, PXAM({"a": 1})), (AttMap({"b": 2}), PXAM({"b": 2})),
        (PXAM({"c": 3}), PXAM({"c": 3})), (EchoAttMap({"d": 4}), EchoAttMap({"d": 4}))])
    def test_non_project_prj_ref_as_arg(self, fetch, prj_ref_val, expect):
        """ Project reference must be null, or an attmap bounded above by PathExAttMap. """
        s = Sample({SAMPLE_NAME_COLNAME: "testsample"}, prj=prj_ref_val)
        assert expect == fetch(s)

    @pytest.mark.parametrize(
        "fetch", [#lambda s: getattr(s, PRJ_REF),
                  lambda s: s[PRJ_REF]
                  ])
    def test_project_prj_ref_in_data(self, proj_type, fetch, tmpdir):
        """ Project is converted to PathExAttMap of sample-independent data. """
        proj_data = {METADATA_KEY: {OUTDIR_KEY: tmpdir.strpath}}
        prj = _get_prj(
            tmpdir.join("minimal_config.yaml").strpath, proj_data, proj_type)
        assert isinstance(prj, Project)
        s = Sample({SAMPLE_NAME_COLNAME: "testsample", PRJ_REF: prj})
        self._assert_prj_dat(proj_data, s, fetch)

    @pytest.mark.parametrize(
        "fetch", [lambda s: getattr(s, PRJ_REF), lambda s: s[PRJ_REF]])
    def test_project_prj_ref_as_arg(self, proj_type, fetch, tmpdir):
        """ Project is converted to PathExAttMap of sample-independent data. """
        proj_data = {METADATA_KEY: {OUTDIR_KEY: tmpdir.strpath}}
        prj = _get_prj(
            tmpdir.join("minimal_config.yaml").strpath, proj_data, proj_type)
        assert isinstance(prj, Project)
        s = Sample({SAMPLE_NAME_COLNAME: "testsample"}, prj=prj)
        self._assert_prj_dat(proj_data, s, fetch)

    @pytest.mark.skip("not implemented")
    def test_prj_ref_data_and_arg(self):
        """ Directly-specified project is favored. """
        pass

    def _assert_prj_dat(self, base_data, s, fetch):
        obs = fetch(s)
        assert isinstance(obs, Mapping) and not isinstance(obs, Project)
        exp_meta, obs_meta = base_data[METADATA_KEY], obs[METADATA_KEY]
        missing = {k: v for k, v in exp_meta.items() if k not in obs_meta}
        assert {} == missing
        diff = {k: (exp_meta[k], obs_meta[k])
                for k in set(exp_meta.keys()) & set(obs_meta.keys())
                if exp_meta[k] != obs_meta[k]}
        assert {} == diff
        extra = [v for k, v in obs_meta.items() if k not in exp_meta]
        assert not any(extra)


class SampleSerializationTests:
    """ Basic tests of Sample serialization with pickle module. """

    @pytest.mark.parametrize("name_attr", [SAMPLE_NAME_COLNAME, "name"])
    def test_pickle_roundtrip(self, name_attr):
        """ Test whether pickle roundtrip produces a comparable object """
        name = "testsample"
        s = Sample({SAMPLE_NAME_COLNAME: name})

        _buffer = tempfile.TemporaryFile()
        pickle.dump(s, _buffer)
        _buffer.seek(0)
        new_s = pickle.load(_buffer)
        assert s == new_s


def _get_prj(conf_file, data, proj_type):
    with open(conf_file, 'w') as f:
        yaml.dump(data, f)
    return proj_type(conf_file)
