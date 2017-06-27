""" Configuration for modules with independent tests of models. """

from collections import OrderedDict
import copy
import sys
if sys.version_info < (3, 3):
    from collections import Iterable, Mapping
else:
    from collections.abc import Iterable, Mapping

import pandas as pd
import pytest

from looper.models import DEFAULT_COMPUTE_RESOURCES_NAME


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



CONFIG_FILENAME = "test-proj-conf.yaml"
ANNOTATIONS_FILENAME = "anns.csv"
SAMPLE_NAME_1 = "test-sample-1"
SAMPLE_NAME_2 = "test-sample-2"
SAMPLE_NAMES = [SAMPLE_NAME_1, SAMPLE_NAME_2]
DATA_VALUES = [1, 2]
DEFAULT_COMPUTE_CONFIG_FILENAME = "default-environment-settings.yaml"
ENV_CONF_LINES = """compute:
  default:
    submission_template: templates/slurm_template.sub
    submission_command: sbatch
    partition: parallel
  econ:
    submission_template: templates/slurm_template.sub
    submission_command: sbatch
    partition: economy
  local:
    submission_template: templates/localhost_template.sub
    submission_command: sh
"""


# Compute resource bundles for pipeline interface configuration data
DEFAULT_RESOURCES = {"file_size": 0, "cores": 1, "mem": 8000,
                     "time": "0-01:00:00", "partition": "local"}
MIDSIZE_RESOURCES = {"file_size": 10, "cores": 8, "mem": 16000,
                     "time": "0-07:00:00", "partition": "serial"}
HUGE_RESOURCES = {"file_size": 30, "cores": 24, "mem": 64000,
                  "time": "30-00:00:00", "partition": "longq"}



def pytest_generate_tests(metafunc):
    """ Conditional customization of test cases in this directory. """
    try:
        classname = metafunc.cls.__name__
    except AttributeError:
        # Some functions don't belong to a class.
        pass
    else:
        if classname == "ConstructorPathParsingTests":
            # Provide test case with two PipelineInterface config bundles.
            metafunc.parametrize(
                    argnames="config_bundles",
                    argvalues=[(atacseq_iface_without_resources(),
                                {"name": "sans-path"})])



@pytest.fixture(scope="function")
def atacseq_iface_without_resources():
    """
    Provide the ATAC-Seq pipeline interface as a fixture, without resources.

    Note that this represents the configuration data for the interface for a
    single pipeline. In order to use this in the form that a PipelineInterface
    expects, this needs to be the value to which a key is mapped within a
    larger Mapping.

    :return Mapping: all of the pipeline interface configuration data for
        ATAC-Seq, minus the resources section
    """
    return {
        "name": "ATACseq",
        "looper_args": True,
        "required_input_files": ["read1", "read2"],
        "all_input_files": ["read1", "read2"],
        "ngs_input_files": ["read1", "read2"],
        "arguments": {
            "--sample-name": "sample_name",
            "--genome": "genome",
            "--input": "read1",
            "--input2": "read2",
            "--single-or-paired": "read_type"
        },
        "optional_arguments": {
            "--frip-ref-peaks": "FRIP_ref",
            "--prealignments": "prealignments",
            "--genome-size": "macs_genome_size"
        }
    }



@pytest.fixture(scope="function")
def atac_pipe_name():
    return "ATACSeq.py"



@pytest.fixture(scope="function")
def atacseq_iface_with_resources(
        atacseq_iface_without_resources, resources):
    """

    :param dict atacseq_iface_without_resources: PipelineInterface config
        data, minus a resources section
    :param Mapping resources: resources section of PipelineInterface
        configuration data
    :return Mapping: pipeline interface data for ATAC-Seq pipeline, with all
        of the base sections plus resources section
    """
    iface_data = copy.deepcopy(atacseq_iface_without_resources)
    iface_data["resources"] = copy.deepcopy(resources)
    return iface_data



@pytest.fixture(scope="function")
def atacseq_piface_data(atacseq_iface_with_resources, atac_pipe_name):
    """
    Provide a test case with data for an ATACSeq PipelineInterface.

    :param str atac_pipe_name: name/key for the pipeline to which the
        interface data pertains
    :return dict: configuration data needed to create PipelineInterface
    """
    return {atac_pipe_name: copy.deepcopy(atacseq_iface_with_resources)}



@pytest.fixture(scope="function")
def default_resources():
    """ Provide test case with default PipelineInterface resources section. """
    return copy.deepcopy(DEFAULT_RESOURCES)



@pytest.fixture(scope="function")
def env_config_filepath(tmpdir):
    """ Write default project/compute environment file for Project ctor. """
    conf_file = tmpdir.join(DEFAULT_COMPUTE_CONFIG_FILENAME)
    conf_file.write(ENV_CONF_LINES)
    return conf_file.strpath



@pytest.fixture(scope="function")
def huge_resources():
    """ Provide non-default resources spec. section for PipelineInterface. """
    return copy.deepcopy(HUGE_RESOURCES)



@pytest.fixture(scope="function")
def midsize_resources():
    """ Provide non-default resources spec. section for PipelineInterface. """
    return copy.deepcopy(MIDSIZE_RESOURCES)



@pytest.fixture(scope="function")
def minimal_project_conf_path(tmpdir):
    """ Write minimal sample annotations and project configuration. """
    anns_file = tmpdir.join(ANNOTATIONS_FILENAME).strpath
    df = pd.DataFrame(OrderedDict([("sample_name", SAMPLE_NAMES),
                                   ("data", DATA_VALUES)]))
    with open(anns_file, 'w') as annotations:
        df.to_csv(annotations, sep=",", index=False)
    conf_file = tmpdir.join(CONFIG_FILENAME)
    config_lines = \
            "metadata:\n  sample_annotation: {}".format(anns_file)
    conf_file.write(config_lines)
    return conf_file.strpath



@pytest.fixture(scope="function")
def piface_config_bundles(request, resources):
    """
    Provide the ATAC-Seq pipeline interface as a fixture, including resources.

    Note that this represents the configuration data for the interface for a
    single pipeline. In order to use this in the form that a PipelineInterface
    expects, this needs to be the value to which a key is mapped within a
    larger Mapping.

    :param pytest._pytest.fixtures.SubRequest request: hook into test case
        requesting this fixture, which is queried for a resources value with
        which to override the default if it's present.
    :param Mapping resources: pipeline interface resource specification
    :return Iterable[Mapping]: collection of bundles of pipeline interface
        configuration bundles
    """
    iface_config_datas = request.getfixturevalue("config_bundles")
    if isinstance(iface_config_datas, Mapping):
        data_bundles = iface_config_datas.values()
    elif isinstance(iface_config_datas, Iterable):
        data_bundles = iface_config_datas
    else:
        raise TypeError("Expected mapping or list collection of "
                        "PipelineInterface data: {} ({})".format(
                iface_config_datas, type(iface_config_datas)))
    resource_specification = request.getfixturevalue("resources") \
            if "resources" in request.fixturenames else resources
    for config_bundle in data_bundles:
        config_bundle.update(resource_specification)
    return iface_config_datas



@pytest.fixture(scope="function")
def resources():
    """ Basic PipelineInterface compute resources data. """
    return {DEFAULT_COMPUTE_RESOURCES_NAME: copy.deepcopy(DEFAULT_RESOURCES),
            "huge": copy.copy(HUGE_RESOURCES)}
