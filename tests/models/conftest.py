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

from pep import DEFAULT_COMPUTE_RESOURCES_NAME, SAMPLE_NAME_COLNAME


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
            "Sample": lambda data: pd.Series(data)}
    which_class = request.getfixturevalue("class_name")
    return transformation_by_class[which_class](instance_raw_data)



@pytest.fixture(scope="function")
def env_config_filepath(tmpdir):
    """ Write default project/compute environment file for Project ctor. """
    conf_file = tmpdir.join(DEFAULT_COMPUTE_CONFIG_FILENAME)
    conf_file.write(ENV_CONF_LINES)
    return conf_file.strpath



@pytest.fixture(scope="function")
def instance_raw_data(request, basic_data_raw):
    """ Supply the raw data for a basic model instance as a fixture. """
    which_class = request.getfixturevalue("class_name")
    return copy.deepcopy(basic_data_raw[which_class])



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
def path_proj_conf_file(tmpdir, proj_conf):
    """ Write basic project configuration data and provide filepath. """
    conf_path = os.path.join(tmpdir.strpath, "project_config.yaml")
    with open(conf_path, 'w') as conf:
        yaml.safe_dump(proj_conf, conf)
    return conf_path



@pytest.fixture(scope="function")
def path_anns_file(request, tmpdir, sample_sheet):
    """ Write basic annotations, optionally using a different delimiter. """
    filepath = os.path.join(tmpdir.strpath, "annotations.csv")
    if "delimiter" in request.fixturenames:
        delimiter = request.getfixturevalue("delimiter")
    else:
        delimiter = ","
    with open(filepath, 'w') as anns_file:
        sample_sheet.to_csv(anns_file, sep=delimiter, index=False)
    return filepath



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
