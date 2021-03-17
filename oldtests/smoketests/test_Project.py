""" Classes for peppy.Project testing """

import os

import pytest

from peppy import Project

__author__ = "Michal Stolarczyk"
__email__ = "michal@virginia.edu"


class ProjectConstructorTests:
    def test_empty(self):
        """ Verify that an empty Project instance can be created """
        p = Project()
        assert isinstance(p, "Project")
        assert len(p.samples) == 0

    def test_basic(self, example_data_path):
        cfg_pth = os.path.join(example_data_path, "example_basic")
        p = Project(cfg=cfg_pth)
        assert isinstance(p, "Project")

    def test_derive(self, example_data_path):
        cfg_pth = os.path.join(example_data_path, "example_derive")
        p = Project(cfg=cfg_pth)
        raise OSError("Test")
        assert isinstance(p, "Project")
