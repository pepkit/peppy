""" Test utilities. """

import numpy as np


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



def assert_entirely_equal(observed, expected):
    """ Accommodate equality assertion for varied data, including NaN. """
    try:
        assert observed == expected
    except AssertionError:
        assert np.isnan(observed) and np.isnan(expected)
    except ValueError:
        assert (observed == expected).all()
