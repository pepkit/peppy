""" Tests for fetching Samples of certain attributes values from a Project """

from collections import defaultdict
import itertools
import os

import mock
import pytest
import yaml

from peppy import Project, Sample
from peppy.const import *
from peppy.utils import fetch_samples


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



PROTOCOL_BY_SAMPLE = {
    sample_name: protocol for sample_name, protocol in [
        ("atac_A", "ATAC-Seq"), ("atac_B", "ATAC-Seq"),
        ("chip1", "ChIP-Seq"), ("WGBS-1", "WGBS"), ("RRBS-1", "RRBS"),
        ("rna_SE", "RNA-seq"), ("rna_PE", "RNA-seq")]
}
BASIC_PROTOCOL_NAMES = set(PROTOCOL_BY_SAMPLE.values())


def _group_samples_by_protocol():
    """ Invert mapping from protocol name to sample name.

    :return Mapping[str, list[str]]: sample names by protocol name
    """
    name_by_protocol = defaultdict(list)
    for sn, p in PROTOCOL_BY_SAMPLE.items():
        name_by_protocol[p].append(sn)
    return name_by_protocol


@pytest.fixture
def expected_sample_names(request):
    """
    Generate expected sample names for a test case's fetch_samples() call.

    Use the test case's fixture regarding protocol names to determine which
    protocols for which to grab sample names.

    :param pytest.fixtures.FixtureRequest request: test case requesting fixture
    :return set[str]: collection of sample names associated with either the
        test cases's protocol names (selector_include) or not associated with them
        (selector_exclude)
    """
    names_by_protocol = _group_samples_by_protocol()
    if "selector_include" in request.fixturenames:
        prot_spec = request.getfixturevalue("selector_include")
    elif "selector_exclude" in request.fixturenames:
        prot_spec = request.getfixturevalue("selector_exclude")
    else:
        raise ValueError(
            "Test case lacks either 'selector_include' and 'selector_exclude' fixtures, "
            "so no sample names can be generated; "
            "it should have one or the other.")
    if isinstance(prot_spec, str):
        prot_spec = [prot_spec]
    prot_spec = set(prot_spec)
    protocols = prot_spec if "selector_include" in request.fixturenames \
            else BASIC_PROTOCOL_NAMES - prot_spec
    print("Protocols generating expectations: {}".format(protocols))
    return itertools.chain.from_iterable(
            names_by_protocol[p] for p in protocols)


@pytest.fixture
def samples():
    """
    Create collection of Samples, useful for mocking a Project.

    :return Iterable[Sample]: collection of bare bones Sample objects, with
        only name and protocol defined
    """
    return [Sample({SAMPLE_NAME_COLNAME: sn, "protocol": p})
            for sn, p in PROTOCOL_BY_SAMPLE.items()]


def _write_project_files(tmpdir, all_samples, sp_samples, sp_name):
    """
    Write key project files.

    :param py._path.local.LocalPath tmpdir: tmpdir fixture from test case
    :param Iterable[Sample] all_samples: collection of samples for the
        main Project sample annotations
    :param Iterable[Sample] sp_samples: collection of samples for the
        subproject
    :return str: Project config file
    """

    # Parse name and protocol from actual Sample objects.
    def sample_data(samples):
        return [(s.sample_name, getattr(s, "protocol", "")) for s in samples]

    def write_anns(fh, samples):
        fh.write("\n".join(map(
            lambda name_proto_pair: "{},{}".format(*name_proto_pair),
            [(SAMPLE_NAME_COLNAME, "protocol")] + sample_data(samples))))

    # Create paths.
    metadir = tmpdir.mkdir(METADATA_KEY)

    # Write annotations
    full_anns = metadir.join("anns.csv")
    write_anns(full_anns, all_samples)
    sp_anns = metadir.join("sp-anns.csv")
    write_anns(sp_anns, sp_samples)

    # So that parsing pipeline interfaces is skipped, don't create pipedir.
    pipe_path = os.path.join(tmpdir.strpath, "pipelines")
    outdir = tmpdir.mkdir("output")

    conf_data = {
        METADATA_KEY: {
            NAME_TABLE_ATTR: full_anns.strpath, OUTDIR_KEY: outdir.strpath,
            "pipeline_interfaces": pipe_path},
        "subprojects": {sp_name: {
            METADATA_KEY: {NAME_TABLE_ATTR: sp_anns.strpath}}}
    }

    conf = metadir.join("conf.yaml")
    with open(conf.strpath, 'w') as f:
        yaml.dump(conf_data, f)

    return conf.strpath


@pytest.mark.parametrize(
    argnames=["selector_attribute", "selector_exclude"],
    argvalues=[("faulty_attr", "RNA-Seq"), ("faulty_attr", "RRBS")])
def test_has_attribute(selector_attribute, selector_exclude, samples):
    """ At least one of the samples has to have the specified selector_attribute. """
    prj = mock.MagicMock(samples=samples)
    with pytest.raises(AttributeError):
        fetch_samples(prj, selector_attribute=selector_attribute, selector_exclude=selector_exclude)


@pytest.mark.parametrize(
    argnames=["selector_attribute", "selector_include", "selector_exclude"],
    argvalues=itertools.product(
        ["protocol"], ["ATAC-Seq", "ChIPmentation", {"RNA-Seq", "ChIP"}],
        ["WGBS", {"WGBS", "RRBS"}]))
def test_only_inclusion_or_exclusion(selector_attribute, selector_include, selector_exclude, samples):
    """ Only an selector_include or selector_exclude set is permitted. """
    prj = mock.MagicMock(samples=samples)
    with pytest.raises(TypeError):
        fetch_samples(prj, selector_attribute,
            selector_include=selector_include, selector_exclude=selector_exclude)


@pytest.mark.parametrize(
    argnames=["selector_attribute", "selector_include", "selector_exclude"],
    argvalues=[
        ("protocol", "ATAC-Seq", None), ("protocol", {"ChIPmentation", "RNA-Seq"}, None),
        ("protocol", None, "ChIP-Seq"), ("protocol", None, {"ATAC-Seq", "ChIPmentation"})])
def test_no_samples(selector_attribute, selector_include, selector_exclude):
    """ Regardless of filtration, lack of samples means empty collection. """
    prj = mock.MagicMock(samples=[])
    observed = fetch_samples(prj, selector_attribute=selector_attribute,
        selector_include=selector_include, selector_exclude=selector_exclude)
    assert [] == observed


@pytest.mark.parametrize(
    argnames=["selector_attribute", "selector_include", "selector_exclude"],
    argvalues=[(None, None, None), (None, None, {}), (None, [], None), (None, [], [])])
def test_no_filter(selector_attribute, selector_include, selector_exclude, samples):
    """ Without a filtration mechanism, all Samples are retained. """
    prj = mock.MagicMock(samples=samples)
    assert samples == fetch_samples(prj, selector_attribute=selector_attribute,
        selector_include=selector_include, selector_exclude=selector_exclude)


class ProtocolInclusionTests:
    """ Samples can be selected for by protocol. """

    # Note that even if the vary_protocol_name "parameter" to a test case
    # function appears to go unnoticed, it's likely present so that the
    # samples fixture can use its value to accordingly adjust the protocol
    # name for each Sample.

    @pytest.mark.parametrize(
        argnames=["selector_attribute", "selector_include"],
        argvalues=[("protocol", "totally-radical-protocol"),
                   ("protocol", "WackyNewProtocol"), ("protocol", "arbitrary_protocol")])
    def test_empty_intersection_with_inclusion(
            self, samples, selector_attribute, selector_include):
        """ Sensitivity and specificity for positive protocol selection. """
        prj = mock.MagicMock(samples=samples)
        observed = fetch_samples(
            prj, selector_attribute=selector_attribute, selector_include=selector_include)
        assert set() == set(observed)

    @pytest.mark.parametrize(
        argnames=["selector_attribute", "selector_include"],
        argvalues=[("protocol", {"ATAC-Seq", "ChIP-Seq"})])
    def test_partial_intersection_with_inclusion(self,
            samples, selector_attribute, selector_include, expected_sample_names):
        """ Empty intersection with the selector_include means no Samples. """

        # Mock the Project instance.
        prj = mock.MagicMock(samples=samples)

        # Debug aid (only visible if failed)
        print("Grouped sample names (by protocol): {}".
              format(_group_samples_by_protocol()))
        print("Inclusion specification: {}".format(selector_include))

        # Perform the call under test and make the associated assertions.
        observed = fetch_samples(
            prj, selector_attribute=selector_attribute, selector_include=selector_include)
        _assert_samples(expected_sample_names, observed)

    def test_complete_intersection_with_inclusion(
            self, samples):
        """ Project with Sample set a subset of selector_include has all fetched. """
        prj = mock.MagicMock(samples=samples)
        expected = {s.name for s in samples}
        inclusion_protocols = list(BASIC_PROTOCOL_NAMES)
        print("Inclusion protocols: {}".format(inclusion_protocols))
        observed = fetch_samples(prj, selector_include=inclusion_protocols)
        _assert_samples(expected, observed)

    @pytest.mark.parametrize(
        argnames=["selector_attribute", "selector_include", "expected_names"],
        argvalues=[("protocol", "ATAC-Seq", {}),
                   ("protocol", ("ChIP-Seq", "ATAC-Seq", "RNA-seq"),
                    {"chip1", "rna_SE", "rna_PE"})])
    def test_samples_without_protocol_are_not_included(
            self, samples, selector_attribute, selector_include, expected_names):
        """ Inclusion does not grab Sample lacking protocol. """

        # Note that the expectations fixture isn't used here since this does
        # not fit the generic framework in which that one applies.

        prj = mock.MagicMock(samples=samples)

        # Remove protocol for ATAC-Seq samples.
        for s in samples:
            if s.protocol == "ATAC-Seq":
                delattr(s, "protocol")

        observed = fetch_samples(
            prj, selector_attribute=selector_attribute, selector_include=selector_include)
        _assert_samples(expected_names, observed)
        
    @pytest.mark.parametrize(
        argnames=["selector_attribute", "selector_include"],
        argvalues=[("protocol", "ATAC-Seq"), ("protocol", {"WGBS", "RRBS"})],
        ids=lambda protos: str(protos))
    def test_equivalence_with_subproject(
            self, tmpdir, samples, selector_attribute, selector_include):
        """ Selection for protocol(s) is like specific subproject. """
        sp_name = "atac"
        confpath = _write_project_files(
            tmpdir, all_samples=samples, sp_name=sp_name,
            sp_samples=list(filter(lambda s: s.protocol in selector_include, samples)))
        try:
            full_project = Project(confpath)
        except Exception:
            anns_file = os.path.join(tmpdir.strpath, METADATA_KEY, "anns.csv")
            print("Annotations file lines:")
            with open(anns_file, 'r') as f:
                print(f.readlines())
            raise
        subproject = Project(confpath, subproject=sp_name)
        expected = {s.name for s in subproject.samples}
        observed = fetch_samples(full_project,
            selector_attribute=selector_attribute, selector_include=selector_include)
        _assert_samples(expected, observed_samples=observed)


class ProtocolExclusionTests:
    """ Samples can be selected against by protocol. """

    # Note that even if the vary_protocol_name "parameter" to a test case
    # function appears to go unnoticed, it's likely present so that the
    # samples fixture can use its value to accordingly adjust the protocol
    # name for each Sample.

    @pytest.mark.parametrize(
        argnames=["selector_attribute", "selector_exclude"],
        argvalues=[("protocol", "mystery_protocol"),
                   ("protocol", ["wacky-protocol", "BrandNewProtocol"])])
    def test_empty_intersection_with_exclusion(
            self, samples, selector_attribute, selector_exclude):
        """ Empty intersection with selector_exclude means all Samples remain. """
        prj = mock.MagicMock(samples=samples)
        expected = {s.name for s in samples}
        observed = fetch_samples(prj,
            selector_attribute=selector_attribute, selector_exclude=selector_exclude)
        _assert_samples(expected, observed)

    @pytest.mark.parametrize(
        argnames=["selector_attribute", "selector_exclude"],
        argvalues=[("protocol", "ChIP-Seq"), ("protocol", {"RNA-seq", "RRBS"})])
    def test_partial_intersection_with_exclusion(
            self, samples, selector_attribute, selector_exclude, expected_sample_names):
        """ Sensitivity and specificity for negative protocol selection. """

        # Mock out the Project instance.
        prj = mock.MagicMock(samples=samples)

        # Make the call and the relevant assertions.
        observed = fetch_samples(prj,
            selector_attribute=selector_attribute, selector_exclude=selector_exclude)
        print(expected_sample_names)
        print(observed)
        _assert_samples(expected_sample_names, observed)

    def test_complete_intersection_with_exclusion(
            self, samples):
        """ Comprehensive exclusion can leave no Samples. """
        prj = mock.MagicMock(samples=samples)
        observed = fetch_samples(
            prj, selector_attribute="protocol", selector_exclude=list(BASIC_PROTOCOL_NAMES))
        _assert_samples([], observed)

    @pytest.mark.parametrize(
        argnames="spare_via_anonymity",
        argvalues=["ChIP-Seq", "ATAC-Seq", ["RNA-seq", "WGBS", "RRBS"]],
        ids=lambda spared: str(spared))
    def test_samples_without_protocol_are_not_excluded(
            self, samples, spare_via_anonymity):
        """ Negative selection on protocol leaves Samples without protocol. """
        # Strategy: specify all of the protocols as exclusions, then allow
        # the parameterization to specify which are to be "spared" exclusion
        # by removing the protocol selector_attribute

        print("Spare input: {}".format(spare_via_anonymity))

        # Account for varied argument types, and contextualize the protocol
        # names with the test case parameterization. That is, vary them as they
        # were in the creation of the value supplied via the samples fixture.
        if isinstance(spare_via_anonymity, str):
            spare_via_anonymity = [spare_via_anonymity]
        spare_via_anonymity = list(spare_via_anonymity)

        print("Modified spare: {}".format(spare_via_anonymity))

        # Remove the protocols designated for sparing (from selector_exclude).
        for s in samples:
            if s.protocol in spare_via_anonymity:
                delattr(s, "protocol")

        print("Protocols on samples: {}".format(
            {s.protocol for s in samples if hasattr(s, "protocol")}))
        print("Protocols to spare: {}".format(spare_via_anonymity))
        print("Non-protocol Samples: {}".format(
            {s.name for s in samples if not hasattr(s, "protocol")}))

        # Mock out the project with the updated Sample objects.
        prj = mock.MagicMock(samples=samples)

        # Expected names are associated with protocols spared selector_exclude.
        sample_names_by_protocol = _group_samples_by_protocol()
        expected_names = set(itertools.chain.from_iterable(
            sample_names_by_protocol[p] for p in spare_via_anonymity))

        # Make the call and relevant assertions.
        observed = fetch_samples(
            prj, selector_attribute="protocol", selector_exclude=list(BASIC_PROTOCOL_NAMES))
        _assert_samples(expected_names, observed)


def _assert_samples(expected_names, observed_samples):
    """
    Assert that each observation is a sample and that the set of expected
    Sample names agrees with the set of observed names.

    :param Iterable[str] expected_names:
    :param Iterable[Sample] observed_samples: collection of Sample objects,
        e.g. obtained with fetch_samples(), to which assertions apply
    """
    expected_names = set(expected_names)
    assert all([isinstance(s, Sample) for s in observed_samples])
    observed_names = {s.name for s in observed_samples}
    assert expected_names == observed_names
