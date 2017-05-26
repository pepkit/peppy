""" Tests for the NGS Project model. """

import copy
import os
import mock
import pytest
import yaml
from looper.models import \
        Project, MissingMetadataException, SAMPLE_ANNOTATIONS_KEY


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



@pytest.fixture(scope="function")
def project_config_data():
    return {
        "metadata": {
            SAMPLE_ANNOTATIONS_KEY: "sample-anns-filler.csv",
            "output_dir": "$HOME/sequencing/output",
            "pipelines_dir": "${CODE}/pipelines"},
        "data_sources": {"arbitrary": "placeholder/data/{filename}"},
        "genomes": {"human": "hg19", "mouse": "mm10"},
        "transcriptomes": {"human": "hg19_cdna", "mouse": "mm10_cdna"}}



def pytest_generate_tests(metafunc):
    """ Dynamic parameterization/customization for tests in this module. """
    if metafunc.cls == DerivedColumnsTests:
        # Parameterize derived columns tests over whether the specification
        # is explicit (vs. implied), and which default column to validate.
        metafunc.parametrize(
                argnames="case_type",
                argvalues=DerivedColumnsTests.DERIVED_COLUMNS_CASE_TYPES,
                ids=lambda case_type: "case_type={}".format(case_type))



class ProjectRequirementsTests:
    """ Tests for a Project's set of requirements. """


    def test_lacks_sample_annotations(
            self, project_config_data, env_config_filepath, tmpdir):
        """ Lack of sample annotations precludes Project construction. """

        # Remove sample annotations KV pair from config data for this test.
        del project_config_data["metadata"][SAMPLE_ANNOTATIONS_KEY]

        # Write the config and assert the expected exception for Project ctor.
        conf_path = _write_project_config(
            project_config_data, dirpath=tmpdir.strpath)
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



class DerivedColumnsTests:
    """ Tests for the behavior of Project's derived_columns attribute. """

    ADDITIONAL_DERIVED_COLUMNS = ["arbitrary1", "filler2", "placeholder3"]
    DERIVED_COLUMNS_CASE_TYPES = ["implicit", "disjoint", "intersection"]


    def create_project(
            self, project_config_data, default_env_path, case_type, dirpath):
        """
        For a test case, determine expectations and create Project instance.
        
        :param dict project_config_data: the actual data to write to the 
            Project configuration file
        :param str default_env_path: path to the default environment config 
            file to pass to Project constructor
        :param str case_type: type of test case to execute; this determines 
            how to specify the derived columns in the config file
        :param str dirpath: path in which to write config file
        :return (Iterable[str], Project): collection of names of derived 
            columns to expect, along with Project instance with which to test
        """

        # Ensure valid parameterization.
        if case_type not in self.DERIVED_COLUMNS_CASE_TYPES:
            raise ValueError(
                "Unexpected derived_columns case type: '{}' (known={})".
                format(case_type, self.DERIVED_COLUMNS_CASE_TYPES))

        # Parameterization specifies expectation and explicit specification.
        expected_derived_columns = copy.copy(Project.DERIVED_COLUMNS_DEFAULT)
        if case_type == "implicit":
            # Negative control; ensure config data lacks derived columns.
            assert "derived_columns" not in project_config_data
        else:
            explicit_derived_columns = \
                    copy.copy(self.ADDITIONAL_DERIVED_COLUMNS)
            expected_derived_columns.extend(self.ADDITIONAL_DERIVED_COLUMNS)
            # Determine explicit inclusion of default derived columns.
            if case_type == "intersection":
                explicit_derived_columns.extend(
                        Project.DERIVED_COLUMNS_DEFAULT)
            project_config_data["derived_columns"] = explicit_derived_columns

        # Write the config and build the Project.
        conf_file_path = _write_project_config(
                project_config_data, dirpath=dirpath)
        with mock.patch("looper.models.Project.add_sample_sheet"):
            project = Project(conf_file_path, default_compute=default_env_path)
        return expected_derived_columns, project



    def test_default_derived_columns_always_present(self,
            env_config_filepath, project_config_data, case_type, tmpdir):
        """ Explicit or implicit, default derived columns are always there. """

        expected_derived_columns, project = self.create_project(
                project_config_data=project_config_data,
                default_env_path=env_config_filepath,
                case_type=case_type, dirpath=tmpdir.strpath)

        # Rough approximation of order-agnostic validation of
        # presence and number agreement for all elements.
        assert len(expected_derived_columns) == len(project.derived_columns)
        assert set(expected_derived_columns) == set(project.derived_columns)


    def test_default_derived_columns_not_duplicated(self,
            env_config_filepath, project_config_data, case_type, tmpdir):
        """ Default derived columns are not added if already present. """
        from collections import Counter
        _, project = self.create_project(
                project_config_data=project_config_data,
                default_env_path=env_config_filepath,
                case_type=case_type, dirpath=tmpdir.strpath)
        num_occ_by_derived_column = Counter(project.derived_columns)
        for default_derived_colname in Project.DERIVED_COLUMNS_DEFAULT:
            assert 1 == num_occ_by_derived_column[default_derived_colname]



class PipelineArgumentsTests:
    """ Tests for Project config's pipeline_arguments section. """


    def test_no_pipeline_arguments(self):
        """ Case in which config specifies no additional pipeline args. """
        pass


    def test_pipeline_args_flags(self):
        pass


    def test_pipeline_args_flags_and_options(self):
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
