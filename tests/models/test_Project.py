""" Tests for the NGS Project model. """

import os
import pytest
from looper.models import Project


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


CONFIG_FILENAME = "test-proj-conf.yaml"
ANNOTATIONS_FILENAME = "anns.csv"
SAMPLE_NAME_1 = "test-sample-1"
SAMPLE_NAME_2 = "test-sample-2"
MINIMAL_SAMPLE_ANNS_LINES = ["sample_name", SAMPLE_NAME_1, SAMPLE_NAME_2]



@pytest.fixture(scope="function")
def proj_conf_path(tmpdir):
    anns_file = tmpdir.join(ANNOTATIONS_FILENAME)
    anns_file.write("\n".join(MINIMAL_SAMPLE_ANNS_LINES))
    conf_file = tmpdir.join(CONFIG_FILENAME)
    conflines = "metadata:\n  sample_annotation: {}".format(anns_file.strpath)
    conf_file.write(conflines)
    return conf_file.strpath



class ProjectRequirementsTests:
    """ Tests for a Project's set of requirements. """


    def test_minimal_configuration_doesnt_fail(self, proj_conf_path):
        Project(config_file=proj_conf_path)


    def test_minimal_configuration_name_inference(self, tmpdir, proj_conf_path):
        project = Project(proj_conf_path)
        _, expected_name = os.path.split(tmpdir.strpath)
        assert expected_name == project.name


    def test_minimal_configuration_output_dir(self, tmpdir, proj_conf_path):
        project = Project(proj_conf_path)
        assert tmpdir.strpath == project.output_dir
