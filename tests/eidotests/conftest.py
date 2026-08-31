import os

import pytest

from peppy import Project


@pytest.fixture
def data_path():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "eidodata"
    )


@pytest.fixture
def schemas_path(data_path):
    return os.path.join(data_path, "schemas")


@pytest.fixture
def peps_path(data_path):
    return os.path.join(data_path, "peps")


@pytest.fixture
def project_file_path(peps_path):
    return os.path.join(peps_path, "test_pep", "test_cfg.yaml")


@pytest.fixture
def project_table_path(peps_path):
    return os.path.join(peps_path, "test_pep", "test_sample_table.csv")


@pytest.fixture
def project_object(project_file_path):
    return Project(project_file_path)


@pytest.fixture
def schema_file_path(schemas_path):
    return os.path.join(schemas_path, "test_schema.yaml")


@pytest.fixture
def schema_samples_file_path(schemas_path):
    return os.path.join(schemas_path, "test_schema_samples.yaml")


@pytest.fixture
def schema_invalid_file_path(schemas_path):
    return os.path.join(schemas_path, "test_schema_invalid.yaml")


@pytest.fixture
def schema_sample_invalid_file_path(schemas_path):
    return os.path.join(schemas_path, "test_schema_sample_invalid.yaml")


@pytest.fixture
def schema_imports_file_path(schemas_path):
    return os.path.join(schemas_path, "test_schema_imports.yaml")


@pytest.fixture
def schema_rel_path_imports_file_path(schemas_path):
    return os.path.join(schemas_path, "test_schema_imports_rel_path.yaml")


@pytest.fixture
def taxprofiler_project_path(peps_path):
    return os.path.join(peps_path, "multiline_output", "config.yaml")


@pytest.fixture
def taxprofiler_project(taxprofiler_project_path):
    return Project(taxprofiler_project_path)


@pytest.fixture
def path_to_taxprofiler_csv_multiline_output(peps_path):
    return os.path.join(peps_path, "multiline_output", "multiline_output.csv")


@pytest.fixture
def path_pep_with_fasta_column(peps_path):
    return os.path.join(peps_path, "pep_with_fasta_column", "config.yaml")


@pytest.fixture
def project_pep_with_fasta_column(path_pep_with_fasta_column):
    return Project(path_pep_with_fasta_column, sample_table_index="sample")


@pytest.fixture
def output_pep_with_fasta_column(path_pep_with_fasta_column):
    with open(
        os.path.join(os.path.dirname(path_pep_with_fasta_column), "output.csv")
    ) as f:
        return f.read()


@pytest.fixture
def taxprofiler_csv_multiline_output(path_to_taxprofiler_csv_multiline_output):
    with open(path_to_taxprofiler_csv_multiline_output, "r") as file:
        data = file.read()
    return data
    # This is broken unless I add na_filter=False. But it's a bad idea anyway, since
    # we're just using this for string comparison anyway...
    # return pd.read_csv(
    #     path_to_taxprofiler_csv_multiline_output, na_filter=False
    # ).to_csv(path_or_buf=None, index=None)


@pytest.fixture
def path_pep_for_schema_with_rel_path(peps_path):
    return os.path.join(peps_path, "pep_schema_rel_path", "config.yaml")


@pytest.fixture
def path_pep_nextflow_taxprofiler(peps_path):
    return os.path.join(peps_path, "pep_nextflow_taxprofiler", "config.yaml")


@pytest.fixture
def project_pep_nextflow_taxprofiler(path_pep_nextflow_taxprofiler):
    return Project(path_pep_nextflow_taxprofiler, sample_table_index="sample")


@pytest.fixture
def output_pep_nextflow_taxprofiler(path_pep_nextflow_taxprofiler):
    with open(
        os.path.join(os.path.dirname(path_pep_nextflow_taxprofiler), "output.csv")
    ) as f:
        return f.read()


@pytest.fixture
def save_result_mock(mocker):
    return mocker.patch("peppy.eido.conversion.save_result")


@pytest.fixture
def test_file_existing_schema(schemas_path):
    return os.path.join(schemas_path, "schema_test_file_exist.yaml")


@pytest.fixture
def test_file_existing_pep(peps_path):
    return os.path.join(peps_path, "test_file_existing", "project_config.yaml")


@pytest.fixture
def test_schema_value_check(schemas_path):
    return os.path.join(schemas_path, "value_check_schema.yaml")


@pytest.fixture
def test_file_value_check(peps_path):
    return os.path.join(peps_path, "value_check_pep", "project_config.yaml")


@pytest.fixture
def test_multiple_subs(peps_path):
    return os.path.join(peps_path, "multiple_subsamples", "project_config.yaml")
