""" Tests for PipelineInterface ADT. """

import copy
import inspect
import itertools
import logging
import os
import random

import mock
import pytest
import yaml

from pep import \
    PipelineInterface, Project, Sample, DEFAULT_COMPUTE_RESOURCES_NAME, \
    SAMPLE_ANNOTATIONS_KEY, SAMPLE_NAME_COLNAME
from pep.pipeline_interface import \
    _InvalidResourceSpecificationException, \
    _MissingPipelineConfigurationException


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


_LOGGER = logging.getLogger(__name__)


# Values with which to build pipeline interface keys and names
PIPELINE_NAMES = ["ATACseq", "WGBS"]
EXTENSIONS = [".py", ".sh", ".R"]



def pytest_generate_tests(metafunc):
    """ Customization specific to test cases in this module. """
    try:
        parameters = metafunc.cls.PARAMETERS
    except AttributeError:
        _LOGGER.debug("No indirect parameterization for test class: '{}'".
                      format(metafunc.cls))
        pass
    else:
        for name, values in parameters.items():
            metafunc.parametrize(argnames=name, argvalues=values)



@pytest.fixture(scope="function")
def basic_pipe_iface_data(request):
    """ Minimal PipelineInterface configuration data. """
    extension = request.getfixturevalue("extension") \
            if "extension" in request.fixturenames else ".py"
    return {pipe_name + extension: {"name": pipe_name}
            for pipe_name in PIPELINE_NAMES}



@pytest.fixture(scope="function")
def pi_with_resources(request, basic_pipe_iface_data, resources):
    """ Add resource bundle data to each config section. """
    if "use_new_file_size" in request.fixturenames:
        file_size_name = "min_file_size" if \
                request.getfixturevalue("use_new_file_size") else "file_size"
        for rp_data in resources.values():
            size1 = rp_data.pop("file_size", None)
            size2 = rp_data.pop("min_file_size", None)
            size = size1 or size2
            if size:
                rp_data[file_size_name] = size
    pipe_iface_config = PipelineInterface(basic_pipe_iface_data)
    for pipe_data in pipe_iface_config.pipelines:
        pipe_data["resources"] = resources
    return pipe_iface_config



@pytest.mark.parametrize(argnames="from_file", argvalues=[False, True])
def test_constructor_input_types(tmpdir, from_file, basic_pipe_iface_data):
    """ PipelineInterface constructor handles Mapping or filepath. """
    if from_file:
        pipe_iface_config = tmpdir.join("pipe-iface-conf.yaml").strpath
        with open(tmpdir.join("pipe-iface-conf.yaml").strpath, 'w') as f:
            yaml.safe_dump(basic_pipe_iface_data, f)
    else:
        pipe_iface_config = basic_pipe_iface_data
    pi = PipelineInterface(pipe_iface_config)
    assert basic_pipe_iface_data == pi.pipe_iface_config
    assert pi.pipe_iface_file == (pipe_iface_config if from_file else None)



@pytest.mark.parametrize(
        argnames="funcname_and_kwargs",
        argvalues=[("choose_resource_package", {"file_size": 4}),
                   ("get_arg_string",
                    {"sample": Sample(
                            {"sample_name": "arbitrary-sample-name"})}),
                   ("get_attribute",
                    {"attribute_key": "irrelevant-attr-name"}),
                   ("get_pipeline_name", {})])
@pytest.mark.parametrize(argnames="use_resources", argvalues=[False, True])
def test_unconfigured_pipeline_exception(
        funcname_and_kwargs, use_resources, pi_with_resources):
    """ Each public function throws same exception given unmapped pipeline. """
    pi = pi_with_resources
    if not use_resources:
        for pipeline in pi.pipelines:
            try:
                del pipeline["resources"][DEFAULT_COMPUTE_RESOURCES_NAME]
            except KeyError:
                # Already no default resource package.
                pass

    # Each of the functions being tested should take pipeline_name arg,
    # and we want to test behavior for the call on an unknown pipeline.
    funcname, kwargs = funcname_and_kwargs
    func = getattr(pi, funcname)
    required_parameters = inspect.getargspec(func).args
    for parameter in ["pipeline_name", "pipeline"]:
        if parameter in required_parameters and parameter not in kwargs:
            kwargs[parameter] = "missing-pipeline"
    with pytest.raises(_MissingPipelineConfigurationException):
        func.__call__(**kwargs)



class PipelineInterfaceNameResolutionTests:
    """ Name is explicit or inferred from key. """


    @pytest.mark.parametrize(
            argnames="name_and_ext_pairs",
            argvalues=itertools.combinations(
                    itertools.product(PIPELINE_NAMES, EXTENSIONS), 2))
    def test_get_pipeline_name_explicit(self, name_and_ext_pairs):
        """ Configuration can directly specify pipeline name. """
        names, extensions = zip(*name_and_ext_pairs)
        pipelines = [name + ext for name, ext in name_and_ext_pairs]
        pi_conf_data = {pipeline: {"name": name}
                        for pipeline, name in zip(pipelines, names)}
        pi = PipelineInterface(pi_conf_data)
        for pipeline, expected_name in zip(pipelines, names):
            assert expected_name == pi.get_pipeline_name(pipeline)


    def test_get_pipeline_name_inferred(self):
        """ Script implies pipeline name if it's not explicitly configured. """
        pipeline_names = ["wgbs", "atacseq"]
        for extensions in itertools.combinations(EXTENSIONS, 2):
            pipelines = [name + ext for name, ext
                         in zip(pipeline_names, extensions)]
            pi_config_data = {pipeline: None for pipeline in pipelines}
            with mock.patch("pep.pipeline_interface.PipelineInterface._expand_paths"):
                pi = PipelineInterface(pi_config_data)
            for expected_name, pipeline in zip(pipeline_names, pipelines):
                assert expected_name == pi.get_pipeline_name(pipeline)



class PipelineInterfaceResourcePackageTests:
    """ Tests for pipeline's specification of compute resources. """

    PARAMETERS = {"use_new_file_size": [False, True]}


    def test_requires_default(
            self, use_new_file_size, pi_with_resources, huge_resources):
        """ If provided, resources specification needs 'default.' """
        pi = pi_with_resources
        for name, pipeline in pi:
            try:
                del pipeline["resources"][DEFAULT_COMPUTE_RESOURCES_NAME]
            except KeyError:
                # Already no default resource package.
                pass
            assert "default" not in pipeline["resources"]
            with pytest.raises(_InvalidResourceSpecificationException):
                pi.choose_resource_package(
                        name, file_size=huge_resources["file_size"] + 1)


    def test_negative_file_size_request(
            self, use_new_file_size, pi_with_resources):
        """ Negative file size is prohibited. """
        pi = pi_with_resources
        for pipeline_name in pi.pipeline_names:
            negative_file_size = -10 * random.random()
            with pytest.raises(ValueError):
                pi.choose_resource_package(
                        pipeline_name, file_size=negative_file_size)


    @pytest.mark.parametrize(argnames="file_size", argvalues=[0, 10, 101])
    def test_resources_not_required(
            self, use_new_file_size, file_size, pi_with_resources):
        """ Compute resource specification is optional. """
        pi = pi_with_resources
        for pipe_data in pi.pipelines:
            del pipe_data["resources"]
        for pipe_name in pi.pipeline_names:
            assert {} == pi.choose_resource_package(pipe_name, int(file_size))
            assert {} == pi.choose_resource_package(pipe_name, float(file_size))


    @pytest.mark.parametrize(
            argnames=["file_size", "expected_package_name"],
            argvalues=[(0, "default"), (4, "default"),
                       (16, "midsize"), (64, "huge")])
    def test_selects_proper_resource_package(
            self, use_new_file_size, pi_with_resources,
            file_size, expected_package_name, midsize_resources):
        """ Minimal resource package sufficient for pipeline and file size. """
        for pipe_data in pi_with_resources.pipelines:
            pipe_data["resources"].update(
                    {"midsize": copy.deepcopy(midsize_resources)})
        for pipe_name, pipe_data in pi_with_resources:
            observed_package = pi_with_resources.choose_resource_package(
                pipe_name, file_size)
            expected_package = copy.deepcopy(
                    pipe_data["resources"][expected_package_name])
            assert expected_package == observed_package


    def test_negative_file_size_prohibited(
            self, use_new_file_size, pi_with_resources):
        """ Negative min file size in resource package spec is prohibited. """
        file_size_attr = "min_file_size" if use_new_file_size else "file_size"
        for pipe_data in pi_with_resources.pipelines:
            for package_data in pipe_data["resources"].values():
                package_data[file_size_attr] = -5 * random.random()
        for pipe_name in pi_with_resources.pipeline_names:
            file_size_request = random.randrange(1, 11)
            with pytest.raises(ValueError):
                pi_with_resources.choose_resource_package(
                        pipe_name, file_size_request)


    def test_file_size_spec_not_required_for_default(
            self, use_new_file_size, basic_pipe_iface_data, 
            default_resources, huge_resources, midsize_resources):
        """ Default package implies minimum file size of zero. """

        def clear_file_size(resource_package):
            for fs_var_name in ("file_size", "min_file_size"):
                if fs_var_name in resource_package:
                    del resource_package[fs_var_name]

        # Create the resource package specification data.
        resources_data = dict(zip(
                ["default", "midsize", "huge"],
                [copy.deepcopy(data) for data in
                 [default_resources, midsize_resources, huge_resources]]))
        for pack_name, pack_data in resources_data.items():
            # Use file size spec name as appropriate; clean default package.
            if pack_name == "default":
                clear_file_size(pack_data)
            elif use_new_file_size:
                pack_data["min_file_size"] = pack_data.pop("file_size")

        # Add resource package spec data and create PipelineInterface.
        pipe_iface_data = copy.deepcopy(basic_pipe_iface_data)
        for pipe_data in pipe_iface_data.values():
            pipe_data["resources"] = resources_data
        pi = PipelineInterface(pipe_iface_data)

        # We should always get default resource package for mini file.
        for pipe_name, pipe_data in pi:
            default_resource_package = \
                    pipe_data["resources"][DEFAULT_COMPUTE_RESOURCES_NAME]
            clear_file_size(default_resource_package)
            assert default_resource_package == \
                   pi.choose_resource_package(pipe_name, 0.001)


    @pytest.mark.parametrize(
            argnames="min_file_size", argvalues=[-1, 1])
    def test_default_package_new_name_zero_size(
            self, use_new_file_size, min_file_size, pi_with_resources):
        """ Default resource package sets minimum file size to zero. """

        for pipe_name, pipe_data in pi_with_resources:
            # Establish faulty default package setting for file size.
            default_resource_package = pipe_data["resources"]["default"]
            if use_new_file_size:
                if "file_size" in default_resource_package:
                    del default_resource_package["file_size"]
                default_resource_package["min_file_size"] = min_file_size
            else:
                if "min_file_size" in default_resource_package:
                    del default_resource_package["min_file_size"]
                default_resource_package["file_size"] = min_file_size

            # Get the resource package to validate.
            # Requesting file size of 0 should always trigger default package.
            observed_resource_package = \
                    pi_with_resources.choose_resource_package(pipe_name, 0)

            # Default package is an early adopter of the new file size name.
            expected_resource_package = copy.deepcopy(default_resource_package)
            if "file_size" in expected_resource_package:
                del expected_resource_package["file_size"]
            # Default packages forces its file size value to 0.
            expected_resource_package["min_file_size"] = 0

            assert expected_resource_package == observed_resource_package


    def test_file_size_spec_required_for_non_default_packages(
            self, use_new_file_size, basic_pipe_iface_data, 
            default_resources, huge_resources):
        """ Resource packages besides default require file size. """

        # Establish the resource specification.
        resource_package_data = {
                "default": copy.deepcopy(default_resources),
                "huge": copy.deepcopy(huge_resources)}

        # Remove file size for non-default; set it for default.
        del resource_package_data["huge"]["file_size"]
        if use_new_file_size:
            resource_package_data["default"]["min_file_size"] = \
                    resource_package_data["default"].pop("file_size")

        # Create the PipelineInterface.
        for pipe_data in basic_pipe_iface_data.values():
            pipe_data["resources"] = resource_package_data
        pi = PipelineInterface(basic_pipe_iface_data)

        # Attempt to select resource package should fail for each pipeline,
        # regardless of the file size specification; restrict to nonnegative
        # file size requests to avoid collision with ValueError that should
        # arise if requesting resource package for a negative file size value.
        for pipe_name in pi.pipeline_names:
            with pytest.raises(KeyError):
                pi.choose_resource_package(pipe_name, random.randrange(0, 10))



class ConstructorPathParsingTests:
    """ The constructor is responsible for expanding pipeline path(s). """

    ADD_PATH = [True, False]
    PIPELINE_KEYS = ["ATACSeq.py", "no_path.py"]
    RELATIVE_PATH_DATA = [
            ("./arbitrary-test-pipelines",
             {},
             "./arbitrary-test-pipelines"),
            ("path/to/$TEMP_PIPE_LOCS",
             {"TEMP_PIPE_LOCS": "validation-value"},
             "path/to/validation-value")]
    ABSOLUTE_PATHS = [
            os.path.join("~", "code_home", "bioinformatics"),
            os.path.join("$TEMP_TEST_HOME", "subfolder"),
            os.path.join("~", "$TEMPORARY_SUBFOLDER", "leaf")]
    ABSPATH_ENVVARS = {"TEMP_TEST_HOME": "tmptest-home-folder",
                       "TEMPORARY_SUBFOLDER": "temp-subfolder"}
    EXPECTED_PATHS_ABSOLUTE = [
            os.path.join(os.path.expanduser("~"), "code_home",
                         "bioinformatics"),
            os.path.join("tmptest-home-folder", "subfolder"),
            os.path.join(os.path.expanduser("~"), "temp-subfolder", "leaf")]


    @pytest.fixture(scope="function")
    def pipe_iface_data(self, piface_config_bundles):
        return dict(zip(self.PIPELINE_KEYS, piface_config_bundles))


    @pytest.fixture(scope="function", autouse=True)
    def apply_envvars(self, request):
        """ Use environment variables temporarily. """

        if "envvars" not in request.fixturenames:
            # We're autousing, so check for the relevant fixture.
            return

        original_envvars = {}
        new_envvars = request.getfixturevalue("envvars")

        # Remember values that are replaced as variables are updated.
        for name, value in new_envvars.items():
            try:
                original_envvars[name] = os.environ[name]
            except KeyError:
                pass
            os.environ[name] = value

        def restore():
            # Restore swapped variables and delete added ones.
            for k, v in new_envvars.items():
                try:
                    os.environ[k] = original_envvars[k]
                except KeyError:
                    del os.environ[k]
        request.addfinalizer(restore)


    def test_no_path(self, config_bundles, piface_config_bundles,
                     pipe_iface_data):
        """ PipelineInterface config sections need not specify path. """
        pi = PipelineInterface(pipe_iface_data)
        for pipe_key in self.PIPELINE_KEYS:
            piface_config = pi[pipe_key]
            # Specific negative test of interest.
            assert "path" not in piface_config
            # Positive control validation.
            assert pipe_iface_data[pipe_key] == piface_config


    @pytest.mark.parametrize(
            argnames=["pipe_path", "envvars", "expected"],
            argvalues=RELATIVE_PATH_DATA)
    def test_relative_path(
            self, config_bundles, piface_config_bundles, pipe_iface_data,
            pipe_path, envvars, expected, apply_envvars):
        """
        PipelineInterface construction expands pipeline path.

        Environment variable(s) expand(s), but the path remains relative
        if specified as such, deferring the joining with pipelines location,
        which makes the path absolute, until the path is actually used.

        """
        for add_path, pipe_key in zip(self.ADD_PATH, self.PIPELINE_KEYS):
            if add_path:
                pipe_iface_data[pipe_key]["path"] = pipe_path
        pi = PipelineInterface(pipe_iface_data)
        for add_path, pipe_key in zip(self.ADD_PATH, self.PIPELINE_KEYS):
            if add_path:
                assert expected == pi[pipe_key]["path"]
            else:
                assert "path" not in pi[pipe_key]


    @pytest.mark.parametrize(
            argnames=["pipe_path", "envvars", "expected"],
            argvalues=zip(ABSOLUTE_PATHS,
                          len(ABSOLUTE_PATHS) * [ABSPATH_ENVVARS],
                          EXPECTED_PATHS_ABSOLUTE))
    def test_path_expansion(
            self, pipe_path, envvars, expected,
            config_bundles, piface_config_bundles, pipe_iface_data):
        """ User/environment variables are expanded. """
        for piface_data in pipe_iface_data.values():
            piface_data["path"] = pipe_path
        pi = PipelineInterface(pipe_iface_data)
        for _, piface_data in pi:
            assert expected == piface_data["path"]



@pytest.mark.usefixtures("write_project_files", "pipe_iface_config_file")
class BasicPipelineInterfaceTests:
    """ Test cases specific to PipelineInterface """

    def test_missing_input_files(self, proj):
        """ We're interested here in lack of exception, not return value. """
        proj.samples[0].get_attr_values("all_input_files")



@pytest.mark.skip("Not implemented")
class PipelineInterfaceArgstringTests:
    """  """
    pass



@pytest.mark.skip("Not implemented")
class PipelineInterfaceLooperArgsTests:
    """  """
    pass



@pytest.mark.skip("Not implemented")
class GenericProtocolMatchTests:
    """ Pipeline interface may support 'all-other' protocols notion. """


    NAME_ANNS_FILE = "annotations.csv"


    @pytest.fixture
    def prj_data(self):
        """ Provide basic Project data. """
        return {"metadata": {"output_dir": "output",
                             "results_subdir": "results_pipeline",
                             "submission_subdir": "submission"}}


    @pytest.fixture
    def sheet_lines(self):
        """ Provide sample annotations sheet lines. """
        return ["{},{}".format(SAMPLE_NAME_COLNAME, "basic_sample")]


    @pytest.fixture
    def sheet_file(self, tmpdir, sheet_lines):
        """ Write annotations sheet file and provide path. """
        anns_file = tmpdir.join(self.NAME_ANNS_FILE)
        anns_file.write(os.linesep.join(sheet_lines))
        return anns_file.strpath


    @pytest.fixture
    def iface_paths(self, tmpdir):
        """ Write basic pipeline interfaces and provide paths. """
        pass


    @pytest.fixture
    def prj(self, tmpdir, prj_data, anns_file, iface_paths):
        """ Provide basic Project. """
        prj_data["pipeline_interfaces"] = iface_paths
        prj_data["metadata"][SAMPLE_ANNOTATIONS_KEY] = anns_file
        prj_file = tmpdir.join("pconf.yaml").strpath
        with open(prj_file, 'w') as f:
            yaml.dump(prj_data, f)
        return Project(prj_file)


    @pytest.mark.skip("Not implemented")
    def test_specific_protocol_match_lower_priority_interface(self):
        """ Generic protocol mapping doesn't preclude specific ones. """
        pass


    @pytest.mark.skip("Not implemented")
    def test_no_specific_protocol_match(self):
        """ Protocol match in no pipeline interface allows generic match. """
        pass
