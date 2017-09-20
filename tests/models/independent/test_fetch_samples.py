""" Tests for fetching Samples of certain protocol(s) from a Project """

import mock
import pytest
from looper.models import fetch_samples


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



PROTOCOL_BY_SAMPLE = {"atac_A", "atac_B", "chip1", "WGBS-1", "RRBS-1", "rna_SE", "rna_PE"}
BASIC_PROTOCOL_NAMES = {"ATAC-Seq", "RNA-Seq", "ChIP-Seq", "WGBS", "RRBS"}



def generate_protocol_alii(protocol):
    """ Create case/punctuation-based variants of a protocol name. """
    return {protocol.upper(), protocol.lower(), protocol.replace("-", "")}



def test_only_inclusion_or_exclusion():
    """ Only an inclusion or exclusion set is permitted. """
    pass



class NoSamplesTests:
    """ Regardless of filtration, lack of samples means empty collection. """
    pass



class ProtocolInclusionTests:
    """ Samples can be selected for by protocol. """

    def test_no_inclusions(self):
        pass

    def test_some_inclusions(self):
        pass


    def test_include_all(self):
        pass


    def test_samples_without_protocol_are_not_included(self):
        pass



class ProtocolExclusionTests:
    """ Samples can be selected against by protocol. """

    def test_no_exclusions(self):
        pass


    def test_some_exclusions(self):
        pass


    def test_exclude_all(self):
        pass


    def test_samples_without_protocol_are_not_excluded(self):
        pass



class NoFiltersTests:
    """ Without a filtration mechanism, all Samples are retained. """
    pass
