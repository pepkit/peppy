""" Tests regarding Project data tables """

import os
import pytest
import yaml
from peppy import Project
from peppy.const import *
from tests.conftest import SAMPLE_ANNOTATION_LINES, SAMPLE_SUBANNOTATION_LINES

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


ANNS_FIXTURE_PREFIX = "anns"
SUBS_FIXTURE_PREFIX = "subs"
FILE_FIXTURE_SUFFIX = "_file"
DATA_FIXTURE_SUFFIX = "_data"


def _get_comma_tab(lines):
    """ Get parallel collections of comma- and tab-delimiter lines """
    return [l.replace("\t", ",") for l in lines], \
           [l.replace(",", "\t") for l in lines]


COMMA_ANNS_DATA, TAB_ANNS_DATA = _get_comma_tab(SAMPLE_ANNOTATION_LINES)
COMMA_SUBANNS_DATA, TAB_SUBANNS_DATA = _get_comma_tab(SAMPLE_SUBANNOTATION_LINES)


def _proc_file_spec(fspec, folder, lines=None):
    """
    Process a file  specification, writing any data necessary.

    :param str fspec: name of the kind of specification being processed
    :param str folder: path to folder in which to place file if written
    :param Iterable[str] lines: collection of lines to write to file
    :return str: path to file written; null iff the specification is null,
        empty iff the specification is empty, and path to file written otherwise
    """
    if fspec is None:
        return None
    elif not fspec:
        fp = ""
    else:
        fp = os.path.join(folder, fspec)
        if lines:
            with open(fp, 'w') as f:
                for l in lines:
                    f.write(l)
    return fp


@pytest.fixture(scope="function")
def prj(request, tmpdir):
    """ Provide a test case with a parameterized Project instance. """
    def proc(spec):
        fp = request.getfixturevalue(spec + FILE_FIXTURE_SUFFIX)
        data_fixture_name = spec + DATA_FIXTURE_SUFFIX
        lines = request.getfixturevalue(data_fixture_name) \
            if data_fixture_name in request.fixturenames else []
        return _proc_file_spec(fp, tmpdir.strpath, lines)
    anns = proc(ANNS_FIXTURE_PREFIX)
    subs = proc(SUBS_FIXTURE_PREFIX)
    data = {METADATA_KEY: {OUTDIR_KEY: tmpdir.strpath}}
    if anns:
        data[METADATA_KEY][SAMPLE_ANNOTATIONS_KEY] = anns
    if subs:
        data[METADATA_KEY][SAMPLE_SUBANNOTATIONS_KEY] = subs
    conf = tmpdir.join("prjcfg.yaml").strpath
    with open(conf, 'w') as f:
        yaml.dump(data, f)
    return Project(conf)


def _assert_absent_prj_var(p, var):
    """
    Assert that a Project lacks a particular variable.

    :param peppy.Project p: Project on which to check variable absence
    :param str var: name of variable to check as absent
    """
    with pytest.raises(AttributeError):
        getattr(p, var)
    with pytest.raises(KeyError):
        p[var]


def _assert_null_prj_var(p, var):
    """
    Assert that a Project is null in a particular variable.

    :param peppy.Project p: Project on which to check variable nullity
    :param str var: name of variable to check as null
    """
    assert getattr(p, var) is None
    assert p[var] is None


@pytest.mark.parametrize(ANNS_FIXTURE_PREFIX + FILE_FIXTURE_SUFFIX, [None, ""])
@pytest.mark.parametrize(SUBS_FIXTURE_PREFIX + FILE_FIXTURE_SUFFIX, [None, ""])
def test_no_annotations_sheets(anns_file, subs_file, prj):
    """ Test project configuration with neither samples nor subsamples. """
    assert prj.get(SAMPLE_ANNOTATIONS_KEY) is None
    assert prj.get(SAMPLE_SUBANNOTATIONS_KEY) is None


@pytest.mark.parametrize(
    [ANNS_FIXTURE_PREFIX + FILE_FIXTURE_SUFFIX,
     ANNS_FIXTURE_PREFIX + DATA_FIXTURE_SUFFIX],
    [("annsA.csv", COMMA_ANNS_DATA),
     ("annsB.tsv", TAB_ANNS_DATA),
     ("annsC.txt", TAB_ANNS_DATA)])
@pytest.mark.parametrize(SUBS_FIXTURE_PREFIX + FILE_FIXTURE_SUFFIX, [None, ""])
def test_annotations_without_subannotations(anns_data, anns_file, subs_file, prj):
    """ Test project config with main samples but no subsamples. """
    _check_table(prj, SAMPLE_ANNOTATIONS_KEY, len(SAMPLE_ANNOTATION_LINES) - 1)
    _assert_null_prj_var(prj, SAMPLE_SUBANNOTATIONS_KEY)


@pytest.mark.parametrize(
    [SUBS_FIXTURE_PREFIX + FILE_FIXTURE_SUFFIX,
     SUBS_FIXTURE_PREFIX + DATA_FIXTURE_SUFFIX],
    [("subann1.csv", COMMA_SUBANNS_DATA),
     ("subann2.tsv", TAB_SUBANNS_DATA),
     ("subann3.txt", TAB_SUBANNS_DATA)])
@pytest.mark.parametrize(ANNS_FIXTURE_PREFIX + FILE_FIXTURE_SUFFIX, [None, ""])
def test_subannotations_without_annotations(subs_data, subs_file, anns_file, prj):
    """ Test project config with subsamples but no main samples. """
    _check_table(prj, SAMPLE_SUBANNOTATIONS_KEY, len(SAMPLE_SUBANNOTATION_LINES) - 1)
    _assert_null_prj_var(prj, SAMPLE_ANNOTATIONS_KEY)


@pytest.mark.parametrize(
    [ANNS_FIXTURE_PREFIX + FILE_FIXTURE_SUFFIX,
     ANNS_FIXTURE_PREFIX + DATA_FIXTURE_SUFFIX],
    [("anns1.csv", COMMA_ANNS_DATA),
     ("anns2.tsv", TAB_ANNS_DATA),
     ("anns3.txt", TAB_ANNS_DATA)])
@pytest.mark.parametrize(
    [SUBS_FIXTURE_PREFIX + FILE_FIXTURE_SUFFIX,
     SUBS_FIXTURE_PREFIX + DATA_FIXTURE_SUFFIX],
    [("subannA.csv", COMMA_SUBANNS_DATA),
     ("subannB.tsv", TAB_SUBANNS_DATA),
     ("subannC.txt", TAB_SUBANNS_DATA)])
def test_both_annotations_sheets(anns_data, anns_file, subs_data, subs_file, prj):
    """ Test project config with both main samples and subsamples. """
    _check_table(prj, SAMPLE_ANNOTATIONS_KEY, len(SAMPLE_ANNOTATION_LINES) - 1)
    _check_table(prj, SAMPLE_SUBANNOTATIONS_KEY, len(SAMPLE_SUBANNOTATION_LINES) - 1)


@pytest.mark.skip("Not implemented")
def test_both_old_encodings():
    """ Current and previous encoding of tables works, deprecated appropriately. """
    pass


@pytest.mark.skip("Not implemented")
def test_mixed_old_new_encoding():
    """ Current and previous encoding of tables works, deprecated appropriately. """
    pass


@pytest.mark.skip("Not implemented")
def test_preservation_during_subproject_activation():
    """ Tables are preserved when a subproject is activated iff it declares no tables. """
    pass


@pytest.mark.skip("Not implemented")
def test_dynamism_during_subproject_activation():
    """ Subproject's declared table(s) take precedence over existing ones."""
    pass


def _check_table(p, k, exp_nrow):
    """
    Validate expectations about a particular table attribute on Project.

    :param peppy.Project p: Project to validate
    :param str k: key/attribute that references the table of interest
    :param int exp_nrow: expected number of rows in the table
    """
    dt_att = getattr(p, k)
    dt_key = p[k]
    assert all((dt_att == dt_key).all())
    obs_nrow = len(dt_att.index)
    assert exp_nrow == obs_nrow, "Rows: exp={}, obs={}".format(exp_nrow, obs_nrow)
