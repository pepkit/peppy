""" Tests for fetching Samples of certain protocol(s) from a Project """

import itertools
import mock
import pytest
from looper.models import fetch_samples, Sample


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



PROTOCOL_BY_SAMPLE = {
    "atac_A": "ATAC-Seq", "atac_B": "ATAC-Seq",
    "chip1": "ChIP-Seq", "WGBS-1": "WGBS", "RRBS-1": "RRBS",
    "rna_SE": "RNA-Seq", "rna_PE": "RNA-Seq"}
BASIC_PROTOCOL_NAMES = list(itertools.chain(*PROTOCOL_BY_SAMPLE.values()))



@pytest.fixture(scope="function")
def samples():
    return [Sample({"sample_name": sn, "protocol": p})
            for sn, p in PROTOCOL_BY_SAMPLE.items()]



def generate_protocol_aliases(protocol):
    """
    Create case/punctuation-based variants of a protocol name.

    This method is useful for generating the inputs to test cases that
    check the fuzziness of a match to protocol, since that's often specified
    by a user and we don't want to be overly strict about how a protocol
    must be specified with regard to punctuation and case.

    :param str protocol: a basic protocol name on which to base variants.
    :return Iterable[str]: collection of protocol name variants based on the
        given protocol name
    """
    return {protocol.upper(), protocol.lower(), protocol.replace("-", "")}



@pytest.fixture(scope="function")
def protocol_variant_strategies():
    """
    Create case/punctuation-based variants of a protocol name.

    This method is useful for generating the inputs to test cases that
    check the fuzziness of a match to protocol, since that's often specified
    by a user and we don't want to be overly strict about how a protocol
    must be specified with regard to punctuation and case.

    :return Iterable[str]: collection of protocol name variants based on the
        given protocol name
    """
    return [lambda p: p.upper, lambda p: p.lower(), lambda p: p.replace("-", "")]



@pytest.mark.parametrize(
    argnames=["inclusion", "exclusion"], argvalues=itertools.product(
            ["ATAC-Seq", "ChIPmentation", {"RNA-Seq", "ChIP"}],
            ["WGBS", {"WGBS", "RRBS"}]))
def test_only_inclusion_or_exclusion(inclusion, exclusion, samples):
    """ Only an inclusion or exclusion set is permitted. """
    prj = mock.MagicMock(samples=samples)
    with pytest.raises(TypeError):
        fetch_samples(prj, inclusion, exclusion)



@pytest.mark.parametrize(
    argnames=["inclusion", "exclusion"], argvalues=[
            ("ATAC", None), ({"ChIPmentation", "RNA-Seq"}, None),
            (None, "ChIP-Seq"), (None, {"ATAC-Seq", "ChIPmentation"})])
def test_no_samples(inclusion, exclusion):
    """ Regardless of filtration, lack of samples means empty collection. """
    prj = mock.MagicMock(samples=[])
    observed = fetch_samples(prj, inclusion, exclusion)
    assert [] == observed



class ProtocolInclusionTests:
    """ Samples can be selected for by protocol. """

    def test_no_inclusions(self):
        """ Empty intersection with the inclusion means no Samples. """
        pass

    def test_some_inclusions(self):
        """ Sensitivity and specificity for positive protocol selection. """
        pass


    def test_inclusion_covers_all_samples(self):
        """ Project with Sample set a subset of inclusion has all fetched. """
        pass


    def test_samples_without_protocol_are_not_included(self):
        """ Inclusion does not grab Sample lacking protocol. """
        pass



class ProtocolExclusionTests:
    """ Samples can be selected against by protocol. """

    def test_no_exclusions(self):
        """ Empty intersection with exclusion means all Samples remain. """
        pass


    def test_some_exclusions(self):
        """ Sensitivity and specificity for negative protocol selection. """
        pass


    def test_exclusion_covers_all_samples(self):
        """ Comprehensive exclusion can leave no Samples. """
        pass


    def test_samples_without_protocol_are_not_excluded(self):
        """ Negative selection on protocol leaves Samples without protocol. """
        pass



class NoFiltersTests:
    """ Without a filtration mechanism, all Samples are retained. """
    pass
