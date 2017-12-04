""" Tests for specific exception conditions that may arise. """

import pytest
from pep.attribute_dict import AttributeDict


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"
__date__ = "2017-02-27"


@pytest.fixture(scope="function")
def ad():
    return AttributeDict()


def test_attrdict_empty_in(ad):
    """ Membership test returns False when the AttributeDict is empty. """
    assert 'a' not in ad


def test_attrdict_empty_notin(ad):
    """ Membership test returns False when requested item is missing. """
    assert 'a' not in ad
