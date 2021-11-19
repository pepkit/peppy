import os
import tempfile

import pytest

from peppy import Project

__author__ = "Michal Stolarczyk"
__email__ = "michal.stolarczyk@nih.gov"

EXAMPLE_TYPES = [
    "basic",
    "derive",
    "imply",
    "append",
    "amendments1",
    "amendments2",
    "derive_imply",
    "duplicate",
    "imports",
    "subtable1",
    "subtable2",
    "subtable3",
    "subtable4",
    "subtable5",
    "remove",
]


class SampleTests:
    @pytest.mark.parametrize("example_pep_cfg_path", ["basic"], indirect=True)
    def test_serialization(self, example_pep_cfg_path):
        """
        Verify that Project object is successfully created for every example PEP
        """
        td = tempfile.mkdtemp()
        fn = os.path.join(td, "serialized_sample.yaml")
        p = Project(cfg=example_pep_cfg_path)
        sample = p.samples[0]
        sample.set = set(["set"])
        sample.dict = dict({"dict": "dict"})
        sample.list = list(["list"])
        sample.to_yaml(fn)
        with open(fn, "r") as f:
            contents = f.read()
        assert "set" in contents
        assert "dict" in contents
        assert "list" in contents

    @pytest.mark.parametrize("example_pep_cfg_path", EXAMPLE_TYPES, indirect=True)
    def test_str_repr_correctness(self, example_pep_cfg_path):
        """
        Verify that the missing amendment request raises correct exception
        """
        p = Project(cfg=example_pep_cfg_path)
        for sample in p.samples:
            str_repr = sample.__str__(max_attr=100)
            assert example_pep_cfg_path in str_repr
            assert "Sample '{}'".format(sample.sample_name) in str_repr

    @pytest.mark.parametrize("example_pep_cfg_path", ["basic"], indirect=True)
    def test_sheet_dict_excludes_private_attrs(self, example_pep_cfg_path):
        """
        Verify that sheet dict includes only original Sample attributes
        """
        p = Project(cfg=example_pep_cfg_path)
        for sample in p.samples:
            assert len(sample.get_sheet_dict()) == len(p.sample_table.columns)
