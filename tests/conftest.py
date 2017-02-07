"""Fixtures for pytest-based units.

Constants and helper functions can also be defined here. Doing so seems to
necessitate provision of an __init__.py file in this tests/ directory
such that Python considers it a package, but if that's already in place and
test execution is not deleteriously affected, then it should be no problem.

"""

import tempfile
import pytest
from looper.models import PipelineInterface, Project

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


CONFIG_LINES = """metadata:
  sample_annotation: samples.csv
  output_dir: test
  pipelines_dir: pipelines
  merge_table: merge.csv

derived_columns: [file, file2, dcol1, dcol2, nonmerged_col, nonmerged_col, data_source]

data_sources:
  src1: "tests/data/{sample_name}{col_modifier}.txt"
  src3: "tests/data/{sample_name}.txt"
  src2: "tests/data/{sample_name}-bamfile.bam"
""".splitlines(True)


@pytest.fixture(scope="class")
def config_file(tmpdir):
    """
    Write configuration data to a temporary file system location.
    The file will be used by one or more tests, and then at the conclusion
    of the scope for which it's defined (likely class, but per)

    :param py.path.local tmpdir: path to temporary directory,
        provided by invocation of the builtin pytest fixture
    :return str: path to the temporary file with configuration data
    """
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False,
                                     dir=str(tmpdir)) as f:
        for conf_line in CONFIG_LINES:
            f.write(conf_line)
        return f.name


@pytest.fixture(scope="function")
def project(request):
    return Project(request.cls.config_file)


@pytest.fixture(scope="function")
def pipe_iface(request):
    return PipelineInterface(request.cls.config_file)
