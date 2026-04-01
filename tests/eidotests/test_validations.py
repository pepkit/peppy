import urllib

import pytest

from peppy import Project
from peppy.eido.exceptions import EidoValidationError, PathAttrNotFoundError
from peppy.eido.validation import (
    validate_config,
    validate_input_files,
    validate_original_samples,
    validate_project,
    validate_sample,
)
from peppy.utils import load_yaml


def _check_remote_file_accessible(url):
    try:
        code = urllib.request.urlopen(url).getcode()
    except (urllib.error.URLError, OSError):
        pytest.skip(f"Remote file not found: {url}")
    else:
        if code != 200:
            pytest.skip(f"Return code: {code}. Remote file not found: {url}")


class TestProjectValidation:
    def test_validate_works(self, project_object, schema_file_path):
        validate_project(project=project_object, schema=schema_file_path)

    def test_validate_detects_invalid(self, project_object, schema_invalid_file_path):
        with pytest.raises(EidoValidationError):
            validate_project(project=project_object, schema=schema_invalid_file_path)

    def test_validate_detects_invalid_imports(
        self, project_object, schema_imports_file_path
    ):
        with pytest.raises(EidoValidationError):
            validate_project(project=project_object, schema=schema_imports_file_path)

    def test_validate_imports_with_rel_path(
        self, path_pep_for_schema_with_rel_path, schema_rel_path_imports_file_path
    ):
        pep_project = Project(path_pep_for_schema_with_rel_path)
        validate_project(project=pep_project, schema=schema_rel_path_imports_file_path)

    def test_validate_converts_samples_to_private_attr(
        self, project_object, schema_samples_file_path
    ):
        """
        In peppy.Project the list of peppy.Sample objects is
        accessible via _samples attr.
        To make the schema creation more accessible for eido users
        samples->_samples key conversion has been implemented
        """
        validate_project(project=project_object, schema=schema_samples_file_path)

    def test_validate_works_with_dict_schema(self, project_object, schema_file_path):
        validate_project(project=project_object, schema=load_yaml(schema_file_path))

    @pytest.mark.parametrize("schema_arg", [1, None, [1, 2, 3]])
    def test_validate_raises_error_for_incorrect_schema_type(
        self, project_object, schema_arg
    ):
        with pytest.raises(TypeError):
            validate_project(project=project_object, schema=schema_arg)


class TestSampleValidation:
    @pytest.mark.parametrize("sample_name", [0, 1, "GSM1558746"])
    def test_validate_works(
        self, project_object, sample_name, schema_samples_file_path
    ):
        validate_sample(
            project=project_object,
            sample_name=sample_name,
            schema=schema_samples_file_path,
        )

    @pytest.mark.parametrize("sample_name", [22, "bogus_sample_name"])
    def test_validate_raises_error_for_incorrect_sample_name(
        self, project_object, sample_name, schema_samples_file_path
    ):
        with pytest.raises((ValueError, IndexError)):
            validate_sample(
                project=project_object,
                sample_name=sample_name,
                schema=schema_samples_file_path,
            )

    @pytest.mark.parametrize("sample_name", [0, 1, "GSM1558746"])
    def test_validate_detects_invalid(
        self, project_object, sample_name, schema_sample_invalid_file_path
    ):
        with pytest.raises(EidoValidationError):
            validate_sample(
                project=project_object,
                sample_name=sample_name,
                schema=schema_sample_invalid_file_path,
            )

    def test_original_sample(self, project_table_path, schema_samples_file_path):
        validate_original_samples(project_table_path, schema_samples_file_path)


class TestConfigValidation:
    def test_validate_succeeds_on_invalid_sample(
        self, project_object, schema_sample_invalid_file_path
    ):
        validate_config(project=project_object, schema=schema_sample_invalid_file_path)

    def test_validate_on_yaml_dict(
        self, project_file_path, schema_sample_invalid_file_path
    ):
        validate_config(
            project=project_file_path, schema=schema_sample_invalid_file_path
        )


class TestRemoteValidation:
    @pytest.mark.parametrize("schema_url", ["http://schema.databio.org/pep/2.0.0.yaml"])
    def test_validate_works_with_remote_schemas(self, project_object, schema_url):
        _check_remote_file_accessible(schema_url)
        validate_project(project=project_object, schema=schema_url)
        validate_config(project=project_object, schema=schema_url)
        validate_sample(project=project_object, schema=schema_url, sample_name=0)


class TestImportsValidation:
    def test_validate(self, project_object, schema_file_path):
        validate_project(project=project_object, schema=schema_file_path)


class TestProjectWithoutConfigValidation:
    @pytest.mark.parametrize(
        "remote_pep_cfg",
        [
            "https://raw.githubusercontent.com/pepkit/example_peps/master/example_basic/sample_table.csv"
        ],
    )
    def test_validate_works(self, schema_file_path, remote_pep_cfg):
        _check_remote_file_accessible(remote_pep_cfg)
        validate_project(
            project=Project(
                remote_pep_cfg
            ),  # create Project object from a remote sample table
            schema=schema_file_path,
        )

    @pytest.mark.parametrize(
        "remote_pep_cfg",
        [
            "https://raw.githubusercontent.com/pepkit/example_peps/master/example_basic/sample_table.csv"
        ],
    )
    def test_validate_detects_invalid(self, schema_invalid_file_path, remote_pep_cfg):
        _check_remote_file_accessible(remote_pep_cfg)
        with pytest.raises(EidoValidationError):
            validate_project(
                project=Project(remote_pep_cfg), schema=schema_invalid_file_path
            )

    def test_validate_file_existence(
        self, test_file_existing_pep, test_file_existing_schema
    ):
        schema_path = test_file_existing_schema
        prj = Project(test_file_existing_pep)
        with pytest.raises(PathAttrNotFoundError):
            validate_input_files(prj, schema_path)

    def test_validation_values(self, test_schema_value_check, test_file_value_check):
        schema_path = test_schema_value_check
        prj = Project(test_file_value_check)
        with pytest.raises(EidoValidationError):
            validate_project(project=prj, schema=schema_path)
