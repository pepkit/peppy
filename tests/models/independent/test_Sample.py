""" Tests for the Sample. """

import os
import tempfile
import mock
import numpy as np
from pandas import Series
import pytest
import looper
from looper.models import Sample, SAMPLE_NAME_COLNAME


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



def pytest_generate_tests(metafunc):
    """ Customization of this module's test cases. """
    if metafunc.cls == CustomSampleTests:
        if "subclass_attrname" in metafunc.fixturenames:
            metafunc.parametrize(argnames="subclass_attrname",
                                 argvalues=["library", "protocol"])
        if "pipelines_type" in metafunc.fixturenames:
            metafunc.parametrize(argnames="pipelines_type",
                                 argvalues=["module", "package"])




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



@pytest.mark.skip("Not implemented")
class CustomSampleTests:
    """ Bespoke Sample creation tests. """


    PROTOCOLS = ["WGBS", "RRBS", "ATAC-Seq", "RNA-seq"]


    @pytest.mark.fixture(scope="function")
    def sample_subclass_definition(self, tmpdir, request):
        subclass_attrname = request.getfixturevalue("subclass_attrname")
        pipelines_type = request.getfixturevalue("pipelines_type")
        if "pipe_path" in request.fixturenames:
            pipe_path = tmpdir.strpath
        else:
            pipe_path = request.getfixturevalue("pipe_path")
        if pipelines_type == "module":
            pipe_path = os.path.join(pipe_path, "pipelines.py")
        elif pipelines_type == "package":
            init_file = os.path.join(pipe_path, "__init__.py")
            with open(init_file, 'w') as f:
                pass
            module_file = tempfile.NamedTemporaryFile(dir=pipe_path, suffix=".py", delete=False)
            module_file.close()
            with open(module_file.name, 'w') as modfile:
                # TODO: write out definition.
                pass
        else:
            raise ValueError(
                    "Unknown pipelines type: {}; module and package "
                    "are supported".format(pipelines_type))

        # TODO: ensure cleanup.
        request.addfinalizer()


    DATA_FOR_SAMPLES = {
            SAMPLE_NAME_COLNAME: ["sample{}".format(i) for i in range(3)],
            "arbitrary-value": list(np.random.randint(-1000, 1000, size=3))}


    CLASS_DEFINITION_LINES = """\"\"\" Sample subclass test file.  \"\"\"
    
    from looper.models import Sample
    
    class DummySampleSubclass(Sample):
        \"\"\" Subclass shell to test Project's Sample subclass seek sensitivity. \"\"\"
        __{attribute_name}__ = {attribute_value}
        pass
        
    class NotSampleSubclass(Sample):
        \"\"\" Subclass shell to test Project's Sample subclass seek specificity. \"\"\"
        __unrecognized__ = irrelevant
    
    """


    def test_generic_sample_for_unfindable_subclass(self):
        """ If no Sample subclass is found, a generic Sample is created. """
        pass


    def test_raw_pipelines_import_has_sample_subclass(
            self, pipelines_type, subclass_attrname):
        """ Project finds Sample subclass in pipelines package. """
        pass


    def test_project_pipelines_dir_has_sample_subclass(
            self, pipelines_type, subclass_attrname):
        """ Project finds Sample subclass in optional pipelines_dir. """
        pass


    def test_sample_subclass_messaging(
            self, pipelines_type, subclass_attrname):
        """ Sample subclass seek process provides info about procedure. """
        pass



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
