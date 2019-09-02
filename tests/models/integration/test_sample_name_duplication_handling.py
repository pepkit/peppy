""" Tests for handling of duplicated sample names """

import pytest
import yaml
import collections
from copy import deepcopy
from peppy import Project
from peppy.const import *
from peppy.utils import infer_delimiter


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


SRC_TEMPLATE = "{sample_name}.txt"
ORGANISM_COLNAME = "organism"
TEST_ORG_COLLECTION = (["frog"]*3) + (["dog"]*4) + ["sparrow"]

BASE_PRJ_CFG_DAT = {
    METADATA_KEY: {},
    DERIVATIONS_DECLARATION: [SAMPLE_NAME_COLNAME, "data_source"],
    DATA_SOURCES_SECTION: {
                            "sn": "{" + ORGANISM_COLNAME + "}",
                            "src": SRC_TEMPLATE,
                           }
}

# Header fields for annotations sheet
ANNS_FILE_COLNAMES = [[SAMPLE_NAME_COLNAME, "data_source", ORGANISM_COLNAME]]

# Data fields for each row of an annotations sheet
ANNS_FILE_ROWS_DATA = [["sn", "src", org] for org in TEST_ORG_COLLECTION]


def pytest_generate_tests(metafunc):
    """ Dynamic test case generation and parameterization for this module """
    if "rows_data" in metafunc.fixturenames:
        metafunc.parametrize("rows_data", [ANNS_FILE_ROWS_DATA])
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
        for i in ANNS_FILE_COLNAMES + rows_data:
            f.write("{}{}{}{}{}{}".format(i[0], sep, i[1], sep, i[2], "\n"))
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


def test_derived_names_can_be_used_for_further_derivation(prj, rows_data):
    """ Sample names that are created the uniqueness enforcement mechanism can be
    used for other attributes derivation. """
    for s in prj.samples:
        assert getattr(s, ORGANISM_COLNAME) != SRC_TEMPLATE


def test_new_sample_names_are_unique(prj, rows_data):
    """ Number of unique sample names is always equal the total samples count. """
    assert len(prj.samples) == len(set([s.sample_name for s in prj.samples]))


def test_original_sample_names_are_retained(prj, rows_data):
    """ The original names are 'backed up' in duplicated samples """
    backup_attrs = [hasattr(s, SAMPLE_NAME_BACKUP_COLNAME) for s in prj.samples]
    unique_orgs = [item for item, count in collections.Counter(TEST_ORG_COLLECTION).items() if count == 1]
    assert len(prj.samples) - len(unique_orgs) == sum(backup_attrs)
    assert any(backup_attrs)
    assert not all(backup_attrs)

