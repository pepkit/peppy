""" Tests for temporary contextualization of Project's Sample objects """

import pytest
import yaml  # TODO: remove once project can take raw config data?

from peppy import Project, ProjectContext, Sample
from peppy.const import *

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


ATAC_NAME = "atac-PE"
CHIP_NAME = "chip1"
RNA_NAME = "rna_PE"
WGBS_NAME = "wgbs-hs"
RRBS_NAME = "rrbs_mm"
ADD_PROJECT_DATA = {
    DATA_SOURCES_SECTION: {"src": "{sample}-{flowcell}.bam"},
    DERIVATIONS_DECLARATION: ["data_source"],
    PIPE_ARGS_SECTION: {"--epilog": None},
    IMPLICATIONS_DECLARATION: {"organism": "assembly"},
    "user": "test-user",
    "email": "tester@domain.org",
}


@pytest.fixture
def sample_names():
    return [ATAC_NAME, CHIP_NAME, RNA_NAME, WGBS_NAME, RRBS_NAME]


@pytest.fixture
def protocols():
    return ["ATAC", "CHIP", "RNA", "WGBS", "RRBS"]


@pytest.fixture
def samples(sample_names, protocols):
    return [
        Sample({SAMPLE_NAME_COLNAME: sn, "protocol": p})
        for sn, p in zip(sample_names, protocols)
    ]


@pytest.fixture
def sample_by_protocol(sample_names, protocols):
    return dict(zip(protocols, sample_names))


@pytest.fixture
def protocol_by_sample(sample_names, protocols):
    return dict(zip(sample_names, protocols))


@pytest.fixture
def project(request, sample_names, protocols, tmpdir):
    """
    Provide test case with a basic Project instance.

    The Sample data written to the annotation sheet file is determined
    by the sample_names and protocols fixures.

    :param pytest.fixtures.FixtureRequest request: test case requesting this
        basic Project fixture
    :param Iterable[str] sample_names: names of samples, to write to an
        annotations sheet file
    :param Iterable[str] protocols: name of protocol for each sample, also
        to be written to the annotations sheet file; the number of elements
        should match the number of sample names
    :param py._path.local.LocalPath tmpdir: temporary directory fixture
    :return Project: basic Project instance with files written, from the
        data provided by the fixtures
    """

    outdir = tmpdir.mkdir("output")
    metadir = tmpdir.mkdir(METADATA_KEY)

    # Write annotations file.
    anns_data = [(SAMPLE_NAME_COLNAME, "protocol")] + list(zip(sample_names, protocols))
    anns = metadir.join("anns.csv")
    anns.write("\n".join(["{},{}".format(sn, p) for sn, p in anns_data]))

    # Create config data.
    conf_data = {
        METADATA_KEY: {NAME_TABLE_ATTR: anns.strpath, OUTDIR_KEY: outdir.strpath}
    }
    # Provide a hook for a test case to add data.
    if "add_project_data" in request.fixturenames:
        conf_data.update(request.getfixturevalue("add_project_data"))

    # Write the config file.
    conf = metadir.join("conf.yaml")
    with open(conf.strpath, "w") as f:
        yaml.dump(conf_data, f)

    return Project(conf.strpath)


class ProjectContextTests:
    """Tests for Project context manager wrapper"""

    def test_no_filtration(self, samples, project):
        """With no selector_include/selector_exclude, all Sample objects are in play."""
        _assert_samples(samples, project.samples)
        with ProjectContext(project) as prj:
            _assert_samples(project.samples, prj.samples)

    @pytest.mark.parametrize(
        argnames=["selector_include", "expected_names"],
        argvalues=[
            ("ATAC", {"atac-PE"}),
            (("WGBS", "RRBS"), {WGBS_NAME, RRBS_NAME}),
            ({"RNA", "CHIP"}, {RNA_NAME, CHIP_NAME}),
        ],
    )
    def test_inclusion(self, samples, project, selector_include, expected_names):
        """Sample objects can be selected for by protocol."""
        _assert_samples(samples, project.samples)
        with ProjectContext(project, selector_include=selector_include) as prj:
            _assert_sample_names(expected_names, observed_samples=prj.samples)

    @pytest.mark.parametrize(
        argnames=["selector_exclude", "expected_names"],
        argvalues=[
            ({"RNA", "CHIP"}, {ATAC_NAME, WGBS_NAME, RRBS_NAME}),
            ("ATAC", {CHIP_NAME, RNA_NAME, WGBS_NAME, RRBS_NAME}),
            ({"WGBS", "RRBS"}, {ATAC_NAME, CHIP_NAME, RNA_NAME}),
        ],
    )
    def test_exclusion(self, samples, project, selector_exclude, expected_names):
        """Sample objects can be selected against by protocol."""
        _assert_samples(samples, project.samples)
        with ProjectContext(project, selector_exclude=selector_exclude) as prj:
            _assert_sample_names(expected_names, observed_samples=prj.samples)

    @pytest.mark.parametrize(
        argnames=["selection", "selection_type"],
        argvalues=[
            ({"CHIP", "WGBS", "RRBS"}, "selector_exclude"),
            ({"WGBS", "ATAC"}, "selector_include"),
        ],
        ids=lambda proto_seltype_pair: "{}:{}".format(*proto_seltype_pair),
    )
    def test_restoration(self, samples, project, selection, selection_type):
        """After exiting the context, original Project samples restore."""
        _assert_samples(samples, project.samples)
        with ProjectContext(project, **{selection_type: selection}) as prj:
            # Ensure that the context manager has changed something about
            # the collection of sample names.
            assert {s.name for s in prj.samples} != {s.name for s in samples}
        # Ensure the restoration of the original samples.
        _assert_samples(samples, project.samples)

    @pytest.mark.parametrize(argnames="add_project_data", argvalues=[ADD_PROJECT_DATA])
    @pytest.mark.parametrize(
        argnames="attr_name", argvalues=list(ADD_PROJECT_DATA.keys())
    )
    def test_access_to_project_attributes(self, project, add_project_data, attr_name):
        """Context manager routes attribute requests through Project."""
        # add_project_data is used by the project fixture.
        with ProjectContext(project) as prj:
            assert getattr(project, attr_name) is getattr(prj, attr_name)

    @pytest.mark.parametrize(
        argnames="attr_name", argvalues=["include", "exclude", "prj"]
    )
    def test_access_to_non_project_attributes(self, project, attr_name):
        """Certain attributes are on the context manager itself."""
        # add_project_data is used by the project fixture.
        with ProjectContext(project) as prj:
            # No selector_include/selector_exclude protocols --> those attributes are null.
            assert getattr(prj, attr_name) is (project if attr_name == "prj" else None)


def _assert_samples(expected_samples, observed_samples):
    """
    Make equality assertions on Sample count and names.

    :param Iterable[Sample] expected_samples: collection of expected Sample
        object instances
    :param Iterable[Sample] observed_samples: collection of observed Sample
        object instances
    """
    assert len(expected_samples) == len(observed_samples)
    assert all(
        map(
            lambda samples: samples[0].name == samples[1].name,
            zip(expected_samples, observed_samples),
        )
    )


def _assert_sample_names(expected_names, observed_samples):
    """
    Make equality assertions on Sample name and type.

    :param Iterable[str] expected_names: collection of expected Sample names
    :param Iterable[Sample] observed_samples: collection of observed Sample
        object instances
    """
    assert all(map(lambda s: isinstance(s, Sample), observed_samples))
    assert set(expected_names) == {s.name for s in observed_samples}
