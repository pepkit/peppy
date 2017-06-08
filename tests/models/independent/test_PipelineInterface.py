""" Tests for PipelineInterface ADT. """

import itertools
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
        funcname_and_kwargs, resources, use_resources, basic_pipe_iface_data):
    """ Each public function throws same exception given unmapped pipeline. """
    pipe_iface_config = _add_resources(basic_pipe_iface_data, resources) \
            if use_resources else basic_pipe_iface_data
    pi = PipelineInterface(pipe_iface_config)
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


    def test_no_default_no_sufficient(self, basic_pipe_iface_data, resources):
        """ If provided, resources specification needs 'default.' """
        del resources[DEFAULT_COMPUTE_RESOURCES_NAME]
        pipe_iface_config = _add_resources(basic_pipe_iface_data, resources)
        pi = PipelineInterface(pipe_iface_config)
        for pipeline in pipe_iface_config.keys():
            with pytest.raises(_InvalidResourceSpecificationException):
                pi.choose_resource_package(
                        pipeline, file_size=HUGE_RESOURCES["file_size"] + 1)


    @pytest.mark.parametrize(argnames="file_size", argvalues=[-1, 10, 101])
    def test_resources_not_required(self, basic_pipe_iface_data, file_size):
        """ Compute resource specification is optional. """
        pi = PipelineInterface(basic_pipe_iface_data)
        for pipeline in basic_pipe_iface_data.keys():
            assert {} == pi.choose_resource_package(pipeline, int(file_size))
            assert {} == pi.choose_resource_package(pipeline, float(file_size))


    @pytest.mark.parametrize(
            argnames=["file_size", "expected_resources"],
            argvalues=[(0, DEFAULT_RESOURCES), (4, DEFAULT_RESOURCES),
                       (16, MIDSIZE_RESOURCES), (64, HUGE_RESOURCES)])
    def test_selects_proper_resource_package(
            self, resources, basic_pipe_iface_data,
            file_size, expected_resources):
        """ Minimal resource package sufficient for pipeline and file size. """
        resources["midsize"] = MIDSIZE_RESOURCES
        pipe_iface_config = _add_resources(basic_pipe_iface_data, resources)
        pi = PipelineInterface(pipe_iface_config)
        for pipeline in pipe_iface_config.keys():
            assert expected_resources == \
                   pi.choose_resource_package(pipeline, file_size)



@pytest.mark.skip("Not implemented")
class PipelineInterfaceArgstringTests:
    """  """
    pass



@pytest.mark.skip("Not implemented")
class PipelineInterfaceLooperArgsTests:
    """  """
    pass



def _add_resources(pipe_iface_config, resources):
    """ Add resource bundle data to each config section. """
    for pipe_data in pipe_iface_config.values():
        pipe_data["resources"] = resources
    return pipe_iface_config
