""" Tests for specific exception conditions that may arise. """

import pytest
from looper.models import AttributeDict


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"
__date__ = "2017-02-27"


@pytest.fixture(scope="function")
def ad():
    return AttributeDict()


def test_attrdict_empty_in(ad):
    assert not 'a' in ad


def test_attrdict_empty_notin(ad):
    assert 'a' not in ad
