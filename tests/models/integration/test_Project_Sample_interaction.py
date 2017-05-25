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
    "output_dir": "temporary/sequencing/results",
    "results_subdir": "results",
    "submission_subdir": "submission",
    "input_dir": "dummy/sequencing/data",
    "tools_folder": "arbitrary-seq-tools-folder"}



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
            self, uses_paths_section, num_samples, project):
        """ Sample folders can be created regardless of declaration style. """

        # Not that the paths section usage flag and the sample count
        # are used by the project configuration fixture.

        assert not any([os.path.exists(path)
                        for s in project.samples for path in s.paths])
        for s in project.samples:
            s.make_sample_dirs()
            assert all([os.path.exists(path) for path in s.paths])



@pytest.fixture(scope="function")
def project(request, tmpdir, env_config_filepath):
    """ Provide requesting test case with a basic Project instance. """

    # Write just the sample names as the annotations.
    annotations_filename = "anns-fill.csv"
    anns_path = tmpdir.join(annotations_filename).strpath
    num_samples = request.getfixturevalue("num_samples")
    with open(anns_path, 'w') as anns_file:
        anns_file.write("sample_name\n")
        anns_file.write("\n".join(
                ["sample{}".format(i) for i in range(1, num_samples + 1)]))

    # Create the Project config data.
    config_data = {"metadata": {SAMPLE_ANNOTATIONS_KEY: annotations_filename}}
    if request.getfixturevalue(request.cls.CONFIG_DATA_PATHS_HOOK):
        config_data["paths"] = {}
        paths_dest = config_data["paths"]
    else:
        paths_dest = config_data["metadata"]

    # Add the paths data to the Project config.
    for path_name, path in PATH_BY_TYPE.items():
        paths_dest[path_name] = os.path.join(tmpdir.strpath, path)

    # Write the Project config file.
    conf_path = tmpdir.join("proj-conf.yaml").strpath
    with open(conf_path, 'w') as conf_file:
        yaml.safe_dump(config_data, conf_file)

    return Project(conf_path, default_compute=env_config_filepath)
