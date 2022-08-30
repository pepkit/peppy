import pytest

from peppy.project import Project


class TestSampleModifiers:
    @pytest.mark.parametrize("example_pep_cfg_path", ["append"], indirect=True)
    def test_append(self, example_pep_cfg_path):
        """Verify that the appended attribute is added to the samples"""
        p = Project(cfg=example_pep_cfg_path)
        assert all([s["read_type"] == "SINGLE" for s in p.samples])

    @pytest.mark.parametrize("example_pep_cfg_path", ["imports"], indirect=True)
    def test_imports(self, example_pep_cfg_path):
        """Verify that the imported attribute is added to the samples"""
        p = Project(cfg=example_pep_cfg_path)
        assert all([s["imported_attr"] == "imported_val" for s in p.samples])

    @pytest.mark.parametrize("example_pep_cfg_path", ["imply"], indirect=True)
    def test_imply(self, example_pep_cfg_path):
        """
        Verify that the implied attribute is added to the correct samples
        """
        p = Project(cfg=example_pep_cfg_path)
        assert all(
            [s["genome"] == "hg38" for s in p.samples if s["organism"] == "human"]
        )
        assert all(
            [s["genome"] == "mm10" for s in p.samples if s["organism"] == "mouse"]
        )

    @pytest.mark.parametrize("example_pep_cfg_path", ["duplicate"], indirect=True)
    def test_duplicate(self, example_pep_cfg_path):
        """
        Verify that the duplicated attribute is identical to the original
        """
        p = Project(cfg=example_pep_cfg_path)
        assert all([s["organism"] == s["animal"] for s in p.samples])

    @pytest.mark.parametrize("example_pep_cfg_path", ["derive"], indirect=True)
    def test_derive(self, example_pep_cfg_path):
        """
        Verify that the declared attr derivation happened
        """
        p = Project(cfg=example_pep_cfg_path)
        assert all(["file_path" in s for s in p.samples])
        assert all(["file_path" in s["_derived_cols_done"] for s in p.samples])

    @pytest.mark.parametrize("example_pep_cfg_path", ["remove"], indirect=True)
    def test_remove(self, example_pep_cfg_path):
        """
        Verify that the declared attr was eliminated from every sample
        """
        p = Project(cfg=example_pep_cfg_path)
        assert all(["protocol" not in s for s in p.samples])

    @pytest.mark.parametrize("example_pep_cfg_path", ["subtable2"], indirect=True)
    def test_subtable(self, example_pep_cfg_path):
        """
        Verify that the sample merging takes place
        """
        p = Project(cfg=example_pep_cfg_path)
        assert all(
            [
                isinstance(s["file"], list)
                for s in p.samples
                if s["sample_name"] in ["frog_1", "frog2"]
            ]
        )
