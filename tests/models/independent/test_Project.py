""" Tests for the NGS Project model. """

import os
import pytest
from looper.models import Project, MissingMetadataException


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



class ProjectRequirementsTests:
    """ Tests for a Project's set of requirements. """


    def test_lacks_sample_annotations(self):
        """ Lack of sample annotations precludes Project construction. """
        with pytest.raises(MissingMetadataException):
            # TODO: implement
            raise Exception()


    def test_minimal_configuration_doesnt_fail(
            self, minimal_project_conf_path, env_config_filepath):
        """ Project construction requires nothing """
        Project(config_file=minimal_project_conf_path,
                default_compute=env_config_filepath)


    def test_minimal_configuration_name_inference(
            self, tmpdir, minimal_project_conf_path, env_config_filepath):
        """ Project infers name from where its configuration lives. """
        project = Project(minimal_project_conf_path,
                          default_compute=env_config_filepath)
        _, expected_name = os.path.split(tmpdir.strpath)
        assert expected_name == project.name


    def test_minimal_configuration_output_dir(
            self, tmpdir, minimal_project_conf_path, env_config_filepath):
        """ Project infers output path from its configuration location. """
        project = Project(minimal_project_conf_path,
                          default_compute=env_config_filepath)
        assert tmpdir.strpath == project.output_dir
