""" Models' tests' configuration. """

import pytest


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



CONFIG_FILENAME = "test-proj-conf.yaml"
ANNOTATIONS_FILENAME = "anns.csv"
SAMPLE_NAME_1 = "test-sample-1"
SAMPLE_NAME_2 = "test-sample-2"
MINIMAL_SAMPLE_ANNS_LINES = ["sample_name", SAMPLE_NAME_1, SAMPLE_NAME_2]
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
    conf_file = tmpdir.join(DEFAULT_COMPUTE_CONFIG_FILENAME)
    conf_file.write(ENV_CONF_LINES)
    return conf_file.strpath



@pytest.fixture(scope="function")
def minimal_project_conf_path(tmpdir):
    """ Write minimal sample annotations and project configuration. """
    anns_file = tmpdir.join(ANNOTATIONS_FILENAME)
    anns_file.write("\n".join(MINIMAL_SAMPLE_ANNS_LINES))
    conf_file = tmpdir.join(CONFIG_FILENAME)
    config_lines = \
            "metadata:\n  sample_annotation: {}".format(anns_file.strpath)
    conf_file.write(config_lines)
    return conf_file.strpath
