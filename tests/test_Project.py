""" Classes for peppy.Project smoketesting """

import os
import socket
import tempfile

import numpy as np
import pytest
from pandas import DataFrame
from yaml import dump, safe_load

from peppy import Project
from peppy.const import SAMPLE_NAME_ATTR, SAMPLE_TABLE_FILE_KEY
from peppy.exceptions import (
    IllegalStateException,
    InvalidSampleTableFileException,
    MissingAmendmentError,
    RemoteYAMLError,
)

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


def _get_pair_to_post_init_test(cfg_path):
    """

    :param cfg_path: path to the project config file
    :type cfg_path: str
    :return: list of two project objects to compare
    :rtype: list[peppy.Project]
    """
    p = Project(cfg=cfg_path)
    pd = Project(cfg=cfg_path, defer_samples_creation=True)
    pd.create_samples(modify=False if pd[SAMPLE_TABLE_FILE_KEY] is not None else True)
    return [p, pd]


def _cmp_all_samples_attr(p1, p2, attr):
    """
    Compare a selected attribute values for all samples in two Projects

    :param p1: project to comapre
    :type p1: peppy.Project
    :param p2: project to comapre
    :type p2: peppy.Project
    :param attr: attribute name to compare
    :type attr: str
    """

    assert [getattr(s, attr, None) for s in p1.samples] == [
        getattr(s, attr, None) for s in p2.samples
    ]


class TestProjectConstructor:
    def test_empty(self):
        """Verify that an empty Project instance can be created"""
        p = Project()
        assert isinstance(p, Project)
        assert len(p.samples) == 0

    def test_nonexistent(self):
        """Verify that OSError is thrown when config does not exist"""
        with pytest.raises(OSError):
            Project(cfg="nonexistentfile.yaml")

    @pytest.mark.parametrize("defer", [False, True])
    @pytest.mark.parametrize("example_pep_cfg_path", EXAMPLE_TYPES, indirect=True)
    def test_instantiaion(self, example_pep_cfg_path, defer):
        """
        Verify that Project object is successfully created for every example PEP
        """
        p = Project(cfg=example_pep_cfg_path, defer_samples_creation=defer)
        assert isinstance(p, Project)

    @pytest.mark.parametrize(
        "config_path",
        [
            "https://raw.githubusercontent.com/pepkit/example_peps/master/example_basic/project_config.yaml",
            "https://raw.githubusercontent.com/pepkit/example_peps/master/example_derive/project_config.yaml",
            "https://raw.githubusercontent.com/pepkit/example_peps/master/example_imply/project_config.yaml",
            "https://raw.githubusercontent.com/pepkit/example_peps/master/example_imports/project_config.yaml",
        ],
    )
    def test_remote(self, config_path):
        """
        Verify that remote project configs are supported
        """
        p = Project(cfg=config_path)
        assert isinstance(p, Project)

    @pytest.mark.parametrize(
        "config_path",
        [
            "https://raw.githubusercontent.com/pepkit/example_peps/master/example_basic/project_config.yaml",
            "https://raw.githubusercontent.com/pepkit/example_peps/master/example_derive/project_config.yaml",
            "https://raw.githubusercontent.com/pepkit/example_peps/master/example_imply/project_config.yaml",
            "https://raw.githubusercontent.com/pepkit/example_peps/master/example_imports/project_config.yaml",
        ],
    )
    def test_remote_simulate_no_network(self, config_path):
        """
        Verify correctness of the remote config reading behavior with no network
        """

        def guard(*args, **kwargs):
            raise Exception("Block internet connection")

        ori_socket_val = socket.socket
        socket.socket = guard
        with pytest.raises(RemoteYAMLError):
            Project(cfg=config_path)
        socket.socket = ori_socket_val

    @pytest.mark.parametrize("example_pep_cfg_path", ["basic", "imply"], indirect=True)
    def test_csv_init_autodetect(self, example_pep_cfg_path):
        """
        Verify that a CSV file can be used to initialize a config file
        """
        assert isinstance(Project(cfg=example_pep_cfg_path), Project)

    @pytest.mark.parametrize(
        "csv_path",
        [
            "https://raw.githubusercontent.com/pepkit/example_peps/master/example_basic/sample_table.csv",
            "https://raw.githubusercontent.com/pepkit/example_peps/master/example_imply/sample_table.csv",
        ],
    )
    def test_remote_csv_init_autodetect(self, csv_path):
        """
        Verify that a remote CSV file can be used to initialize a config file
        """
        assert isinstance(Project(cfg=csv_path), Project)

    @pytest.mark.parametrize("example_pep_cfg_path", ["automerge"], indirect=True)
    def test_automerge(self, example_pep_cfg_path):
        """
        Verify that duplicated sample names lead to sample auto-merging
        """
        p = Project(cfg=example_pep_cfg_path)
        # there are 4 rows in the table, but 1 sample has a duplicate
        assert len(p.samples) == 3

    @pytest.mark.parametrize("example_pep_csv_path", ["automerge"], indirect=True)
    def test_automerge_csv(self, example_pep_csv_path):
        """
        Verify that duplicated sample names lead to sample auto-merging if object is initialized from a CSV
        """
        p = Project(cfg=example_pep_csv_path)
        # there are 4 rows in the table, but 1 sample has a duplicate
        assert len(p.samples) == 3

    @pytest.mark.parametrize(
        "config_path",
        [
            "https://raw.githubusercontent.com/pepkit/example_peps/master/example_automerge/project_config.yaml",
        ],
    )
    def test_automerge_remote(self, config_path):
        """
        Verify that duplicated sample names lead to sample auto-merging from a remote config
        """
        p = Project(cfg=config_path)
        # there are 4 rows in the table, but 1 sample has a duplicate
        assert len(p.samples) == 3

    @pytest.mark.parametrize(
        "example_pep_cfg_path", ["subtable_automerge"], indirect=True
    )
    def test_automerge_disallowed_with_subsamples(self, example_pep_cfg_path):
        """
        Verify that both duplicated sample names and subsample table specification is disallowed
        """
        with pytest.raises(IllegalStateException):
            Project(cfg=example_pep_cfg_path)

    @pytest.mark.parametrize("defer", [False, True])
    @pytest.mark.parametrize("example_pep_cfg_path", ["amendments1"], indirect=True)
    def test_amendments(self, example_pep_cfg_path, defer):
        """
        Verify that the amendment is activate at object instantiation
        """
        p = Project(
            cfg=example_pep_cfg_path, amendments="newLib", defer_samples_creation=defer
        )
        assert all([s["protocol"] == "ABCD" for s in p.samples])

    @pytest.mark.parametrize("example_pep_cfg_path", ["subtable1"], indirect=True)
    def test_subsample_table_works_when_no_sample_mods(self, example_pep_cfg_path):
        """
        Verify that subsample table functionality is not
        dependant on sample modifiers
        """
        p = Project(cfg=example_pep_cfg_path)
        assert any([s["file"] != "multi" for s in p.samples])

    @pytest.mark.parametrize("example_pep_cfg_path", ["custom_index"], indirect=True)
    def test_cutsom_sample_table_index_config(self, example_pep_cfg_path):
        """
        Verify that custom sample table index is sourced from the config
        """
        Project(cfg=example_pep_cfg_path)

    @pytest.mark.parametrize("example_pep_cfg_path", ["custom_index"], indirect=True)
    def test_cutsom_sample_table_index_constructor(self, example_pep_cfg_path):
        """
        Verify that custom sample table index is sourced from the config
        """
        with pytest.raises(InvalidSampleTableFileException):
            Project(cfg=example_pep_cfg_path, sample_table_index="bogus_column")

    @pytest.mark.parametrize("example_pep_cfg_path", ["subtables"], indirect=True)
    def test_subsample_table_multiple(self, example_pep_cfg_path):
        """
        Verify that subsample table functionality in multi subsample context
        """
        p = Project(cfg=example_pep_cfg_path)
        assert any(["desc" in s for s in p.samples])

    @pytest.mark.parametrize("defer", [False, True])
    @pytest.mark.parametrize("example_pep_cfg_path", EXAMPLE_TYPES, indirect=True)
    def test_no_description(self, example_pep_cfg_path, defer):
        """
        Verify that Project object is successfully created when no description
         is specified in the config
        """
        p = Project(cfg=example_pep_cfg_path, defer_samples_creation=defer)
        assert isinstance(p, Project)
        assert "description" in p and p.description is None

    @pytest.mark.parametrize("defer", [False, True])
    @pytest.mark.parametrize("desc", ["desc1", "desc 2 <test> 123$!@#;11", 11, None])
    @pytest.mark.parametrize("example_pep_cfg_path", EXAMPLE_TYPES, indirect=True)
    def test_description(self, example_pep_cfg_path, desc, defer):
        """
        Verify that Project object contains description specified in the config
        """
        td = tempfile.mkdtemp()
        temp_path_cfg = os.path.join(td, "config.yaml")
        with open(example_pep_cfg_path, "r") as f:
            data = safe_load(f)
        data["description"] = desc
        del data["sample_table"]
        with open(temp_path_cfg, "w") as f:
            dump(data, f)
        p = Project(cfg=temp_path_cfg, defer_samples_creation=defer)
        assert isinstance(p, Project)
        assert "description" in p and p.description == str(desc)

    @pytest.mark.parametrize(
        "example_pep_cfg_noname_path", ["project_config.yaml"], indirect=True
    )
    def test_missing_sample_name_derive(self, example_pep_cfg_noname_path):
        """
        Verify that even if sample_name column is missing in the sample table,
        it can be derived and no error is issued
        """
        p = Project(cfg=example_pep_cfg_noname_path)
        assert SAMPLE_NAME_ATTR in p.sample_table.columns

    @pytest.mark.parametrize(
        "example_pep_cfg_noname_path", ["project_config_noname.yaml"], indirect=True
    )
    def test_missing_sample_name(self, example_pep_cfg_noname_path):
        """
        Verify that if sample_name column is missing in the sample table an
        error is issued
        """
        with pytest.raises(InvalidSampleTableFileException):
            Project(cfg=example_pep_cfg_noname_path)

    @pytest.mark.parametrize(
        "example_pep_cfg_noname_path", ["project_config_noname.yaml"], indirect=True
    )
    def test_missing_sample_name_defer(self, example_pep_cfg_noname_path):
        """
        Verify that if sample_name column is missing in the sample table an
        error is not issued if sample creation is deferred
        """
        Project(cfg=example_pep_cfg_noname_path, defer_samples_creation=True)

    @pytest.mark.parametrize(
        "example_pep_cfg_noname_path", ["project_config_noname.yaml"], indirect=True
    )
    def test_missing_sample_name_custom_index(self, example_pep_cfg_noname_path):
        """
        Verify that if sample_name column is missing in the sample table an
        error is not issued if a custom sample_table index is set
        """
        p = Project(cfg=example_pep_cfg_noname_path, sample_table_index="id")
        assert p.sample_name_colname == "id"

    @pytest.mark.parametrize(
        "example_pep_cfg_path",
        ["basic"],
        indirect=True,
    )
    def test_equality(self, example_pep_cfg_path):
        p1 = Project(cfg=example_pep_cfg_path)
        p2 = Project(cfg=example_pep_cfg_path)

        assert p1 == p2

    @pytest.mark.parametrize(
        "example_peps_cfg_paths", [["basic", "BiocProject"]], indirect=True
    )
    def test_inequality(self, example_peps_cfg_paths):
        cfg1, cfg2 = example_peps_cfg_paths
        p1 = Project(cfg=cfg1)
        p2 = Project(cfg=cfg2)
        assert p1 != p2

    @pytest.mark.parametrize("example_pep_cfg_path", EXAMPLE_TYPES, indirect=True)
    def test_from_dict_instatiation(self, example_pep_cfg_path):
        """
        Verify that we can accurately instiate a project from its dictionary
        representation.
        """
        p1 = Project(cfg=example_pep_cfg_path)
        p2 = Project().from_dict(p1.to_dict(extended=True))
        assert p1 == p2

    def test_to_dict_does_not_create_nans(self, example_pep_nextflow_csv_path):
        wrong_values = ["NaN", np.nan, "nan"]

        p1 = Project(
            cfg=example_pep_nextflow_csv_path, sample_table_index="sample"
        ).to_dict()
        for sample in p1.get("_samples"):
            for attribute, value in sample.items():
                assert value not in wrong_values

    @pytest.mark.parametrize("example_pep_cfg_path", ["missing_version"], indirect=True)
    def test_missing_version(self, example_pep_cfg_path):
        """
        Verify that peppy can load a config file with no pep version
        """
        p = Project(cfg=example_pep_cfg_path)
        assert isinstance(p.pep_version, str)

    @pytest.mark.parametrize("example_pep_csv_path", ["basic"], indirect=True)
    def test_sample_table_version(self, example_pep_csv_path):
        """
        Verify that peppy can load a config file with no pep version
        """
        p = Project(cfg=example_pep_csv_path)
        assert isinstance(p.pep_version, str)

    @pytest.mark.parametrize(
        "example_pep_csv_path", ["nextflow_samplesheet"], indirect=True
    )
    def test_auto_merge_duplicated_names_works_for_different_read_types(
        self, example_pep_csv_path
    ):
        p = Project(example_pep_csv_path, sample_table_index="sample")
        assert len(p.samples) == 4

    @pytest.mark.parametrize(
        "expected_attribute",
        [
            "sample",
            "instrument_platform",
            "run_accession",
            "fastq_1",
            "fastq_2",
            "fasta",
        ],
    )
    @pytest.mark.parametrize("example_pep_cfg_path", ["nextflow_config"], indirect=True)
    def test_peppy_initializes_samples_with_correct_attributes(
        self, example_pep_cfg_path, expected_attribute
    ):
        p = Project(example_pep_cfg_path, sample_table_index="sample")
        assert all([hasattr(sample, expected_attribute) for sample in p.samples])


class TestProjectManipulationTests:
    @pytest.mark.parametrize("example_pep_cfg_path", ["amendments1"], indirect=True)
    def test_amendments_activation_interactive(self, example_pep_cfg_path):
        """
        Verify that the amendment can be activated interactively
        """
        p = Project(cfg=example_pep_cfg_path)
        p.activate_amendments("newLib")
        assert all([s["protocol"] == "ABCD" for s in p.samples])
        assert p.amendments is not None

    @pytest.mark.parametrize("example_pep_cfg_path", ["amendments1"], indirect=True)
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

    @pytest.mark.parametrize("defer", [False, True])
    @pytest.mark.parametrize("example_pep_cfg_path", ["amendments1"], indirect=True)
    def test_missing_amendment_raises_correct_exception(
        self, example_pep_cfg_path, defer
    ):
        with pytest.raises(MissingAmendmentError):
            Project(
                cfg=example_pep_cfg_path,
                amendments="nieznany",
                defer_samples_creation=defer,
            )

    @pytest.mark.parametrize("defer", [False, True])
    @pytest.mark.parametrize("example_pep_cfg_path", ["amendments1"], indirect=True)
    def test_amendments_argument_cant_be_null(self, example_pep_cfg_path, defer):
        p = Project(cfg=example_pep_cfg_path, defer_samples_creation=defer)
        with pytest.raises(TypeError):
            p.activate_amendments(amendments=None)

    @pytest.mark.parametrize("defer", [False, True])
    @pytest.mark.parametrize("example_pep_cfg_path", EXAMPLE_TYPES, indirect=True)
    def test_str_repr_correctness(self, example_pep_cfg_path, defer):
        """
        Verify string representation correctness
        """
        p = Project(cfg=example_pep_cfg_path, defer_samples_creation=defer)
        str_repr = p.__str__()
        assert example_pep_cfg_path in str_repr
        assert "{} samples".format(str(len(p.samples))) in str_repr
        assert p.name in str_repr

    @pytest.mark.parametrize("defer", [False, True])
    @pytest.mark.parametrize("example_pep_cfg_path", ["amendments1"], indirect=True)
    def test_amendments_listing(self, example_pep_cfg_path, defer):
        p = Project(cfg=example_pep_cfg_path, defer_samples_creation=defer)
        assert isinstance(p.list_amendments, list)

    @pytest.mark.parametrize("example_pep_cfg_path", ["basic"], indirect=True)
    def test_sample_updates_regenerate_df(self, example_pep_cfg_path):
        """
        Verify that Sample modifications cause sample_table regeneration
        """
        p = Project(cfg=example_pep_cfg_path)
        s_ori = p.sample_table
        p.samples[0].update({"witam": "i_o_zdrowie_pytam"})
        assert not p.sample_table.equals(s_ori)

    @pytest.mark.parametrize("example_pep_cfg_path", ["subtable1"], indirect=True)
    def test_subsample_table_property(self, example_pep_cfg_path):
        """
        Verify that Sample modifications cause sample_table regeneration
        """
        p = Project(cfg=example_pep_cfg_path)
        assert isinstance(p.subsample_table, DataFrame) or isinstance(
            p.subsample_table, list
        )

    @pytest.mark.parametrize("example_pep_cfg_path", ["basic"], indirect=True)
    def test_get_sample(self, example_pep_cfg_path):
        """Verify that sample getting method works"""
        p = Project(cfg=example_pep_cfg_path)
        p.get_sample(sample_name=p.samples[0]["sample_name"])

    @pytest.mark.parametrize("example_pep_cfg_path", ["basic"], indirect=True)
    def test_get_sample_nonexistent(self, example_pep_cfg_path):
        """Verify that sample getting returns ValueError if not sample found"""
        p = Project(cfg=example_pep_cfg_path)
        with pytest.raises(ValueError):

            p.get_sample(sample_name="kdkdkdk")


class TestPostInitSampleCreation:
    @pytest.mark.parametrize("example_pep_cfg_path", ["append"], indirect=True)
    def test_append(self, example_pep_cfg_path):
        """
        Verify that the appending works the same way in a post init
        sample creation scenario
        """
        p, pd = _get_pair_to_post_init_test(example_pep_cfg_path)
        _cmp_all_samples_attr(p, pd, "read_type")

    @pytest.mark.parametrize("example_pep_cfg_path", ["imports"], indirect=True)
    def test_imports(self, example_pep_cfg_path):
        """
        Verify that the importing works the same way in a post init
        sample creation scenario
        """
        p, pd = _get_pair_to_post_init_test(example_pep_cfg_path)
        _cmp_all_samples_attr(p, pd, "imported_attr")

    @pytest.mark.parametrize("example_pep_cfg_path", ["imply"], indirect=True)
    def test_imply(self, example_pep_cfg_path):
        """
        Verify that the implication the same way in a post init
        sample creation scenario
        """
        p, pd = _get_pair_to_post_init_test(example_pep_cfg_path)
        _cmp_all_samples_attr(p, pd, "genome")

    @pytest.mark.parametrize("example_pep_cfg_path", ["duplicate"], indirect=True)
    def test_duplicate(self, example_pep_cfg_path):
        """
        Verify that the duplication the same way in a post init
        sample creation scenario
        """
        p, pd = _get_pair_to_post_init_test(example_pep_cfg_path)
        _cmp_all_samples_attr(p, pd, "organism")

    @pytest.mark.parametrize("example_pep_cfg_path", ["derive"], indirect=True)
    def test_derive(self, example_pep_cfg_path):
        """
        Verify that the derivation the same way in a post init
        sample creation scenario
        """
        p, pd = _get_pair_to_post_init_test(example_pep_cfg_path)
        _cmp_all_samples_attr(p, pd, "file_path")

    @pytest.mark.parametrize("example_pep_cfg_path", ["append"], indirect=True)
    def test_equality(self, example_pep_cfg_path):
        """
        Test equality function of two projects
        """
        p1 = Project(cfg=example_pep_cfg_path)
        p2 = Project(cfg=example_pep_cfg_path)
        assert p1 == p2

    @pytest.mark.parametrize("example_pep_cfg_path", ["append"], indirect=True)
    @pytest.mark.parametrize("example_pep_csv_path", ["derive"], indirect=True)
    def test_unequality(self, example_pep_cfg_path, example_pep_csv_path):
        """
        Test equality function of two projects
        """
        p1 = Project(cfg=example_pep_cfg_path)
        p2 = Project(cfg=example_pep_csv_path)
        assert not p1 == p2

    @pytest.mark.parametrize("example_pep_cfg_path", ["append"], indirect=True)
    def test_from_dict(self, example_pep_cfg_path):
        """
        Test initializing project from dict
        """
        p1 = Project(cfg=example_pep_cfg_path)
        p1_dict = p1.to_dict(extended=True)
        del p1_dict["_config"]["sample_table"]
        p2 = Project().from_dict(p1_dict)
        assert p1 == p2

    @pytest.mark.parametrize("config_with_pandas_obj", ["append"], indirect=True)
    @pytest.mark.parametrize("example_pep_csv_path", ["append"], indirect=True)
    def test_from_pandas(self, config_with_pandas_obj, example_pep_csv_path):
        """
        Test initializing project from dict
        """
        p1 = Project().from_pandas(config_with_pandas_obj)
        p2 = Project(example_pep_csv_path)

        assert p1 == p2
