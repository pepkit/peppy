""" Models' tests' configuration. """

from collections import OrderedDict
import pytest
import pandas as pd


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



@pytest.fixture(scope="function")
def env_config_filepath(tmpdir):
    """ Write default project/compute environment file for Project ctor. """
    conf_file = tmpdir.join(DEFAULT_COMPUTE_CONFIG_FILENAME)
    conf_file.write(ENV_CONF_LINES)
    return conf_file.strpath



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
