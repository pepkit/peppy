""" Regression tests related to subproject activation behavior """

import os

import mock
import pytest
import yaml

from peppy import Project
from peppy.const import *
from peppy.project import NEW_PIPES_KEY, RESULTS_FOLDER_VALUE, SUBMISSION_FOLDER_VALUE
from tests.helpers import randomize_filename

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


_PARENT_ANNS = "sample_annotation.csv"
_CHILD_ANNS = "sample_annotation_sp1.csv"
_SP_NAME = "dog"
SHEET_PARSE_FUNCPATH = "peppy.project.Project.parse_sample_sheet"


def touch(folder, name):
    """In provided folder, create empty file with given name."""
    fp = os.path.join(folder, name)
    with open(fp, "w"):
        return fp


@pytest.fixture(scope="function")
def conf_data(tmpdir):
    """Provide the project configuration data, writing each annotation file."""
    d = tmpdir.strpath
    parent_sheet_file = touch(d, _PARENT_ANNS)
    child_sheet_file = touch(d, _CHILD_ANNS)
    return {
        METADATA_KEY: {
            NAME_TABLE_ATTR: parent_sheet_file,
            OUTDIR_KEY: tmpdir.strpath,
            NEW_PIPES_KEY: tmpdir.strpath,
        },
        SUBPROJECTS_SECTION: {
            _SP_NAME: {METADATA_KEY: {NAME_TABLE_ATTR: child_sheet_file}}
        },
    }


@pytest.fixture(scope="function")
def conf_file(tmpdir, conf_data):
    """Write project config data to a tempfile and provide the filepath."""
    conf = tmpdir.join(randomize_filename(n_char=20)).strpath
    with open(conf, "w") as f:
        yaml.dump(conf_data, f)
    return conf


class SubprojectSampleAnnotationTests:
    """Tests concerning sample annotations path when a subproject is used."""

    @staticmethod
    def test_annotations_path_is_from_subproject(conf_file):
        """Direct Project construction with subproject points to anns file."""
        with mock.patch(SHEET_PARSE_FUNCPATH):
            p = Project(conf_file, subproject=_SP_NAME)
        _, anns_file = os.path.split(p[METADATA_KEY][NAME_TABLE_ATTR])
        assert _CHILD_ANNS == anns_file

    @staticmethod
    def test_subproject_activation_updates_sample_annotations_path(conf_file):
        """Subproject's sample annotation file pointer replaces original."""
        with mock.patch(SHEET_PARSE_FUNCPATH):
            p = Project(conf_file)
            p.activate_subproject(_SP_NAME)
        _, anns_file = os.path.split(p[METADATA_KEY][NAME_TABLE_ATTR])
        assert _CHILD_ANNS == anns_file


class SubprojectMetadataPathTests:
    """Tests for behavior of metadata section paths in the context of subprojects."""

    @pytest.fixture
    def prj(self, tmpdir, conf_data):
        """Provide test cases with a Project that features a subproject that declares output_dir."""
        suboutfolder = "tmp_sub_folder"
        suboutpath = os.path.join(tmpdir.strpath, suboutfolder)
        assert OUTDIR_KEY in conf_data[METADATA_KEY]
        assert OUTDIR_KEY not in conf_data[SUBPROJECTS_SECTION][_SP_NAME]
        assert suboutpath != conf_data[METADATA_KEY][OUTDIR_KEY]
        conf_data[SUBPROJECTS_SECTION][_SP_NAME][METADATA_KEY][OUTDIR_KEY] = suboutpath
        conf_path = tmpdir.join("conf.yaml").strpath
        with open(conf_path, "w") as f:
            yaml.dump(conf_data, f)
        with mock.patch(SHEET_PARSE_FUNCPATH):
            return Project(conf_path)

    @pytest.mark.parametrize(
        "check",
        [
            lambda sub: sub.results_folder
            == os.path.join(sub.output_dir, RESULTS_FOLDER_VALUE),
            lambda sub: sub.submission_folder
            == os.path.join(sub.output_dir, SUBMISSION_FOLDER_VALUE),
        ],
    )
    def test_relative_path_metadata_dynamism(self, prj, check):
        """Results and submission paths are relative to whatever output_dir is."""
        main_out = prj.output_dir
        with mock.patch(SHEET_PARSE_FUNCPATH):
            sub = prj.activate_subproject(_SP_NAME)
        assert sub.output_dir != main_out
        assert check(sub)

    @pytest.mark.parametrize(
        "eq_attr", ["output_dir", "results_folder", "submission_folder"]
    )
    def test_relative_path_metadata_stasis(self, conf_file, eq_attr):
        """Key metadata paths are preserved with subproject that doesn't alter them."""
        with mock.patch(SHEET_PARSE_FUNCPATH):
            p = Project(conf_file)
        main_path = getattr(p, eq_attr)
        with mock.patch(SHEET_PARSE_FUNCPATH):
            sub = p.activate_subproject(_SP_NAME)
        assert main_path == getattr(sub, eq_attr)
