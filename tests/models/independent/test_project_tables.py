""" Tests regarding Project data tables """

from collections import namedtuple
from copy import deepcopy
from functools import partial
import os
import sys
if sys.version_info < (3, 3):
    from collections import Mapping
else:
    from collections.abc import Mapping
import pandas as pd
from pandas import DataFrame
import pytest
import yaml
from peppy import Project
from peppy.const import *
from peppy.utils import infer_delimiter
from peppy.project import OLD_ANNS_META_KEY, OLD_SUBS_META_KEY, READ_CSV_KWARGS
from tests.conftest import SAMPLE_ANNOTATION_LINES, SAMPLE_SUBANNOTATION_LINES
from tests.helpers import randomize_filename


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


ANNS_FIXTURE_PREFIX = "anns"
SUBS_FIXTURE_PREFIX = "subs"
FILE_FIXTURE_SUFFIX = "_file"
DATA_FIXTURE_SUFFIX = "_data"
SP_SPECS_KEY = "subprj_specs"


def _get_comma_tab(lines):
    """ Get parallel collections of comma- and tab-delimiter lines """
    return [l.replace("\t", ",") for l in lines], \
           [l.replace(",", "\t") for l in lines]


COMMA_ANNS_DATA, TAB_ANNS_DATA = _get_comma_tab(SAMPLE_ANNOTATION_LINES)
COMMA_SUBANNS_DATA, TAB_SUBANNS_DATA = _get_comma_tab(SAMPLE_SUBANNOTATION_LINES)
LINES_BY_DELIM = {"\t": (TAB_ANNS_DATA, TAB_SUBANNS_DATA),
                  ",": (COMMA_ANNS_DATA, COMMA_SUBANNS_DATA)}


SubPrjDataSpec = namedtuple("SubPrjDataSpec", ["key", "filename", "lines"])


def pytest_generate_tests(metafunc):
    """ Dynamic test case generation and parameterization for this module. """
    if "delimiter" in metafunc.fixturenames:
        metafunc.parametrize("delimiter", ["\t", ","])


def _flip_table_data(lines):
    return [lines[0]] + lines[1:][::-1]


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
        assert anns1.equals(anns2)
        assert subs1.equals(subs2)


def _add_sp_section(md, subproj_section):
    """
    To an existing collection of Project metadata, add subprojects section.

    :param MutableMapping md: collection of Project metadata to updated
    :param Mapping subproj_section: subprojects section config data
    :return Mapping: input data with subprojects data added
    """
    assert SUBPROJECTS_SECTION not in md, \
        "Subprojects section ('{}') is already present".format(SUBPROJECTS_SECTION)
    res = deepcopy(md)
    res[SUBPROJECTS_SECTION] = subproj_section
    return res


def _guess_delim(lines):
    commas = all(["," in l for l in lines])
    tabs = all(["\t" in l for l in lines])
    if (commas and tabs) or not (commas or tabs):
        raise ValueError("Could not infer delimiter from input lines:\n{}".
                         format("\n".join(lines)))
    return ".csv" if commas else ".tsv"


def get_sp_par(k, f, lines, fn=None):
    """
    Create a particular test case parameterization scheme.

    :param str k: the key/attr name for a metadata annotations file
    :param function f: function with which to retrieve key's value from
        Project instance
    :param Iterable[str] lines: collection of lines to write to the metadata
        annotations file named here
    :param str fn: name for metadata annotations file, which will be bound
        as value to given key
    :return str, function, namedtuple: 3-tuple in which first component is
        key/attr name, second is function with which to retrieve value for that
        key from a Project instance, and third is a specification used by a
        fixture to write the subproject's file(s) and to add the subproject
        metadata to a project's general configuration metadata.
    :raise ValueError: if filename is not provided or one is provided without
        extension, and extension cannot be inferred from data lines
    """
    ext = os.path.splitext(fn)[1] if fn else None
    if not ext:
        ext = _guess_delim(lines)
    if not fn:
        fn = randomize_filename(ext=ext)
    elif not os.path.splitext(fn)[1]:
        fn = fn + ext
    return k, f, SubPrjDataSpec(k, fn, lines)


_FETCHERS = {SAMPLE_ANNOTATIONS_KEY: [_getatt, _getkey],
             SAMPLE_SUBANNOTATIONS_KEY: [_getatt, _getkey],
             OLD_ANNS_META_KEY: [get_att_dep, get_key_dep],
             OLD_SUBS_META_KEY: [get_att_dep, get_key_dep]}


class SubprojectActivationSampleMetadataAnnotationTableTests:
    """ Tests for behavior of tables in context of subproject activation. """

    INJECTED_SP_NAME = "injected_subproject"

    @pytest.fixture(scope="function")
    def prj(self, request, tmpdir, prj_data):
        """ Provide test case with a Project instance. """
        # TODO: write newer sheets.
        data = deepcopy(prj_data)
        fixnames = request.fixturenames
        check = False
        if SUBPROJECTS_SECTION in fixnames and SP_SPECS_KEY in fixnames:
            raise Exception("Conflicting test case subproject parameterizations: "
                            "{} and {}".format(SUBPROJECTS_SECTION, SP_SPECS_KEY))
        elif SP_SPECS_KEY in request.fixturenames:
            kvs = {}
            specs = request.getfixturevalue(SP_SPECS_KEY)
            if isinstance(specs, SubPrjDataSpec):
                specs = [specs]
            elif not isinstance(specs, list):
                raise TypeError(
                    "Subproject specs value must be a single spec or a "
                    "collection of them; got {}".format(type(specs)))
            for spec in specs:
                fn = spec.filename
                with open(tmpdir.join(fn).strpath, 'w') as f:
                    for l in spec.lines:
                        f.write(l)
                kvs[spec.key] = fn
            data[SUBPROJECTS_SECTION] = {
                self.INJECTED_SP_NAME: {METADATA_KEY: kvs}}
            check = True
        elif SUBPROJECTS_SECTION in request.fixturenames:
            kvs = request.getfixturevalue(SUBPROJECTS_SECTION)
            if not isinstance(kvs, Mapping):
                raise TypeError(
                    "Test case subproject parameterization ({}) isn't a mapping: {}".
                        format(SUBPROJECTS_SECTION, type(kvs)))
            data[SUBPROJECTS_SECTION] = kvs
            check = True
        if check:
            assert SUBPROJECTS_SECTION in data, \
                "Missing {} section".format(SUBPROJECTS_SECTION)
        conf = tmpdir.join("prjcfg.yaml").strpath
        with open(conf, 'w') as f:
            yaml.dump(data, f)
        return Project(conf)

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
    @pytest.mark.parametrize(
        ["key", "fun", SP_SPECS_KEY],
        [get_sp_par(*args) for args in [
            (k, f, _flip_table_data(SAMPLE_ANNOTATION_LINES))
            for k in [SAMPLE_ANNOTATIONS_KEY, OLD_ANNS_META_KEY] for f in _FETCHERS[k]]])
    def test_subproject_uses_different_main_table(prj, tmpdir,
            anns_file, anns_data, subs_file, subs_data, fun, key, subprj_specs):
        """ Main table is updated while subannotations are unaffected. """
        orig_anns = fun(prj, key)
        orig_subs = prj[SAMPLE_SUBANNOTATIONS_KEY]
        assert isinstance(orig_anns, DataFrame)
        assert SUBPROJECTS_SECTION in prj
        sps = list(prj[SUBPROJECTS_SECTION].keys())
        assert 1 == len(sps)
        sp = sps[0]
        prj.activate_subproject(sp)
        assert sp == prj.subproject
        assert orig_subs.equals(prj[SAMPLE_SUBANNOTATIONS_KEY])
        new_anns_obs = fun(prj, key)
        assert not orig_anns.equals(new_anns_obs)
        new_anns_filepath = os.path.join(
            tmpdir.strpath, prj[SUBPROJECTS_SECTION][sp][METADATA_KEY][key])
        new_anns_exp = pd.read_csv(new_anns_filepath,
            sep=infer_delimiter(new_anns_filepath), **READ_CSV_KWARGS)
        assert new_anns_exp.equals(new_anns_obs)


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
    @pytest.mark.parametrize(
        ["key", "fun", SP_SPECS_KEY],
        [get_sp_par(*args) for args in [
            (k, f, _flip_table_data(SAMPLE_SUBANNOTATION_LINES))
            for k in [SAMPLE_SUBANNOTATIONS_KEY, OLD_SUBS_META_KEY] for f in _FETCHERS[k]]])
    def test_subproject_uses_different_subsamples(prj, tmpdir,
            anns_file, anns_data, subs_file, subs_data, fun, key, subprj_specs):
        """ Subannotations are updated while the main table is unaltered. """
        orig_anns = prj[SAMPLE_ANNOTATIONS_KEY]
        orig_subs = fun(prj, key)
        assert isinstance(orig_subs, DataFrame)
        assert SUBPROJECTS_SECTION in prj
        sps = list(prj[SUBPROJECTS_SECTION].keys())
        assert 1 == len(sps)
        sp = sps[0]
        prj.activate_subproject(sp)
        assert sp == prj.subproject
        assert orig_anns.equals(prj[SAMPLE_ANNOTATIONS_KEY])
        new_subs_obs = fun(prj, key)
        assert not orig_subs.equals(new_subs_obs)
        new_subs_filepath = os.path.join(
            tmpdir.strpath, prj[SUBPROJECTS_SECTION][sp][METADATA_KEY][key])
        new_subs_exp = pd.read_csv(new_subs_filepath,
            sep=infer_delimiter(new_subs_filepath), **READ_CSV_KWARGS)
        assert new_subs_exp.equals(new_subs_obs)

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
    @pytest.mark.parametrize(
        ["ann_key", "sub_key", "fun", SP_SPECS_KEY],
        [(k1, k2, f, [SubPrjDataSpec(k, randomize_filename(ext=_guess_delim(ls)), ls) for k, ls in
                      [(k1, _flip_table_data(SAMPLE_ANNOTATION_LINES)),
                       (k2, _flip_table_data(SAMPLE_SUBANNOTATION_LINES))]])
         for k1, k2 in [(SAMPLE_ANNOTATIONS_KEY, SAMPLE_SUBANNOTATIONS_KEY),
                        (OLD_ANNS_META_KEY, OLD_SUBS_META_KEY)] for f in _FETCHERS[k1]])
    def test_subproject_uses_different_main_and_subsample_table(prj, tmpdir,
            anns_file, anns_data, subs_file, subs_data, ann_key, sub_key, fun,
            subprj_specs):
        """ Both metadata annotation tables can be updated by subproject. """
        orig_anns, orig_subs = fun(prj, ann_key), fun(prj, sub_key)
        assert SUBPROJECTS_SECTION in prj
        sps = list(prj[SUBPROJECTS_SECTION].keys())
        assert 1 == len(sps)
        sp = sps[0]
        prj.activate_subproject(sp)
        assert sp == prj.subproject
        new_anns, new_subs = fun(prj, ann_key), fun(prj, sub_key)
        assert not orig_subs.equals(new_anns)
        assert not orig_subs.equals(new_subs)
        subs_sect = prj[SUBPROJECTS_SECTION][sp][METADATA_KEY]
        ann_fp = os.path.join(tmpdir.strpath, subs_sect[ann_key])
        sub_fp = os.path.join(tmpdir.strpath, subs_sect[sub_key])
        exp_ann = pd.read_csv(ann_fp, **READ_CSV_KWARGS)
        exp_sub = pd.read_csv(sub_fp, **READ_CSV_KWARGS)
        assert exp_ann.equals(new_anns)
        assert exp_sub.equals(new_subs)

    @staticmethod
    @pytest.mark.parametrize(
        ["key", "fun", SP_SPECS_KEY],
        [get_sp_par(*args) for args in
         [(k, f, lines) for k, lines in [
             (SAMPLE_ANNOTATIONS_KEY, SAMPLE_ANNOTATION_LINES),
             (SAMPLE_SUBANNOTATIONS_KEY, SAMPLE_SUBANNOTATION_LINES),
             (OLD_ANNS_META_KEY, SAMPLE_ANNOTATION_LINES),
             (OLD_SUBS_META_KEY, SAMPLE_SUBANNOTATION_LINES)]
          for f in _FETCHERS[k]]])
    def test_subproject_introduces_both_table_kinds(prj, fun, key, subprj_specs):
        """ Both metadata annotation tables can be introduced by subproject. """
        assert fun(prj, key) is None
        assert SUBPROJECTS_SECTION in prj
        sp_names = list(prj[SUBPROJECTS_SECTION].keys())
        assert 1 == len(sp_names)
        sp = sp_names[0]
        prj.activate_subproject(sp)
        assert sp == prj.subproject
        newval = fun(prj, key)
        assert isinstance(newval, DataFrame)
        num_entries_exp = len(subprj_specs.lines) - 1
        num_entries_obs = len(newval.index)
        assert num_entries_exp == num_entries_obs, \
            "Expected {} metadata annotation entries but found {}".\
            format(num_entries_exp, num_entries_obs)

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
    @pytest.mark.parametrize(SUBPROJECTS_SECTION,
        [{"random_sp_name": {METADATA_KEY: {OUTDIR_KEY: "random_ouput_subdir"}}}])
    @pytest.mark.parametrize("fun", [_getatt, _getkey])
    def test_preservation_during_subproject_activation(
            prj, fun, subprojects, anns_file, anns_data, subs_file, subs_data):
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
        assert anns1.equals(anns2)
        assert subs1.equals(subs2)


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
    assert dt_att.equals(dt_key)
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
