""" Tests for the NGS Project model. """

import os
import pytest
import yaml
from looper.models import Project, MissingMetadataException


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



class ProjectRequirementsTests:
    """ Tests for a Project's set of requirements. """

    NO_ANNOTATIONS_CONFIG_DATA = \
        {"metadata": {
            "output_dir": "$HOME/sequencing/output",
            "pipelines_dir": "${CODE}/pipelines"},
        "data_sources": {"arbitrary": "placeholder/data/{filename}"},
        "genomes": {"human": "hg19", "mouse": "mm10"},
        "transcriptomes": {"human": "hg19_cdna", "mouse": "mm10_cdna"}}


    def test_lacks_sample_annotations(self, env_config_filepath, tmpdir):
        """ Lack of sample annotations precludes Project construction. """
        conf_path = tmpdir.join("proj-conf.yaml").strpath
        with open(conf_path, 'w') as conf_file:
            yaml.safe_dump(self.NO_ANNOTATIONS_CONFIG_DATA, conf_file)
        with pytest.raises(MissingMetadataException):
            Project(conf_path, default_compute=env_config_filepath)


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
