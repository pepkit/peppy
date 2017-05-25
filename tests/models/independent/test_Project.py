""" Tests for the NGS Project model. """

import os
import pytest
import yaml
from looper.models import \
        Project, MissingMetadataException, SAMPLE_ANNOTATIONS_KEY


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



PROJECT_CONFIG_DATA = {
    "metadata": {
            SAMPLE_ANNOTATIONS_KEY: "sample-anns-filler.csv",
            "output_dir": "$HOME/sequencing/output",
            "pipelines_dir": "${CODE}/pipelines"},
    "data_sources": {"arbitrary": "placeholder/data/{filename}"},
    "genomes": {"human": "hg19", "mouse": "mm10"},
    "transcriptomes": {"human": "hg19_cdna", "mouse": "mm10_cdna"}}

DERIVED_COLUMNS_CASE_TYPES = ["implicit", "disjoint", "intersection"]



def pytest_generate_tests(metafunc):
    """ Dynamic parameterization/customization for tests in this module. """
    if metafunc.cls == DerivedColumnsTests:
        # Parameterize derived columns tests over whether the specification
        # is explicit (vs. implied), and which default column to validate.
        metafunc.parametrize(
                argnames="case_type", argvalues=DERIVED_COLUMNS_CASE_TYPES,
                ids=lambda case_type: "case_type={}".format(case_type))
        metafunc.parametrize(
                argnames="colname", argvalues=Project.DERIVED_COLUMNS_DEFAULT,
                ids=lambda colname: "column: {}".format(colname))



class ProjectRequirementsTests:
    """ Tests for a Project's set of requirements. """


    def test_lacks_sample_annotations(self, env_config_filepath, tmpdir):
        """ Lack of sample annotations precludes Project construction. """

        # Create Project config data without sample annotations.
        from copy import deepcopy
        no_annotations_config_data = deepcopy(PROJECT_CONFIG_DATA)
        del no_annotations_config_data[SAMPLE_ANNOTATIONS_KEY]

        # Write the config and assert the expected exception for Project ctor.
        conf_path = _write_project_config(
                no_annotations_config_data, dirpath=tmpdir.strpath)
        with pytest.raises(MissingMetadataException):
            Project(conf_path, default_compute=env_config_filepath)


    def test_minimal_configuration_doesnt_fail(
            self, minimal_project_conf_path, env_config_filepath):
        """ Project ctor requires minimal config and default environment. """
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



@pytest.mark.skip("Not implemented")
class DerivedColumnsTests:
    """ Tests for the behavior of Project's derived_columns attribute. """


    def test_default_derived_columns_always_present(
            self, case_type, colname, env_config_filepath, tmpdir):
        """ Explicit or implicit, default derived columns are always there. """
        if case_type == "implicit":
            config_data = PROJECT_CONFIG_DATA
        elif case_type == "disjoint":
            pass
        elif case_type == "intersection":
            pass
        else:
            raise ValueError(
                    "Unexpected derived_columns case type: '{}' (known={})".
                    format(case_type, DERIVED_COLUMNS_CASE_TYPES))
        conf_file_path = _write_project_config(
                config_data, dirpath=tmpdir.strpath)
        project = Project(conf_file_path, default_compute=env_config_filepath)


    def test_default_derived_columns_not_duplicated(self, case_type, colname):
        """ Default derived columns are not added if already present. """
        pass



def _write_project_config(config_data, dirpath, filename="proj-conf.yaml"):
    """
    Write the configuration file for a Project.
    
    :param dict config_data: configuration data to write to disk
    :param str dirpath: path to folder in which to place file
    :param str filename: name for config file
    :return str: path to config file written
    """
    conf_file_path = os.path.join(dirpath, filename)
    with open(conf_file_path, 'w') as conf_file:
        yaml.safe_dump(config_data, conf_file)
    return conf_file_path
