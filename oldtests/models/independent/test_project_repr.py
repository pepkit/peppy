""" Tests for Project representation """

import os
import subprocess

import pytest

from peppy import Project
from peppy.const import SUBPROJECTS_SECTION
from peppy.project import MAX_PROJECT_SAMPLES_REPR

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


REPO_NAME = "example_peps"
REPO_URL = "https://github.com/pepkit/" + REPO_NAME


@pytest.fixture(scope="class")
def example_peps(tmpdir_factory):

    tmp = tmpdir_factory.mktemp("code").strpath
    cmd = "git clone {}".format(REPO_URL)
    try:
        subprocess.check_call(cmd, cwd=tmp, shell=True)
    except subprocess.CalledProcessError:
        raise Exception("Failed to pull data ()".format(cmd))
    root = os.path.join(tmp, REPO_NAME)
    return {n: Project(p) for n, p in _determine_project_paths(root).items()}


def check_samples_repr(p):
    """
    Validate sample names portion of given Project's text repr.

    :param peppy.Project p: project instance to check
    :return str | NoneType: invalidation message if validation fails, else null
    """
    all_names = list(p.sample_names)
    text = _get_repr_lines(p)[2]
    obs_names = text.split(": ")[1].strip().split(", ")
    exp_names = (
        all_names
        if len(all_names) <= MAX_PROJECT_SAMPLES_REPR
        else all_names[:MAX_PROJECT_SAMPLES_REPR]
    )
    if exp_names != obs_names:
        return "Expected sample names {} but found {} in repr".format(
            all_names, obs_names
        )


def check_sections_repr(p):
    """
    Validate section names portion of given Project's text repr.

    :param peppy.Project p: project instance to check
    :return str | NoneType: invalidation message if validation fails, else null
    """
    all_lines = _get_repr_lines(p)
    rel_lines = [l for l in all_lines if l.startswith("Sections")]
    if len(rel_lines) != 1:
        return (
            "Project should have exactly one line for sections but has {}: "
            "{}".format(len(rel_lines), rel_lines)
        )
    text = rel_lines[0]
    names = text.split(": ")[1].strip().split(", ")
    data = [(n, getattr(p, n)) for n in names]
    bad_names = [
        n
        for n, obj in data
        if n.startswith("_") or isinstance(obj, property) or callable(obj)
    ]
    if bad_names:
        return "Unexpected section names in project repr: {}".format(bad_names)


def check_subs_repr(p):
    """
    Validate subproject names representation in given Project's text repr.

    :param peppy.Project p: project instance to check
    :return str | NoneType: invalidation message if validation fails, else null
    """
    all_lines = _get_repr_lines(p)
    rel_lines = [l for l in all_lines if l.startswith("Subprojects")]
    subs = p.get(SUBPROJECTS_SECTION)
    if subs:
        names = list(subs.keys())
        if not rel_lines:
            return (
                "No subproject lines in project repr, but project has "
                "subprojects: {}".format(", ".join(names))
            )
        if len(rel_lines) != 1:
            return "Multiple subproject-related lines: {}".format(rel_lines)
        text = rel_lines[0]
        missing = [n for n in names if n not in text]
        if missing:
            return (
                "Missing subproject names from relevant repr line ({}): "
                "{}".format(text, missing)
            )
    elif rel_lines:
        return "Project lacks subprojects but has subproject lines in repr: {}".format(
            rel_lines
        )


def check_line_count(p):
    """
    Validate number of lines in given Project's text repr.

    :param peppy.Project p: project instance to check
    :return str | NoneType: invalidation message if validation fails, else null
    """
    names = list(p.sample_names)
    subs = p.get(SUBPROJECTS_SECTION)
    # Main message line, sections line, and possibly sample names and subprojects.
    exp_num_lines = 2 + int(bool(names)) + int(bool(subs))
    obs_lines = _get_repr_lines(p)
    if exp_num_lines != len(obs_lines):
        return "Expected {} repr lines but got {}: {}".format(
            exp_num_lines, len(obs_lines), obs_lines
        )


@pytest.mark.remote_data
class ProjectReprTests:
    """Tests for terminal representation of a project."""

    @pytest.fixture(scope="function")
    def proj_name(self, request):
        return request.getfixturevalue("example_peps").keys()

    @pytest.mark.parametrize(
        "invalidate",
        [check_line_count, check_subs_repr, check_sections_repr, check_samples_repr],
    )
    def test_project_repr(self, example_peps, invalidate):
        assert len(example_peps) > 0
        print(
            "Checking {} projects: {}".format(
                len(example_peps), ", ".join(example_peps.keys())
            )
        )
        fails = []
        for n, p in example_peps.items():
            try:
                err = invalidate(p)
            except Exception as e:
                err = str(e)
            if err:
                fails.append((n, err))
        if fails:
            pytest.fail("{} projects failed validation: {}".format(len(fails), fails))


def _determine_project_paths(data_root):
    """
    Map project name (subfolder) to config path, from root of examples projects.

    This function will initially interpret each folder immediately within the
    given root as a folder in which project config files are stored, and thus
    use that subfolder name as a name for a putative project. If extant, the
    path to project_config.yaml within that folder is bound (as value) to the
    subfolder/project name (as key).

    :param str data_root: path to folder in which some subfolders store
        project configuration data; the canonical instance is the root of the
        example_peps repository
    :return Mapping: binding between subfolder (project) name and path to
        configuration file
    :raise AssertionError: if the given data root path isn't a folder
    """
    assert os.path.isdir(data_root), "Data root path isn't a folder: {}".format(
        data_root
    )
    path = lambda sub: os.path.join(data_root, sub, "project_config.yaml")
    return {n: path(n) for n in os.listdir(data_root) if os.path.isfile(path(n))}


def _get_repr_lines(p):
    """Get lines from Project's __repr__"""
    return repr(p).split("\n")
