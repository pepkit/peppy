""" Tests for constant_attributes in the context of a subproject """

import os
import pytest
import yaml
from peppy import Project
from peppy.const import *

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


SUBS1 = {"const1": 1}
SUBP_MAP = {"with_const": {CONSTANTS_DECLARATION: SUBS1},
            "without_const": {}}


@pytest.mark.parametrize("main_const", [{}])
@pytest.mark.parametrize(
    ["subp", "expected"], [("with_const", SUBS1), ("without_const", {})])
def test_subproject_introduces_constants(prj, subp, expected, main_const):
    """ A subproject can add constant to a Project that lacked them. """
    assert not prj[CONSTANTS_DECLARATION]
    prj = prj.activate_subproject(subp)
    assert expected == prj[CONSTANTS_DECLARATION]


@pytest.mark.parametrize(
    "main_const", [{"fixed_main_const": "arbval"}, {"RK": "random"}])
def test_constants_survive_activation_of_subproject_without_constants(prj, main_const):
    """ Constants survive if extant and subproject declares none. """
    assert main_const == prj[CONSTANTS_DECLARATION]
    prj.activate_subproject("without_const")
    assert main_const == prj[CONSTANTS_DECLARATION]


@pytest.mark.parametrize(
    "main_const", [{"fixed_main_const": "arbval"}, {"RK": "random"}])
def test_constants_are_overwritten_by_subproject(prj, main_const):
    """ A subproject's constants take precedence over existing. """
    assert main_const == prj[CONSTANTS_DECLARATION]
    prj.activate_subproject("with_const")
    assert SUBS1 == prj[CONSTANTS_DECLARATION]


@pytest.mark.skip("Not implemented")
def test_constants_are_restored_after_subproject_deactivation(main_const):
    """ After subproject deactivation, project's original constants return. """
    pass


@pytest.fixture
def prj(tmpdir, request):
    """ Create Project after writing config in given tempfolder. """
    tmp = tmpdir.strpath
    assert os.path.isdir(tmp)
    main_const = request.getfixturevalue("main_const")
    data = {METADATA_KEY: {OUTDIR_KEY: tmp}, SUBPROJECTS_SECTION: SUBP_MAP}
    cfg = os.path.join(tmp, "pc.yaml")
    assert not os.path.exists(cfg), "Config path already exists: {}".format(cfg)
    if main_const:
        data[CONSTANTS_DECLARATION] = main_const
        check = lambda p: main_const == p[CONSTANTS_DECLARATION]
    else:
        check = lambda p: {} == CONSTANTS_DECLARATION
    with open(cfg, 'w') as f:
        yaml.dump(data, f)
    p = Project(cfg)
    check(p)
    return p
