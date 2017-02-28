"""Fixtures for pytest-based units.

Constants and helper functions can also be defined here. Doing so seems to
necessitate provision of an __init__.py file in this tests/ directory
such that Python considers it a package, but if that's already in place and
test execution is not deleteriously affected, then it should be no problem.

"""

import logging
import os
import shutil
import string
import subprocess
import tempfile

from pandas.io.parsers import EmptyDataError
import pytest

from looper import setup_looper_logger
from looper.models import PipelineInterface, Project


# TODO: needed for interactive mode, but may crush cmdl option for setup.
_LOGGER = logging.getLogger("looper")


# {basedir} lines are formatted during file write; other braced entries remain.
PROJECT_CONFIG_LINES = """metadata:
  sample_annotation: samples.csv
  output_dir: test
  pipelines_dir: pipelines
  merge_table: merge.csv

derived_columns: [{derived_column_names}]

data_sources:
  src1: "{basedir}/data/{sample_name}{col_modifier}.txt"
  src3: "{basedir}/data/{sample_name}.txt"
  src2: "{basedir}/data/{sample_name}-bamfile.bam"
""".splitlines(True)
# Will populate the corresponding string format entry in project config lines.
DERIVED_COLNAMES = ["file", "file2", "dcol1", "dcol2",
                    "nonmerged_col", "nonmerged_col", "data_source"]

# Connected with project config lines & should match; separate for clarity.
ANNOTATIONS_FILENAME = "samples.csv"
MERGE_TABLE_FILENAME = "merge.csv"
SRC1_TEMPLATE = "data/{sample_name}{col_modifier}.txt"
SRC2_TEMPLATE = "data/{sample_name}-bamfile.bam"
SRC3_TEMPLATE = "data/{sample_name}.txt"


PIPELINE_INTERFACE_CONFIG_LINES = """testpipeline.sh:
  name: test_pipeline  # Name used by pypiper so looper can find the logs
  looper_args: False
  arguments:
    "--input": file
  optional_arguments:
    "--sample-name": sample_name
    "--dcol1": dcol1
  required_input_files: [file, file2]
  resources:
    default:
      file_size: "0"
      cores: "8"
      mem: "32000"
      time: "2-00:00:00"
      partition: "longq"
testngs.sh:
  name: test_ngs_pipeline  # Name used by pypiper so looper can find the logs
  looper_args: True
  arguments:
    "--input": file
  optional_arguments:
    "--sample-name": sample_name
    "--genome": genome
    "--single-or-paired": read_type
    "--dcol1": dcol1
  required_input_files: [file]
  all_input_files: [file, read1]
  ngs_input_files: [file]
  resources:
    default:
      file_size: "0"
      cores: "8"
      mem: "32000"
      time: "2-00:00:00"
      partition: "longq"
""".splitlines(True)

# Determined by "looper_args" in pipeline interface lines.
LOOPER_ARGS_BY_PIPELINE = {
    "testpipeline.sh": False,
    "testngs.sh": True
}

# These per-sample file lists pertain to the expected required inputs.
# These map to required_input_files in the pipeline interface config files.
_FILE_FILE2_BY_SAMPLE = [
        ["a.txt", "a.txt"],
        ["b3.txt", "b3.txt"],
        ["c.txt", "c.txt"],
        ["d-bamfile.bam", "d.txt"]
]
# Values expected when accessing a proj.samples[<index>].file
# file is mapped to data_source by sample annotations and merge_table.
FILE_BY_SAMPLE = [
        ["a.txt"],
        ["b1.txt", "b2.txt", "b3.txt"],
        ["c.txt"],
        ["d-bamfile.bam"]
]
PIPELINE_TO_REQD_INFILES_BY_SAMPLE = {
    "testpipeline.sh": _FILE_FILE2_BY_SAMPLE,
    "testngs.sh": FILE_BY_SAMPLE
}

SAMPLE_ANNOTATION_LINES = """sample_name,library,file,file2,organism,nonmerged_col,data_source,dcol2
a,testlib,src3,src3,,src3,src3,
b,testlib,,,,src3,src3,src1
c,testlib,src3,src3,,src3,src3,
d,testngs,src2,src3,human,,src3,
""".splitlines(True)

# Derived from sample annotation lines
NUM_SAMPLES = len(SAMPLE_ANNOTATION_LINES) - 1
NGS_SAMPLE_INDICES = {3}

MERGE_TABLE_LINES = """sample_name,file,file2,dcol1,col_modifier
b,src1,src1,src1,1
b,src1,src1,src1,2
b,src1,src1,src1,3
""".splitlines(True)

# Only sample 'b' is merged, and it's in index-1 in the annotation lines.
MERGED_SAMPLE_INDICES = {1}
# In merge_table lines, file2 --> src1.
# In project config's data_sources section,
# src1 --> "data/{sample_name}{col_modifier}.txt"
EXPECTED_MERGED_SAMPLE_FILES = ["b1.txt", "b2.txt", "b3.txt"]


# Discover name of attribute pointing to location of test config file based
# on the type of model instance being requested in a test fixture.
_ATTR_BY_TYPE = {
    Project: "project_config_file",
    PipelineInterface: "pipe_iface_config_file"
}


# TODO: split models conftest stuff into its own subdirectory.
# Provide some basic atomic-type data for models tests.
_BASE_KEYS = ("epigenomics", "H3K", "ac", "EWS", "FLI1")
_BASE_VALUES = \
    ("topic", "marker", "acetylation", "RNA binding protein", "FLI1")
_SEASON_HIERARCHY = {
    "spring": {"February": 28, "March": 31, "April": 30, "May": 31},
    "summer": {"June": 30, "July": 31, "August": 31},
    "fall": {"September": 30, "October": 31, "November": 30},
    "winter": {"December": 31, "January": 31}
}
COMPARISON_FUNCTIONS = ["__eq__", "__ne__", "__len__",
                        "keys", "values", "items"]


def pytest_addoption(parser):
    parser.addoption("--logging-level",
                     default="WARN",
                     help="Project root logger level to use for tests")


@pytest.fixture(scope="session", autouse=True)
def conf_logs(request):
    level = request.config.getoption("--logging-level")
    setup_looper_logger(level=level, devmode=True)
    logging.getLogger("looper").info(
        "Configured looper logger at level %s; attaching tests' logger %s",
        str(level), __name__)
    global _LOGGER
    _LOGGER = logging.getLogger(__name__)



def interactive(prj_lines=PROJECT_CONFIG_LINES,
                iface_lines=PIPELINE_INTERFACE_CONFIG_LINES,
                merge_table_lines = MERGE_TABLE_LINES,
                sample_annotation_lines=SAMPLE_ANNOTATION_LINES,
                project_kwargs=None):
    """
    Create Project and PipelineInterface instances from default or given data.

    This is intended to provide easy access to instances of fundamental looper
    object for interactive test-authorship-motivated work in an iPython
    interpreter or Notebook. Test authorship is simplified if we provide
    easy access to viable instances of these objects.

    :param collections.Iterable[str] prj_lines: project config lines
    :param collections.Iterable[str] iface_lines: pipeline interface
        config lines
    :param collections.Iterable[str] merge_table_lines: lines for a merge
        table file
    :param collections.Iterable[str] sample_annotation_lines: lines for a
        sample annotations file
    :param dict project_kwargs: keyword arguments for Project constructor
    :return Project, PipelineInterface: one Project and one PipelineInterface,
    """
    # TODO: don't work with tempfiles once ctors tolerate Iterable.
    dirpath = tempfile.mkdtemp()
    path_conf_file = _write_temp(
        prj_lines,
        dirpath=dirpath, fname="project_config.yaml")
    path_iface_file = _write_temp(
        iface_lines,
        dirpath=dirpath, fname="pipeline_interface.yaml")
    path_merge_table_file = _write_temp(
        merge_table_lines,
        dirpath=dirpath, fname=MERGE_TABLE_FILENAME
    )
    path_sample_annotation_file = _write_temp(
        sample_annotation_lines,
        dirpath=dirpath, fname=ANNOTATIONS_FILENAME
    )

    prj = Project(path_conf_file, **(project_kwargs or {}))
    iface = PipelineInterface(path_iface_file)
    for path in [path_conf_file, path_iface_file,
                 path_merge_table_file, path_sample_annotation_file]:
        os.unlink(path)
    return prj, iface



class _DataSourceFormatMapping(dict):
    """
    Partially format text with braces. This helps since bracing is the
    mechanism that `looper` uses to derive columns, but it's also the
    core string formatting mechanism.
    """
    def __missing__(self, derived_column):
        return "{" + derived_column + "}"


def _write_temp(lines, dirpath, fname):
    """
    Note that delete flag is a required argument since it's potentially
    dangerous. When writing to a directory path generated by pytest tmpdir
    fixture, the file will be deleted after the requesting class/function/etc.
    completes execution anyway, but otherwise failure to set the delete flag
    could leave lingering files. Perhaps that is desired and intended, but
    in general such responsibility should be delegated to the caller.

    :param collections.abc.Iterable(str) lines: sequence of
        lines to write to file
    :param str dirpath: path to directory in which to place the tempfile
    :param str fname: name for file in `dirpath` to which to write `lines`
    :return str: full path to written file
    """
    basedir_replacement = _DataSourceFormatMapping(basedir=dirpath)
    derived_columns_replacement = _DataSourceFormatMapping(
            **{"derived_column_names": ", ".join(DERIVED_COLNAMES)}
    )
    filepath = os.path.join(dirpath, fname)
    _LOGGER.debug("Writing %d lines to file '%s'", len(lines), filepath)
    data_source_formatter = string.Formatter()
    with open(filepath, 'w') as tmpf:
        for l in lines:
            if "{basedir}" in l:
                l = data_source_formatter.vformat(
                    l, (), basedir_replacement)
            elif "{derived_column_names}" in l:
                l = data_source_formatter.vformat(
                    l, (), derived_columns_replacement)
            tmpf.write(l)
        return tmpf.name


@pytest.fixture(scope="class")
def write_project_files(request):
    """
    Write project config data to a temporary file system location.

    :param pytest._pytest.fixtures.SubRequest request: object requesting
        this fixture
    :return str: path to the temporary file with configuration data
    """
    dirpath = tempfile.mkdtemp()
    path_conf_file = _write_temp(PROJECT_CONFIG_LINES,
                                 dirpath=dirpath, fname="project_config.yaml")
    path_merge_table_file = _write_temp(
            MERGE_TABLE_LINES,
            dirpath=dirpath, fname=MERGE_TABLE_FILENAME
    )
    path_sample_annotation_file = _write_temp(
            SAMPLE_ANNOTATION_LINES,
            dirpath=dirpath, fname=ANNOTATIONS_FILENAME
    )
    request.cls.project_config_file = path_conf_file
    request.cls.merge_table_file = path_merge_table_file
    request.cls.sample_annotation_file = path_sample_annotation_file
    _write_test_data_files(tempdir=dirpath)
    yield path_conf_file, path_merge_table_file, path_sample_annotation_file
    shutil.rmtree(dirpath)


# Placed here for data/use locality.
_TEST_DATA_FOLDER = "data"
_BAMFILE_PATH = os.path.join(os.path.dirname(__file__),
                             _TEST_DATA_FOLDER, "d-bamfile.bam")
_TEST_DATA_FILE_BASENAMES = ["a", "b1", "b2", "b3", "c", "d"]
_TEST_DATA = {"{}.txt".format(name):
              "This is the content of test file {}.".format(name)
              for name in _TEST_DATA_FILE_BASENAMES}


def _write_test_data_files(tempdir):
    """
    Write the temporary data files used by the tests.

    :param str tempdir: path to tests' primary temporary directory,
        within which temp data files may be placed directly or within
        subdirectory/ies.
    """
    data_files_subdir = os.path.join(tempdir, _TEST_DATA_FOLDER)
    os.makedirs(data_files_subdir)    # Called 1x/tempdir, so should not exist.
    subprocess.check_call(["cp", _BAMFILE_PATH, data_files_subdir])
    for fname, data in _TEST_DATA.items():
        filepath = os.path.join(tempdir, _TEST_DATA_FOLDER, fname)
        with open(filepath, 'w') as testfile:
            _LOGGER.debug("Writing test data file to '%s'", filepath)
            testfile.write(data)


@pytest.fixture(scope="class")
def pipe_iface_config_file(request):
    """
    Write pipeline interface config data to a temporary file system location.

    :param pytest._pytest.fixtures.SubRequest request: object requesting
        this fixture
    :return str: path to the temporary file with configuration data
    """
    dirpath = tempfile.mkdtemp()
    path_conf_file = _write_temp(
            PIPELINE_INTERFACE_CONFIG_LINES,
            dirpath=dirpath, fname="pipeline_interface.yaml"
    )
    request.cls.pipe_iface_config_file = path_conf_file
    yield path_conf_file
    shutil.rmtree(dirpath)


def _req_cls_att(req, attr):
    """ Grab `attr` attribute from class of `req`. """
    return getattr(getattr(req, "cls"), attr)


def _create(request, wanted):
    """
    Create instance of `wanted` type, using file in `request` class.

    :param _pytest.fixtures.FixtureRequest: test case that initiated the
        fixture request that triggered this call
    :param type wanted: the data type to be created
    """
    data_source = _req_cls_att(request, _ATTR_BY_TYPE[wanted])
    _LOGGER.debug("Using %s as source of data to build %s",
                  data_source, wanted.__class__.__name__)
    try:
        return wanted(data_source)
    except EmptyDataError:
        with open(data_source, 'r') as datafile:
            _LOGGER.error("File contents:\n{}".format(datafile.readlines()))
        raise


@pytest.fixture(scope="function")
def proj(request):
    """
    Create `looper` `Project` instance using data from file
    pointed to by class of `request`.

    :param pytest._pytest.fixtures.SubRequest request: test case requesting
        a project instance
    :return looper.models.Project: object created by parsing
        data in file pointed to by `request` class
    """
    return _create(request, Project)


@pytest.fixture(scope="function")
def pipe_iface(request):
    """
    Create `looper` `PipelineInterface` instance using data from file
    pointed to by class of `request`.

    :param pytest._pytest.fixtures.SubRequest request: test case requesting
        a project instance
    :return looper.models.PipelineInterface: object created by parsing
        data in file pointed to by `request` class
    """
    return _create(request, PipelineInterface)



def basic_entries():
    for k, v in zip(_BASE_KEYS, _BASE_VALUES):
        yield k, v


def nested_entries():
    for k, v in _SEASON_HIERARCHY.items():
        yield k, v



def pytest_generate_tests(metafunc):
    """ Centralize dynamic test case parameterization. """
    if "empty_collection" in metafunc.fixturenames:
        # Test case strives to validate expected behavior on empty container.
        collection_types = [tuple, list, set, dict]
        metafunc.parametrize(
                "empty_collection",
                argvalues=[ctype() for ctype in collection_types],
                ids=[ctype.__name__ for ctype in collection_types])
