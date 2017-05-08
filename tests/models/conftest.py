""" Models' tests' configuration. """

import pytest


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



CONFIG_FILENAME = "test-proj-conf.yaml"
ANNOTATIONS_FILENAME = "anns.csv"
SAMPLE_NAME_1 = "test-sample-1"
SAMPLE_NAME_2 = "test-sample-2"
MINIMAL_SAMPLE_ANNS_LINES = ["sample_name", SAMPLE_NAME_1, SAMPLE_NAME_2]



@pytest.fixture(scope="function")
def minimal_project_conf_path(tmpdir):
    """ Write minimal sample annotations and project configuration. """
    anns_file = tmpdir.join(ANNOTATIONS_FILENAME)
    anns_file.write("\n".join(MINIMAL_SAMPLE_ANNS_LINES))
    conf_file = tmpdir.join(CONFIG_FILENAME)
    conflines = "metadata:\n  sample_annotation: {}".format(anns_file.strpath)
    conf_file.write(conflines)
    return conf_file.strpath


