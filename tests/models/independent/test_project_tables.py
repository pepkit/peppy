""" Tests regarding Project data tables """

import os
import pytest
import yaml
from peppy import Project
from peppy.const import *
from tests.conftest import SAMPLE_ANNOTATION_LINES

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


ANNS_FIXTURE_PREFIX = "anns"
SUBS_FIXTURE_PREFIX = "subs"
FILE_FIXTURE_SUFFIX = "_file"
DATA_FIXTURE_SUFFIX = "_data"


COMMA_ANNS_DATA = [l.replace("\t", ",") for l in SAMPLE_ANNOTATION_LINES]
TAB_ANNS_DATA = [l.replace(",", "\t") for l in COMMA_ANNS_DATA]


def _proc_file_spec(fspec, folder, lines=None):
    if fspec is None:
        return None
    elif not fspec:
        fp = ""
    else:
        fp = os.path.join(folder, fspec)
        if lines:
            with open(fp, 'w') as f:
                map(lambda l: f.write(l), lines)
    return fp


@pytest.fixture(scope="function")
def prj(request, tmpdir):
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


@pytest.mark.parametrize(ANNS_FIXTURE_PREFIX + FILE_FIXTURE_SUFFIX, [None, ""])
@pytest.mark.parametrize(SUBS_FIXTURE_PREFIX + FILE_FIXTURE_SUFFIX, [None, ""])
def test_no_annotations_sheets(anns_file, subs_file, prj):
    assert prj.get(SAMPLE_ANNOTATIONS_KEY) is None
    assert prj.get(SAMPLE_SUBANNOTATIONS_KEY) is None


@pytest.mark.parametrize(
    [ANNS_FIXTURE_PREFIX + FILE_FIXTURE_SUFFIX,
     ANNS_FIXTURE_PREFIX + DATA_FIXTURE_SUFFIX],
    [("anns.csv", COMMA_ANNS_DATA),
     ("anns.tsv", TAB_ANNS_DATA),
     ("anns.txt", TAB_ANNS_DATA)])
@pytest.mark.parametrize(SUBS_FIXTURE_PREFIX + FILE_FIXTURE_SUFFIX, [None, ""])
def test_annotations_without_subannotations(anns_data, anns_file, subs_file, prj):
    dt_att = getattr(prj, SAMPLE_ANNOTATIONS_KEY)
    dt_key = prj[SAMPLE_ANNOTATIONS_KEY]
    assert all((dt_att == dt_key).all())
    obs_nrow = len(dt_att.index)
    exp_nrow = len(anns_data) -1
    assert exp_nrow == obs_nrow, \
        "{} lines but {} rows in table".format(exp_nrow, obs_nrow)
    assert prj.get(SAMPLE_SUBANNOTATIONS_KEY) is None


@pytest.mark.skip("Not implemented")
def test_subannotations_without_annotations():
    pass


@pytest.mark.skip("Not implemented")
def test_both_annotations_sheets():
    pass
