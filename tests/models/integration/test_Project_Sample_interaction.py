""" Tests for interaction between a Project and a Sample. """

import os
import pytest
import yaml
from looper.models import Project, SAMPLE_ANNOTATIONS_KEY


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



# Arbitrary (but reasonable) path names/types to use to test
# Project construction behavior with respect to config file format.
PATH_BY_TYPE = {
    "output_dir": "/home/guest/sequencing/results",
    "results_subdir": "results",
    "submission_subdir": "submission",
    "input_dir": "/home/guest/sequencing/data",
    "tools_folder": "/usr/local/bin"}



class ProjectSampleInteractionTests:
    """ Tests for interaction between Project and Sample. """

    CONFIG_DATA_PATHS_HOOK = "uses_paths_section"
    EXPECTED_PATHS = {
            os.path.join(PATH_BY_TYPE[name], path) 
            if name in ["results_subdir", "submission_subdir"] 
            else path for name, path in PATH_BY_TYPE.items()}

    @pytest.mark.parametrize(
            argnames=CONFIG_DATA_PATHS_HOOK, argvalues=[False, True],
            ids=lambda has_paths: "paths_section={}".format(has_paths))
    @pytest.mark.parametrize(
            argnames="num_samples", argvalues=range(1, 4), 
            ids=lambda n_samples: "samples={}".format(n_samples))
    def test_sample_folders_creation(
            self, uses_paths_section, num_samples,
            project_config, env_config_filepath):
        """ Sample folders can be created regardless of declaration style. """

        # Not that the paths section usage flag and the sample count
        # are used by the project configuration fixture.

        prj = Project(project_config, default_compute=env_config_filepath)
        assert not any([os.path.exists(path)
                        for s in prj.samples for path in s.paths])
        prj.samples[0].make_sample_dirs()
        assert all([os.path.exists(path)
                    for s in prj.samples for path in s.paths])



@pytest.fixture(scope="function")
def project_config(request, tmpdir):

    annotations_filename = "anns-fill.csv"
    anns_file = tmpdir.join(annotations_filename)
    num_samples = request.getfixturevalue("num_samples")
    anns_file.write("sample_name\n")
    anns_file.write("\n".join(
            ["sample{}".format(i) for i in range(num_samples)]))
    config_data = {"metadata": {SAMPLE_ANNOTATIONS_KEY: annotations_filename}}

    if request.getfixturevalue(request.cls.CONFIG_DATA_PATHS_HOOK):
        config_data["paths"] = {}
        paths_dest = config_data["paths"]
    else:
        paths_dest = config_data["metadata"]

    for path_name, path in PATH_BY_TYPE.items():
        paths_dest[path_name] = path

    conf_file = tmpdir.join("proj-conf.yaml")
    yaml.safe_dump(config_data, conf_file)
    return conf_file.strpath
