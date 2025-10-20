import urllib

import pytest
from peppy import Project
from peppy.eido.exceptions import EidoValidationError, PathAttrNotFoundError
from peppy.eido.validation import validate_project
from peppy.utils import load_yaml


def _check_remote_file_accessible(url):
    try:
        code = urllib.request.urlopen(url).getcode()
    except:
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
