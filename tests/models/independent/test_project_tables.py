""" Tests regarding Project data tables """

from copy import deepcopy
from functools import partial
import os
import pytest
import yaml
from peppy import Project
from peppy.const import *
from peppy.project import OLD_ANNS_META_KEY, OLD_SUBS_META_KEY
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
LINES_BY_DELIM = {"\t": (TAB_ANNS_DATA, TAB_SUBANNS_DATA),
                  ",": (COMMA_ANNS_DATA, COMMA_SUBANNS_DATA)}


def pytest_generate_tests(metafunc):
    """ Dynamic test case generation and parameterization for this module. """
    if "delimiter" in metafunc.fixturenames:
        metafunc.parametrize("delimiter", ["\t", ","])


@pytest.fixture(scope="function")
def prj_data(request, tmpdir):
    """
    Provide basic Project data, based on inspection of requesting test case.

    :param pytest.fixture.FixtureRequest request: test case requesting this
        fixture
    :param py.path.LocalPath tmpdir: temporary directory for a test case
    :return Mapping: basic data with which to create Project
    """
    def proc(spec):
        fixname = spec + FILE_FIXTURE_SUFFIX
        if fixname not in request.fixturenames:
            return None
        fp = request.getfixturevalue(fixname)
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
    if SUBPROJECTS_SECTION in request.fixturenames:
        data[SUBPROJECTS_SECTION] = \
            request.getfixturevalue(SUBPROJECTS_SECTION)
    return deepcopy(data)


@pytest.fixture(scope="function")
def prj(prj_data, tmpdir):
    """ Provide a test case with a parameterized Project instance. """
    conf = tmpdir.join("prjcfg.yaml").strpath
    with open(conf, 'w') as f:
        yaml.dump(prj_data, f)
    return Project(conf)


def _get_via_dep(p, k, f):
    """
    Fetch value for particular key from a Project, asserting deprecation.

    :param peppy.Project p: project from which to retrieve value
    :param str k: key for which to retrieve value
    :param function f: function with which to do the retrieval
    """
    with pytest.warns(DeprecationWarning):
        return f(p, k)


def _getatt(p, n):
    return getattr(p, n)


def _getkey(p, k):
    return p[k]


# Get deprecated key's value.
get_key_dep = partial(_get_via_dep, f=_getkey)

# Get deprecated attribute's value.
get_att_dep = partial(_get_via_dep, f=_getatt)


@pytest.mark.parametrize("key", [OLD_ANNS_META_KEY, OLD_SUBS_META_KEY])
@pytest.mark.parametrize("fun", [get_att_dep, get_key_dep])
def test_no_sheets_old_access(prj, key, fun):
    """ When the Project uses neither metadata table slot, they're null. """
    assert fun(prj, key) is None


@pytest.mark.parametrize(
    "key", [SAMPLE_ANNOTATIONS_KEY, SAMPLE_SUBANNOTATIONS_KEY])
@pytest.mark.parametrize("fun", [_getatt, _getkey])
def test_no_sheets_new_access(prj, key, fun):
    """ When the Project uses neither metadata table slot, they're null. """
    assert fun(prj, key) is None


@pytest.fixture(scope="function")
def main_table_file(request):
    """ Determine path for main sample metadata annotations file. """
    return _get_path_from_req(request, "anns")


@pytest.fixture(scope="function")
def subann_table_file(request):
    """ Path to metadata subannotations file """
    return _get_path_from_req(request, "subann")


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


class SampleAnnotationConfigEncodingTests:
    """ Tests for ways of encoding/representing sample annotations in project config. """

    @staticmethod
    @pytest.mark.parametrize("anns_key", [OLD_ANNS_META_KEY])
    @pytest.mark.parametrize("subs_key", [OLD_SUBS_META_KEY])
    def test_old_encodings(
            delimiter, tmpdir, main_table_file,
            subann_table_file, anns_key, subs_key):
        """ Current and previous encoding of tables works, deprecated appropriately. """
        # Data setup
        anns_data, subs_data = LINES_BY_DELIM[delimiter]
        anns_file = _write(main_table_file, anns_data)
        subs_file = _write(subann_table_file, subs_data)
        conf_file = tmpdir.join("conf.yaml").strpath
        conf_data = {
            METADATA_KEY: {
                anns_key: anns_file,
                subs_key: subs_file,
                OUTDIR_KEY: tmpdir.strpath
            }
        }
        # Project creation
        with open(conf_file, 'w') as cfg:
            yaml.dump(conf_data, cfg)
        prj = Project(conf_file)
        # Behavioral validation/assertions
        with pytest.warns(DeprecationWarning):
            anns1 = getattr(prj, anns_key)
        with pytest.warns(DeprecationWarning):
            anns2 = prj[anns_key]
        with pytest.warns(DeprecationWarning):
            subs1 = getattr(prj, subs_key)
        with pytest.warns(DeprecationWarning):
            subs2 = prj[subs_key]
        # Validation that we didn't just get back garbage value(s)
        assert all((anns1 == anns2).all())
        assert all((subs1 == subs2).all())


class SubprojectActivationSampleMetadataAnnotationTableTests:
    """ Tests for behavior of tables in context of subproject activation. """

    @staticmethod
    def newer_lines(orig):
        """ Reverse a collection of lines to provide a trivial difference. """
        newer = reversed(orig)
        assert newer != orig
        return newer

    @pytest.fixture(scope="function")
    def newer_anns_lines(self):
        """ Reverse the main annotation lines to provide a diff. """
        return self.newer_lines(SAMPLE_ANNOTATION_LINES)

    @pytest.fixture(scope="function")
    def newer_subs_lines(self):
        """ Reverse the subannotation lines to provide a diff. """
        return self.newer_lines(SAMPLE_SUBANNOTATION_LINES)

    @staticmethod
    def prj(request, tmpdir, prj_data):
        """ Provide test case with a Project instance. """
        # TODO: write newer sheets.
        data = deepcopy(prj_data)
        data[SUBPROJECTS_SECTION] = request.getfixturevalue(SUBPROJECTS_SECTION)
        conf = tmpdir.join("prjcfg.yaml", 'w').strpath
        with open(conf, 'w') as f:
            yaml.dump(prj_data, f)
        return Project(conf)

    @staticmethod
    @pytest.mark.skip("Not implemented")
    @pytest.mark.parametrize("subprojects", [])
    def test_subproject_uses_different_main_table(prj, subprojects):
        """ Main table is updated while subannotations are unaffected. """
        pass

    @staticmethod
    @pytest.mark.skip("Not implemented")
    @pytest.mark.parametrize(SUBPROJECTS_SECTION, [])
    def test_subproject_uses_different_subsamples(prj, subprojects):
        """ Subannotations are updated while the main table is unaltered. """
        pass

    @staticmethod
    @pytest.mark.skip("Not implemented")
    @pytest.mark.parametrize(SUBPROJECTS_SECTION, [])
    def test_subproject_uses_different_main_and_subsample_table(prj, subprojects):
        """ Both metadata annotation tables can be updated by subproject. """
        pass

    @staticmethod
    @pytest.mark.skip("Not implemented")
    @pytest.mark.parametrize(SUBPROJECTS_SECTION, [])
    def test_subproject_introduces_both_table_kinds(prj, subprojects):
        """ Both metadata annotation tables can be introduced by subproject. """
        pass

    @staticmethod
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
    @pytest.mark.parametrize(SUBPROJECTS_SECTION, [
        {"random_sp_name": {
            METADATA_KEY: {
                SAMPLE_ANNOTATIONS_KEY: "newer_table.tsv",
                SAMPLE_SUBANNOTATIONS_KEY: "newer_units.tsv"
            }
        }}
    ])
    @pytest.mark.parametrize("fun", [_getatt, _getkey])
    def test_preservation_during_subproject_activation(
            anns_file, anns_data, subs_file, subs_data, prj, fun, subprojects):
        """ Tables are preserved when a subproject is activated if it declares no tables. """
        subs = prj[SUBPROJECTS_SECTION]
        for k in [SAMPLE_ANNOTATIONS_KEY, SAMPLE_SUBANNOTATIONS_KEY,
                  OLD_ANNS_META_KEY, OLD_SUBS_META_KEY]:
            assert k not in subs, "Table key in subprojects section: {}".format(k)
        anns1, subs1 = fun(prj, SAMPLE_ANNOTATIONS_KEY), \
                       fun(prj, SAMPLE_SUBANNOTATIONS_KEY)
        assert anns1 is not None
        assert subs1 is not None
        prj.activate_subproject("random_sp_name")
        anns2 = fun(prj, SAMPLE_ANNOTATIONS_KEY)
        subs2 = fun(prj, SAMPLE_SUBANNOTATIONS_KEY)
        assert all((anns1 == anns2).all())
        assert all((subs1 == subs2).all())


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


def _get_extension(sep):
    """ Based on delimiter to be used, get file extension. """
    return {"\t": ".tsv", ",": ".csv"}[sep]


def _get_path_from_req(request, name):
    """ From test case parameterization request, create path for certain file. """
    sep = request.getfixturevalue("delimiter") \
        if "delimiter" in request.fixturenames else "\t"
    ext = _get_extension(sep)
    return request.getfixturevalue("tmpdir").join(name + ext).strpath


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
        lines and _write(fp, lines)
    return fp


def _write(fp, lines):
    """
    Write a collection of lines to given file.

    :param str fp: path to file to write
    :param Iterable[str] lines: collection of lines to write
    :return str: path to file written
    """
    with open(fp, 'w') as f:
        for l in lines:
            f.write(l)
    return fp
