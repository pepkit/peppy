"""Fixtures for pytest-based units.

Constants and helper functions can also be defined here. Doing so seems to
necessitate provision of an __init__.py file in this tests/ directory
such that Python considers it a package, but if that's already in place and
test execution is not deleteriously affected, then it should be no problem.

"""

import copy
import logging
import os
import shutil
import string
import subprocess
import tempfile

import pytest
import yaml
from logmuse import init_logger
from pandas.io.parsers import EmptyDataError

from peppy import SAMPLE_NAME_COLNAME, Project
from peppy.const import METADATA_KEY, NAME_TABLE_ATTR, SAMPLE_SUBANNOTATIONS_KEY

_LOGGER = logging.getLogger("peppy")


P_CONFIG_FILENAME = "project_config.yaml"

ANNOTATIONS_FILENAME = "samples.csv"
SUBSAMPLES_FILENAME = "merge.csv"

# {basedir} lines are formatted during file write; other braced entries remain.
PROJECT_CONFIG_LINES = """{md_key}:
  {tab_key}: {main_table}
  output_dir: test
  pipeline_interfaces: pipelines
  {subtab_key}: {subtable}

derived_attributes: [{{derived_attribute_names}}]

data_sources:
  src1: "{{basedir}}/data/{{sample_name}}{{col_modifier}}.txt"
  src3: "{{basedir}}/data/{{sample_name}}.txt"
  src2: "{{basedir}}/data/{{sample_name}}-bamfile.bam"

implied_attributes:
  sample_name:
    a:
      genome: hg38
      phenome: hg72
    b:
      genome: hg38
""".format(
    md_key=METADATA_KEY,
    tab_key=NAME_TABLE_ATTR,
    main_table=ANNOTATIONS_FILENAME,
    subtable=SUBSAMPLES_FILENAME,
    subtab_key=SAMPLE_SUBANNOTATIONS_KEY,
).splitlines(
    True
)
# Will populate the corresponding string format entry in project config lines.
DERIVED_COLNAMES = [
    "file",
    "file2",
    "dcol1",
    "dcol2",
    "nonmerged_col",
    "nonmerged_col",
    "data_source",
]

# Connected with project config lines & should match; separate for clarity.
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
""".splitlines(
    True
)

# Determined by "looper_args" in pipeline interface lines.
LOOPER_ARGS_BY_PIPELINE = {"testpipeline.sh": False, "testngs.sh": True}

# These per-sample file lists pertain to the expected required inputs.
# These map to required_input_files in the pipeline interface config files.
_FILE_FILE2_BY_SAMPLE = [
    ["a.txt", "a.txt"],
    ["b3.txt", "b3.txt"],
    ["c.txt", "c.txt"],
    ["d-bamfile.bam", "d.txt"],
]
# Values expected when accessing a proj.samples[<index>].file
# file is mapped to data_source by sample annotations and subannotations.
FILE_BY_SAMPLE = [
    ["a.txt"],
    ["b1.txt", "b2.txt", "b3.txt"],
    ["c.txt"],
    ["d-bamfile.bam"],
]
PIPELINE_TO_REQD_INFILES_BY_SAMPLE = {
    "testpipeline.sh": _FILE_FILE2_BY_SAMPLE,
    "testngs.sh": FILE_BY_SAMPLE,
}

SAMPLE_ANNOTATION_LINES = """sample_name,protocol,file,file2,organism,nonmerged_col,data_source,dcol2
a,testlib,src3,src3,,src3,src3,
b,testlib,,,,src3,src3,src1
c,testlib,src3,src3,,src3,src3,
d,testngs,src2,src3,human,,src3,
""".splitlines(
    True
)

# Derived from sample annotation lines
NUM_SAMPLES = len(SAMPLE_ANNOTATION_LINES) - 1
NGS_SAMPLE_INDICES = {3}

SAMPLE_SUBANNOTATION_LINES = """sample_name,file,file2,dcol1,col_modifier
b,src1,src1,src1,1
b,src1,src1,src1,2
b,src1,src1,src1,3
""".splitlines(
    True
)

# Only sample 'b' is merged, and it's in index-1 in the annotation lines.
MERGED_SAMPLE_INDICES = {1}
# In sample subannotation lines, file2 --> src1.
# In project config's data_sources section,
# src1 --> "data/{sample_name}{col_modifier}.txt"
EXPECTED_MERGED_SAMPLE_FILES = ["b1.txt", "b2.txt", "b3.txt"]

# Discover name of attribute pointing to location of test config file based
# on the type of model instance being requested in a test fixture.
_ATTR_BY_TYPE = {Project: "project_config_file"}

COLUMNS = [SAMPLE_NAME_COLNAME, "val1", "val2", "protocol"]
PROJECT_CONFIG_DATA = {METADATA_KEY: {NAME_TABLE_ATTR: "annotations.csv"}}


def update_project_conf_data(extension):
    """ Updated Project configuration data mapping based on file extension """
    updated = copy.deepcopy(PROJECT_CONFIG_DATA)
    filename = updated[METADATA_KEY][NAME_TABLE_ATTR]
    base, _ = os.path.splitext(filename)
    updated[METADATA_KEY][NAME_TABLE_ATTR] = "{}.{}".format(base, extension)
    return updated


def pytest_addoption(parser):
    """ Facilitate command-line test behavior adjustment. """
    parser.addoption(
        "--logging-level",
        default="WARN",
        help="Project root logger level to use for tests",
    )


def pytest_generate_tests(metafunc):
    """ Centralize dynamic test case parameterization. """
    if "empty_collection" in metafunc.fixturenames:
        # Test case strives to validate expected behavior on empty container.
        collection_types = [tuple, list, set, dict]
        metafunc.parametrize(
            "empty_collection",
            argvalues=[ctype() for ctype in collection_types],
            ids=[ctype.__name__ for ctype in collection_types],
        )


@pytest.fixture(scope="session", autouse=True)
def conf_logs(request):
    """ Configure logging for the testing session. """
    level = request.config.getoption("--logging-level")
    logname = "peppy"
    init_logger(name=logname, level=level, devmode=True)
    logging.getLogger(logname).info(
        "Configured pep logger at level %s; attaching tests' logger %s",
        str(level),
        __name__,
    )
    global _LOGGER
    _LOGGER = logging.getLogger("peppy.{}".format(__name__))


@pytest.fixture(scope="function")
def sample_annotation_lines():
    """
    Return fixed collection of lines for sample annotations sheet.

    :return Iterable[str]: collection of lines for sample annotations sheet
    """
    return SAMPLE_ANNOTATION_LINES


@pytest.fixture(scope="function")
def path_empty_project(request, tmpdir):
    """ Provide path to Project config file with empty annotations. """

    # Determine how to write the data and how to name a file.
    delimiter = (
        request.getfixturevalue("delimiter")
        if "delimiter" in request.fixturenames
        else ","
    )
    extension = "csv" if delimiter == "," else "txt"

    # Update the Project configuration data.
    conf_data = update_project_conf_data(extension)

    # Write the needed files.
    anns_path = os.path.join(tmpdir.strpath, conf_data[METADATA_KEY][NAME_TABLE_ATTR])

    with open(anns_path, "w") as anns_file:
        anns_file.write(delimiter.join(COLUMNS))
    conf_path = os.path.join(tmpdir.strpath, "proj-conf.yaml")
    with open(conf_path, "w") as conf_file:
        yaml.dump(conf_data, conf_file)

    return conf_path


def interactive(
    prj_lines=PROJECT_CONFIG_LINES,
    iface_lines=PIPELINE_INTERFACE_CONFIG_LINES,
    sample_subannotation_lines=SAMPLE_SUBANNOTATION_LINES,
    annotation_lines=SAMPLE_ANNOTATION_LINES,
    project_kwargs=None,
    logger_kwargs=None,
):
    """
    Create Project instance from default or given data.

    This is intended to provide easy access to instances of fundamental pep
    object for interactive test-authorship-motivated work in an iPython
    interpreter or Notebook. Test authorship is simplified if we provide
    easy access to viable instances of these objects.

    :param Iterable[str] prj_lines: project config lines
    :param Iterable[str] iface_lines: pipeline interface config lines
    :param Iterable[str] sample_subannotation_lines: lines for a merge table file
    :param Iterable[str] annotation_lines: lines for a sample annotations file
    :param dict project_kwargs: keyword arguments for Project constructor
    :param dict logger_kwargs: keyword arguments for logging configuration
    :return Project: configured Project
    """

    # Establish logging for interactive session.
    pep_logger_kwargs = {"level": "DEBUG", "name": "peppy"}
    pep_logger_kwargs.update(logger_kwargs or {})
    init_logger(**pep_logger_kwargs)

    # TODO: don't work with tempfiles once ctors tolerate Iterable.
    dirpath = tempfile.mkdtemp()
    path_conf_file = _write_temp(prj_lines, dirpath=dirpath, fname=P_CONFIG_FILENAME)
    path_iface_file = _write_temp(
        iface_lines, dirpath=dirpath, fname="pipeline_interface.yaml"
    )
    path_sample_subannotation_file = _write_temp(
        sample_subannotation_lines, dirpath=dirpath, fname=SUBSAMPLES_FILENAME
    )
    path_sample_annotation_file = _write_temp(
        annotation_lines, dirpath=dirpath, fname=ANNOTATIONS_FILENAME
    )

    prj = Project(path_conf_file, **(project_kwargs or {}))
    for path in [
        path_conf_file,
        path_iface_file,
        path_sample_subannotation_file,
        path_sample_annotation_file,
    ]:
        os.unlink(path)
    return prj


class _DataSourceFormatMapping(dict):
    """
    Partially format text with braces. This helps since bracing is the
    mechanism that pep uses to derive columns, but it's also the
    core string formatting mechanism.
    """

    def __missing__(self, derived_attribute):
        return "{" + derived_attribute + "}"


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
    derived_attributes_replacement = _DataSourceFormatMapping(
        **{"derived_attribute_names": ", ".join(DERIVED_COLNAMES)}
    )
    filepath = os.path.join(dirpath, fname)
    data_source_formatter = string.Formatter()
    num_lines = 0
    with open(filepath, "w") as tmpf:
        for l in lines:
            if "{basedir}" in l:
                out = data_source_formatter.vformat(l, (), basedir_replacement)
            elif "{derived_attribute_names}" in l:
                out = data_source_formatter.vformat(
                    l, (), derived_attributes_replacement
                )
            else:
                out = l
            tmpf.write(out)
            num_lines += 1
    _LOGGER.debug("Wrote %d line(s) to disk: '%s'", num_lines, filepath)
    return filepath


@pytest.fixture(scope="function")
def project_config_lines():
    """ Provide safer iteration over the lines for Project config file. """
    return PROJECT_CONFIG_LINES


@pytest.fixture(scope="function")
def path_project_conf(tmpdir, project_config_lines):
    """
    Write the Project configuration data.

    :param py.path.local.LocalPath tmpdir: temporary Path fixture
    :param Iterable[str] project_config_lines: collection of lines for
        Project configuration file
    :return str: path to file with Project configuration data
    """
    with open(os.path.join(tmpdir.strpath, SUBSAMPLES_FILENAME), "w") as f:
        for l in SAMPLE_SUBANNOTATION_LINES:
            f.write(l)
    return _write_temp(project_config_lines, tmpdir.strpath, P_CONFIG_FILENAME)


@pytest.fixture(scope="function")
def proj_conf_data(path_project_conf):
    """
    Read and parse raw Project configuration data.

    :param str path_project_conf: path to file with Project configuration data
    :return Mapping: the data parsed from the configuration file written,
        a Mapping form of the raw Project config text lines
    """
    with open(path_project_conf, "r") as conf_file:
        return yaml.safe_load(conf_file)


@pytest.fixture(scope="function")
def path_sample_anns(tmpdir, sample_annotation_lines):
    """
    Write the sample annotations file and return the path to it.

    :param py.path.local.LocalPath tmpdir: temporary Path fixture
    :param Iterable[str] sample_annotation_lines: collection of lines for
        the sample annotations files
    :return str: path to the sample annotations file that was written
    """
    filepath = _write_temp(
        sample_annotation_lines, tmpdir.strpath, ANNOTATIONS_FILENAME
    )
    return filepath


@pytest.fixture(scope="function")
def p_conf_fname():
    """
    Return fixed name of project config file.

    :return str: name of project config file
    """
    return P_CONFIG_FILENAME


@pytest.fixture(scope="class")
def write_project_files(request):
    """
    Write project config data to a temporary file system location.

    :param pytest._pytest.fixtures.SubRequest request: object requesting
        this fixture
    :return str: path to the temporary file with configuration data
    """
    dirpath = tempfile.mkdtemp()
    path_conf_file = _write_temp(
        PROJECT_CONFIG_LINES, dirpath=dirpath, fname=P_CONFIG_FILENAME
    )
    path_sample_subannotation_file = _write_temp(
        SAMPLE_SUBANNOTATION_LINES, dirpath=dirpath, fname=SUBSAMPLES_FILENAME
    )
    path_sample_annotation_file = _write_temp(
        SAMPLE_ANNOTATION_LINES, dirpath=dirpath, fname=ANNOTATIONS_FILENAME
    )
    request.cls.project_config_file = path_conf_file
    request.cls.sample_subannotation_file = path_sample_subannotation_file
    request.cls.sample_annotation_file = path_sample_annotation_file
    _write_test_data_files(tempdir=dirpath)
    yield path_conf_file, path_sample_subannotation_file, path_sample_annotation_file
    shutil.rmtree(dirpath)


@pytest.fixture(scope="function")
def subannotation_filepath(tmpdir):
    """ Write sample subannotations (temp) file and return path to it. """
    return _write_temp(
        SAMPLE_SUBANNOTATION_LINES, dirpath=tmpdir.strpath, fname=SUBSAMPLES_FILENAME
    )


# Placed here (rather than near top of file) for data/use locality.
_TEST_DATA_FOLDER = "data"
_BAMFILE_PATH = os.path.join(
    os.path.dirname(__file__), _TEST_DATA_FOLDER, "d-bamfile.bam"
)
_TEST_DATA_FILE_BASENAMES = ["a", "b1", "b2", "b3", "c", "d"]
_TEST_DATA = {
    "{}.txt".format(name): "This is the content of test file {}.".format(name)
    for name in _TEST_DATA_FILE_BASENAMES
}


def _write_test_data_files(tempdir):
    """
    Write the temporary data files used by the tests.

    :param str tempdir: path to tests' primary temporary directory,
        within which temp data files may be placed directly or within
        subdirectory/ies.
    """
    data_files_subdir = os.path.join(tempdir, _TEST_DATA_FOLDER)
    os.makedirs(data_files_subdir)  # Called 1x/tempdir, so should not exist.
    subprocess.check_call(["cp", _BAMFILE_PATH, data_files_subdir])
    for fname, data in _TEST_DATA.items():
        filepath = os.path.join(tempdir, _TEST_DATA_FOLDER, fname)
        with open(filepath, "w") as testfile:
            _LOGGER.debug("Writing test data file to '%s'", filepath)
            testfile.write(data)


def request_class_attribute(req, attr):
    """ Grab `attr` attribute from class of `req`. """
    return getattr(getattr(req, "cls"), attr)


def _create(request, data_type, **kwargs):
    """
    Create instance of desired type, using file in request class.

    :param _pytest.fixtures.FixtureRequest: test case that initiated the
        fixture request that triggered this call
    :param type data_type: the data type to be created
    """
    request_class_attr_name = _ATTR_BY_TYPE[data_type]
    data_source = request_class_attribute(request, request_class_attr_name)
    _LOGGER.debug(
        "Using %s as source of data to build %s",
        data_source,
        data_type.__class__.__name__,
    )
    try:
        return data_type(data_source, **kwargs)
    except EmptyDataError:
        with open(data_source, "r") as datafile:
            _LOGGER.error("File contents:\n{}".format(datafile.readlines()))
        raise


@pytest.fixture(scope="function")
def proj(request):
    """
    Create project instance using data from file pointed to by request class.

    To use this fixture, the test case must reside within a class that
    defines a "project_config_file" attribute. This is most easily done by
    marking the class with "@pytest.mark.usefixtures('write_project_files')"

    :param pytest._pytest.fixtures.SubRequest request: test case requesting
        a project instance
    :return peppy.Project: object created by parsing
        data in file pointed to by `request` class
    """
    p = _create(request, Project)
    p.finalize_pipelines_directory()
    return p
