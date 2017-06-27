""" Configuration for modules with independent tests of models. """

from collections import OrderedDict
import copy
import os
import sys
if sys.version_info < (3, 3):
    from collections import Iterable, Mapping
else:
    from collections.abc import Iterable, Mapping

import pandas as pd
import pytest
import yaml

from looper.models import DEFAULT_COMPUTE_RESOURCES_NAME, SAMPLE_NAME_COLNAME


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

BASIC_PROTOMAP = {"ATAC": "ATACSeq.py"}

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
    """ Oft-used as filename for pipeline module and PipelineInterface key. """
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
def basic_data_raw():
    return copy.deepcopy({
            "AttributeDict": {}, "ProtocolMapper": BASIC_PROTOMAP,
            "Sample": {SAMPLE_NAME_COLNAME: "arbitrary-sample"}})



@pytest.fixture(scope="function")
def basic_instance_data(request, instance_raw_data):
    """
    Transform the raw data for a basic model instance to comply with its ctor.

    :param pytest._pytest.fixtures.SubRequest request: test case requesting
        the basic instance data
    :param Mapping instance_raw_data: the raw data needed to create a
        model instance
    :return object: basic instance data in a form accepted by its constructor
    """
    # Cleanup is free with _write_config, using request's temp folder.
    transformation_by_class = {
            "AttributeDict": lambda data: data,
            "PipelineInterface": lambda data:
                    _write_config(data, request, "pipeline_interface.yaml"),
            "ProtocolInterface": lambda data:
                    _write_config(data, request, "pipeline_interface.yaml"),
            "ProtocolMapper": lambda data: data,
            "Sample": lambda data: pd.Series(data)}
    which_class = request.getfixturevalue("class_name")
    return transformation_by_class[which_class](instance_raw_data)



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
def instance_raw_data(request, basic_data_raw, atacseq_piface_data):
    """ Supply the raw data for a basic model instance as a fixture. """
    which_class = request.getfixturevalue("class_name")
    if which_class == "PipelineInterface":
        return copy.deepcopy(atacseq_piface_data)
    elif which_class == "ProtocolInterface":
        return {"protocol_mapping":
                        copy.deepcopy(basic_data_raw["ProtocolMapper"]),
                "pipelines": copy.deepcopy(atacseq_piface_data)}
    else:
        return copy.deepcopy(basic_data_raw[which_class])



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



def _write_config(data, request, filename):
    """
    Write configuration data to file.

    :param str Sequence | Mapping data: data to write to file, YAML compliant
    :param pytest._pytest.fixtures.SubRequest request: test case that
        requested a fixture from which this function was called
    :param str filename: name for the file to write
    :return str: full path to the file written
    """
    # We get cleanup for free by writing to file in requests temp folder.
    dirpath = request.getfixturevalue("tmpdir").strpath
    filepath = os.path.join(dirpath, filename)
    with open(filepath, 'w') as conf_file:
        yaml.safe_dump(data, conf_file)
    return filepath
