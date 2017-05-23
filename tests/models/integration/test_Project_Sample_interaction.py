""" Tests for interaction between a Project and a Sample. """

import pytest
import yaml


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



@pytest.fixure(scope="function")
def name_config_file():
    return "proj-conf.yaml"



@pytest.fixture(scope="function")
def project_config(request):
    # Requesting test case must provide path to temp folder.
    tmpfolder = request.getfixturevalue("tmpdir")
    name_conf_file = request.getfixturevalue(name_config_file.__name__)
    path_conf_file = tmpfolder.join(name_config_file)



@pytest.fixture(scope="function")
def config_data(request):
    return {"sample_annotation": "sample-annotations-dummy.csv"}



@pytest.mark.skip("Not implemented")
class ProjectSampleInteractionTests:
    """ Tests for interaction between Project and Sample. """

    @pytest.mark.parametrize(
            argnames="uses_paths_section", argvalues=[False, True],
            ids=lambda has_paths: "paths_section={}".format(has_paths))
    def test_sample_folders_creation(
            self, uses_paths_section, tmpdir, name_config_file, config_data):
        pass
