""" Regression tests related to subproject activation behavior """

import mock
import os
import pytest
import yaml
from peppy import Project
from peppy import SAMPLE_ANNOTATIONS_KEY
from peppy.const import METADATA_KEY, NAME_TABLE_ATTR
from tests.helpers import randomize_filename

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


_PARENT_ANNS = "sample_annotation.csv"
_CHILD_ANNS = "sample_annotation_sp1.csv"
_SP_NAME = "dog"


def touch(folder, name):
    """ In provided folder, create empty file with given name. """
    fp = os.path.join(folder, name)
    with open(fp, 'w'):
        return fp


@pytest.fixture(scope="function")
def conf_data(tmpdir):
    """ Provide the project configuration data, writing each annotation file. """
    d = tmpdir.strpath
    parent_sheet_file = touch(d, _PARENT_ANNS)
    child_sheet_file = touch(d, _CHILD_ANNS)
    return {
        METADATA_KEY: {
            SAMPLE_ANNOTATIONS_KEY: parent_sheet_file,
            "output_dir": tmpdir.strpath,
            "pipeline_interfaces": tmpdir.strpath
        },
        "subprojects": {
            _SP_NAME: {METADATA_KEY: {SAMPLE_ANNOTATIONS_KEY: child_sheet_file}}
        }
    }


@pytest.fixture(scope="function")
def conf_file(tmpdir, conf_data):
    """ Write project config data to a tempfile and provide the filepath. """
    conf = tmpdir.join(randomize_filename(n_char=20)).strpath
    with open(conf, 'w') as f:
        yaml.dump(conf_data, f)
    return conf


class SubprojectSampleAnnotationTests:
    """ Tests concerning sample annotations path when a subproject is used. """

    @staticmethod
    def test_annotations_path_is_from_subproject(conf_file):
        """ Direct Project construction with subproject points to anns file. """
        with mock.patch("peppy.project.Project.parse_sample_sheet"):
            p = Project(conf_file, subproject=_SP_NAME)
        _, anns_file = os.path.split(p[METADATA_KEY][NAME_TABLE_ATTR])
        assert _CHILD_ANNS == anns_file

    @staticmethod
    def test_subproject_activation_updates_sample_annotations_path(conf_file):
        """ Subproject's sample annotation file pointer replaces original. """
        with mock.patch("peppy.project.Project.parse_sample_sheet"):
            p = Project(conf_file)
            p.activate_subproject(_SP_NAME)
        _, anns_file = os.path.split(p[METADATA_KEY][NAME_TABLE_ATTR])
        assert _CHILD_ANNS == anns_file
