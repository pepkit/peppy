""" Tests for handling of duplicated sample names """

import itertools
from copy import deepcopy
import pytest
import yaml
from peppy import Project
from peppy.const import *
from peppy.utils import infer_delimiter, make_unique_with_occurrence_index


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


# Partially populated Project config data; defer to tmpdir for paths.
BASE_PRJ_CFG_DAT = {
    METADATA_KEY: {},
    DERIVATIONS_DECLARATION: ["data_source"],
    DATA_SOURCES_SECTION: {"src": "{name}.txt"}
}


# Header fields for annotations sheet
ANNS_FILE_COLNAMES = [(SAMPLE_NAME_COLNAME, "data_source")]

# Data fields for each row of an annotations sheet
ANNS_FILE_ROWS_DATA = [
    [("sample" + c, "src") for c in perm]
    for perm in set(itertools.permutations(("A", "B", "A", "B")))]


def pytest_generate_tests(metafunc):
    """ Dynamic test case generation and parameterization for this module """
    if "rows_data" in metafunc.fixturenames:
        metafunc.parametrize("rows_data", ANNS_FILE_ROWS_DATA)
    if "fetch_names" in metafunc.fixturenames:
        metafunc.parametrize(
            "fetch_names", [lambda p: list(p.sample_names),
                            lambda p: list(p.sample_table[SAMPLE_NAME_COLNAME])])


def make_anns_file(fp, rows_data):
    """
    Write a sample annotations file.

    :param str fp: path to the file to write
    :param Iterable[(str, str)] rows_data: sequence of data fields to write
        as lines in a sample annotations file
    :return str: path to the sample annotations file
    """
    sep = infer_delimiter(fp)
    with open(fp, 'w') as f:
        f.write("\n".join(["{}{}{}".format(name, sep, src)
                           for name, src in ANNS_FILE_COLNAMES + rows_data]))
    return fp


@pytest.fixture
def proj_conf_data(tmpdir):
    """ Provide a test case with basic Project config data. """
    data = deepcopy(BASE_PRJ_CFG_DAT)
    data[METADATA_KEY][OUTDIR_KEY] = tmpdir.strpath
    data[METADATA_KEY][SAMPLE_ANNOTATIONS_KEY] = tmpdir.join("anns.tsv").strpath
    return data


@pytest.fixture
def prj(request, tmpdir, proj_conf_data):
    """ Provide a test case with a basic Project instance. """
    conf_file = tmpdir.join("conf.yaml").strpath
    make_anns_file(proj_conf_data[METADATA_KEY][SAMPLE_ANNOTATIONS_KEY],
                   request.getfixturevalue("rows_data"))
    with open(conf_file, 'w') as f:
        yaml.dump(proj_conf_data, f)
    return Project(conf_file)


def test_new_sample_names_are_unique(prj, rows_data, fetch_names):
    """ The primary sample names have uniqueness assurance. """
    obs = fetch_names(prj)
    assert len(set(_extract_names(rows_data))) < len(rows_data)    # Non-unique pretest
    # As many names as original non-unique, but now they're unique.
    assert len(obs) == len(rows_data)
    assert len(obs) == len(set(obs))


def test_original_sample_names_are_retained(prj, rows_data):
    """ The original, perhaps duplicated names are 'backed up.' """
    exp = _extract_names(rows_data)
    assert exp == list(prj.sample_table[SAMPLE_NAME_BACKUP_COLNAME])


def test_table_index_uses_unique_names(prj, rows_data):
    """ The table is indexed according to the unique names. """
    exp = make_unique_with_occurrence_index(_extract_names(rows_data))
    assert exp == list(prj.sample_table.index)


def _extract_names(rows_data):
    """ Assume name is first field in collection of 2-tuples. """
    return [sn for sn, _ in rows_data]
