""" Tests for PipelineInterface ADT. """

import itertools
import random

import pytest
import yaml

from looper.models import \
    PipelineInterface, _InvalidResourceSpecificationException, \
    _MissingPipelineConfigurationException, DEFAULT_COMPUTE_RESOURCES_NAME


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


# Values with which to build pipeline interface keys and names
PIPELINE_NAMES = ["ATACseq", "WGBS"]
EXTENSIONS = [".py", ".sh", ".R"]

# Compute resource bundles for pipeline interface configuration data
DEFAULT_RESOURCES = {"file_size": 0, "cores": 1, "mem": 8000,
                     "time": "0-01:00:00", "partition": "local"}
MIDSIZE_RESOURCES = {"file_size": 10, "cores": 8, "mem": 16000,
                     "time": "0-07:00:00", "partition": "serial"}
HUGE_RESOURCES = {"file_size": 30, "cores": 24, "mem": 64000,
                  "time": "30-00:00:00", "partition": "longq"}
HUGE_RESOURCES_NAME = "huge"



def pytest_generate_tests(metafunc):
    """ Customization specific to test cases in this module. """
    try:
        parameters = metafunc.cls.PARAMETERS
    except AttributeError:
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
def resources():
    """ Basic PipelineInterface compute resources data. """
    return {DEFAULT_COMPUTE_RESOURCES_NAME: DEFAULT_RESOURCES,
            "huge": HUGE_RESOURCES}



@pytest.mark.parametrize(argnames="from_file", argvalues=[False, True])
def test_constructor_input_types(tmpdir, from_file, basic_pipe_iface_data):
    """ PipelineInterface constructor handles Mapping or filepath. """
    if from_file:
        pipe_iface_config = tmpdir.join("pipe-iface-conf.yaml").strpath
        with open(tmpdir.join("pipe-iface-conf.yaml").strpath, 'w') as f:
            yaml.safe_dump(basic_pipe_iface_data, f)
    else: pipe_iface_config = basic_pipe_iface_data
    pi = PipelineInterface(pipe_iface_config)
    assert basic_pipe_iface_data == pi.pipe_iface_config
    assert pi.pipe_iface_file == (pipe_iface_config if from_file else None)



@pytest.fixture(scope="function", autouse=True)
def pi_with_resources(request, basic_pipe_iface_data, resources):
    """ Add resource bundle data to each config section. """
    if "modify_resources" in request.fixturenames:
        modify_resources = request.getfixturevalue("modify_resources")
        modify_resources(resources)
    if "file_size_attr" in request.fixturenames:
        file_size_name = request.getfixturevalue("file_size_attr")
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



@pytest.mark.parametrize(
        argnames="funcname_and_kwargs",
        argvalues=[("choose_resource_package", {"file_size": 4}),
                   ("get_arg_string", {"sample": "arbitrary-sample-name"}),
                   ("get_attribute",
                    {"attribute_key": "irrelevant-attr-name"}),
                   ("get_pipeline_name", {}),
                   ("uses_looper_args", {})])
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
    funcname, kwargs = funcname_and_kwargs
    with pytest.raises(_MissingPipelineConfigurationException):
        getattr(pi, funcname).__call__("missing-pipeline", **kwargs)



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
            pi = PipelineInterface(pi_config_data)
            for expected_name, pipeline in zip(pipeline_names, pipelines):
                assert expected_name == pi.get_pipeline_name(pipeline)



class PipelineInterfaceResourcePackageTests:
    """ Tests for pipeline's specification of compute resources. """

    PARAMETERS = {"file_size_attr": ["file_size", "min_file_size"]}


    def test_requires_default(
            self, file_size_attr, pi_with_resources):
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
                        name, file_size=HUGE_RESOURCES[file_size_attr] + 1)


    def test_negative_file_size_request(
            self, file_size_attr, pi_with_resources):
        """ Negative file size is prohibited. """
        pi = pi_with_resources
        for pipeline_name in pi.pipeline_names:
            negative_file_size = -10 * random.random()
            with pytest.raises(ValueError):
                pi.choose_resource_package(
                        pipeline_name, file_size=negative_file_size)


    @pytest.mark.parametrize(argnames="file_size", argvalues=[0, 10, 101])
    def test_resources_not_required(self, file_size_attr, file_size, pi_with_resources):
        """ Compute resource specification is optional. """
        pi = pi_with_resources
        for pipe_data in pi.pipelines:
            del pipe_data["resources"]
        for pipe_name in pi.pipeline_names:
            assert {} == pi.choose_resource_package(pipe_name, int(file_size))
            assert {} == pi.choose_resource_package(pipe_name, float(file_size))


    @pytest.mark.parametrize(
            argnames=["file_size", "expected_resources"],
            argvalues=[(0, DEFAULT_RESOURCES), (4, DEFAULT_RESOURCES),
                       (16, MIDSIZE_RESOURCES), (64, HUGE_RESOURCES)])
    @pytest.mark.parametrize(
            argnames="modify_resources",
            argvalues=[lambda resources: resources.update(
                    {"midsize": MIDSIZE_RESOURCES})])
    def test_selects_proper_resource_package(
            self, file_size_attr, modify_resources, pi_with_resources,
            file_size, expected_resources):
        """ Minimal resource package sufficient for pipeline and file size. """
        for pipe_name in pi_with_resources.pipeline_names:
            observed_resources = pi_with_resources.choose_resource_package(
                    pipe_name, file_size)
            assert expected_resources == observed_resources


    @pytest.mark.parametrize(
            argnames="modify_resources",
            argvalues=[lambda resources:
                       map(lambda package: package.update({"file_size": -5}),
                           resources.values())])
    def test_negative_file_size_prohibited(
            self, file_size_attr, modify_resources, pi_with_resources):
        """ Negative min file size in resource package spec is prohibited. """
        for pipe_name in pi_with_resources.pipeline_names:
            file_size_request = random.randrange(1, 11)
            with pytest.raises(ValueError):
                pi_with_resources.choose_resource_package(
                        pipe_name, file_size_request)


    @pytest.mark.skip("Not implemented")
    def test_file_size_spec_not_required_for_default(self, file_size_attr):
        """ Default package implies minimum file size of zero. """
        pass


    @pytest.mark.skip("Not implemented")
    @pytest.mark.parametrize(
            argnames="min_file_size", argvalues=[None, -1, 0, 1])
    def test_default_package_enforces_zero_file_size(self, file_size_attr, min_file_size):
        """ Default resource package sets minimum file size to zero. """
        pass


    @pytest.mark.skip("Not implemented")
    def test_file_size_spec_required_for_non_default_packages(self, file_size_attr):
        pass



@pytest.mark.skip("Not implemented")
class PipelineInterfaceArgstringTests:
    """  """
    pass



@pytest.mark.skip("Not implemented")
class PipelineInterfaceLooperArgsTests:
    """  """
    pass
