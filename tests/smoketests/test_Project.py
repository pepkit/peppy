""" Classes for peppy.Project smoketesting """

from peppy import Project
from peppy.exceptions import MissingAmendmentError
from pandas import DataFrame
import pytest
import os

__author__ = "Michal Stolarczyk"
__email__ = "michal@virginia.edu"

EXAMPLE_TYPES = \
    ["basic", "derive", "imply", "append", "amendments1", "amendments2",
     "derive_imply", "duplicate", "imports", "subtable1", "subtable2",
     "subtable3", "subtable4", "subtable5", "remove"]


class ProjectConstructorTests:
    def test_empty(self):
        """ Verify that an empty Project instance can be created """
        p = Project()
        assert isinstance(p, Project)
        assert len(p.samples) == 0

    @pytest.mark.parametrize('example_pep_cfg_path', EXAMPLE_TYPES, indirect=True)
    def test_instantiaion(self, example_pep_cfg_path):
        """
        Verify that Project object is successfully created for every example PEP
        """
        p = Project(cfg=example_pep_cfg_path)
        assert isinstance(p, Project)

    @pytest.mark.parametrize('example_pep_cfg_path', ["amendments1"], indirect=True)
    def test_amendments(self, example_pep_cfg_path):
        """
        Verify that the amendment is activate at object instantiation
        """
        p = Project(cfg=example_pep_cfg_path, amendments="newLib")
        assert all([s["protocol"] == "ABCD" for s in p.samples])

    @pytest.mark.parametrize('example_pep_cfg_path', ["old"], indirect=True)
    def test_old_format_support(self, example_pep_cfg_path):
        """
        Verify that old format (without implications and subprojects)
        is still supported
        """
        os.environ["DATA"] = "data"
        p = Project(cfg=example_pep_cfg_path)
        assert all(["read1" in s for s in p.samples])

    @pytest.mark.parametrize('example_pep_cfg_path', ["subtable1"], indirect=True)
    def test_subsample_table_works_when_no_sample_mods(self, example_pep_cfg_path):
        """
        Verify that subsample table functionality is not
        dependant on sample modifiers
        """
        p = Project(cfg=example_pep_cfg_path)
        assert any([s["file"] != "multi" for s in p.samples])


class ProjectManipulationTests:
    @pytest.mark.parametrize('example_pep_cfg_path', ["amendments1"], indirect=True)
    def test_amendments_activation_interactive(self, example_pep_cfg_path):
        """
        Verify that the amendment can be activated interactively
        """
        p = Project(cfg=example_pep_cfg_path)
        p.activate_amendments("newLib")
        assert all([s["protocol"] == "ABCD" for s in p.samples])
        assert p.amendments is not None

    @pytest.mark.parametrize('example_pep_cfg_path', ["amendments1"], indirect=True)
    def test_amendments_deactivation_interactive(self, example_pep_cfg_path):
        """
        Verify that the amendment can be activated interactively
        """
        p = Project(cfg=example_pep_cfg_path)
        p.deactivate_amendments()
        assert all([s["protocol"] != "ABCD" for s in p.samples])
        p.activate_amendments("newLib")
        p.deactivate_amendments()
        assert all([s["protocol"] != "ABCD" for s in p.samples])
        assert p.amendments is None

    @pytest.mark.parametrize('example_pep_cfg_path', ["amendments1"], indirect=True)
    def test_missing_amendment_raises_error(self, example_pep_cfg_path):
        """
        Verify that the missing amendment request raises correct exception
        """
        with pytest.raises(MissingAmendmentError):
            Project(cfg=example_pep_cfg_path, amendments="nieznany")

    @pytest.mark.parametrize('example_pep_cfg_path', ["amendments1"], indirect=True)
    def test_missing_amendment_raises_error(self, example_pep_cfg_path):
        """
        Verify that the missing amendment request raises correct exception
        """
        with pytest.raises(MissingAmendmentError):
            Project(cfg=example_pep_cfg_path, amendments="nieznany")

    @pytest.mark.parametrize('example_pep_cfg_path', EXAMPLE_TYPES, indirect=True)
    def test_str_repr_correctness(self, example_pep_cfg_path):
        """
        Verify that the missing amendment request raises correct exception
        """
        p = Project(cfg=example_pep_cfg_path)
        str_repr = p.__str__()
        assert example_pep_cfg_path in str_repr
        assert "{} samples".format(str(len(p.samples))) in str_repr
        assert p.name in str_repr

    @pytest.mark.parametrize('example_pep_cfg_path', ["amendments1"], indirect=True)
    def test_amendments_listing(self, example_pep_cfg_path):
        """
        Verify that the missing amendment request raises correct exception
        """
        p = Project(cfg=example_pep_cfg_path)
        assert isinstance(p.list_amendments, list)

    @pytest.mark.parametrize('example_pep_cfg_path', ["basic"], indirect=True)
    def test_sample_updates_regenerate_df(self, example_pep_cfg_path):
        """
        Verify that Sample modifications cause sample_table regeneration
        """
        p = Project(cfg=example_pep_cfg_path)
        s_ori = p.sample_table
        p.samples[0].update({"witam": "i_o_zdrowie_pytam"})
        assert not p.sample_table.equals(s_ori)

    @pytest.mark.parametrize('example_pep_cfg_path', ["subtable1"], indirect=True)
    def test_subsample_table_property(self, example_pep_cfg_path):
        """
        Verify that Sample modifications cause sample_table regeneration
        """
        p = Project(cfg=example_pep_cfg_path)
        assert isinstance(p.subsample_table, DataFrame)


class SampleModifiersTests:
    @pytest.mark.parametrize('example_pep_cfg_path', ["append"], indirect=True)
    def test_append(self, example_pep_cfg_path):
        """ Verify that the appended attribute is added to the samples """
        p = Project(cfg=example_pep_cfg_path)
        assert all([s["read_type"] == "SINGLE" for s in p.samples])

    @pytest.mark.parametrize('example_pep_cfg_path', ["imports"], indirect=True)
    def test_imports(self, example_pep_cfg_path):
        """ Verify that the imported attribute is added to the samples """
        p = Project(cfg=example_pep_cfg_path)
        assert all([s["imported_attr"] == "imported_val" for s in p.samples])

    @pytest.mark.parametrize('example_pep_cfg_path', ["imply"], indirect=True)
    def test_imply(self, example_pep_cfg_path):
        """
        Verify that the implied attribute is added to the correct samples
        """
        p = Project(cfg=example_pep_cfg_path)
        assert all([s["genome"] == "hg38" for s in p.samples if
                    s["organism"] == "human"])
        assert all([s["genome"] == "mm10" for s in p.samples if
                    s["organism"] == "mouse"])

    @pytest.mark.parametrize('example_pep_cfg_path', ["duplicate"], indirect=True)
    def test_duplicate(self, example_pep_cfg_path):
        """
        Verify that the duplicated attribute is identical to the original
        """
        p = Project(cfg=example_pep_cfg_path)
        assert all([s["organism"] == s["animal"] for s in p.samples])

    @pytest.mark.parametrize('example_pep_cfg_path', ["derive"], indirect=True)
    def test_derive(self, example_pep_cfg_path):
        """
        Verify that the declared attr derivation happened
        """
        p = Project(cfg=example_pep_cfg_path)
        assert all(["file_path" in s for s in p.samples])
        assert all(["file_path" in s["_derived_cols_done"] for s in p.samples])

    @pytest.mark.parametrize('example_pep_cfg_path', ["remove"], indirect=True)
    def test_remove(self, example_pep_cfg_path):
        """
        Verify that the declared attr was eliminated from every sample
        """
        p = Project(cfg=example_pep_cfg_path)
        assert all(["protocol" not in s for s in p.samples])

    @pytest.mark.parametrize('example_pep_cfg_path', ["subtable2"], indirect=True)
    def test_subtable(self, example_pep_cfg_path):
        """
        Verify that the sample merging takes place
        """
        p = Project(cfg=example_pep_cfg_path)
        assert all([isinstance(s["file"], list) for s in p.samples
                    if s["sample_name"] in ["frog_1", "frog2"]])
