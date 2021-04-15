""" Test utilities. """

import random
import string
from functools import partial

import numpy as np
import pytest
from attmap import AttMap

import peppy

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


def compare_mappings(expected, observed):
    """ Account for possibility that observed value is AttMap. """
    print("EXPECTED: {}".format(expected))
    print("OBSERVED: {}".format(observed))
    assert set(expected.keys()) == set(observed.keys())
    for k, v_exp in expected.items():
        v_obs = observed[k]
        assert v_exp == (v_obs.to_dict() if isinstance(v_obs, AttMap) else v_obs)


def named_param(argnames, argvalues):
    """
    Parameterize a test case and automatically name/label by value

    :param str argnames: Single parameter name; this is only named in the
        plural for concordance with the pytest parameter to which it maps.
    :param Iterable[object] argvalues: Collection of arguments to the
        indicated parameter (argnames)
    :return functools.partial: Wrapped version of the call to the pytest
        test case parameterization function, for use as decorator.
    """
    return partial(
        pytest.mark.parametrize(
            argnames, argvalues, ids=lambda arg: "{}={}".format(argnames, arg)
        )
    )


def randomize_filename(ext=None, n_char=25):
    """
    Randomly generate a filename

    :param str ext: Extension, optional
    :param n_char: Number of characters (excluding extension)
    :return str: Randomized filename
    """
    if not isinstance(n_char, int):
        raise TypeError("Character count is not an integer: {}".format(n_char))
    if n_char < 0:
        raise ValueError("Negative char count: {}".format(n_char))
    fn = "".join(random.choice(string.ascii_letters) for _ in range(n_char))
    if not ext:
        return fn
    if not ext.startswith("."):
        ext = "." + ext
    return fn + ext


class TempLogFileHandler(object):
    """ Context manager for temporary file handler logging attachment """

    def __init__(self, filepath, level, mode="w"):
        """
        Create the temporary file handler by providing path and level

        :param str filepath: Path to file to use for logging handler.
        :param str | int level: Minimal severity level for file handler.
        :param str mode: Mode in which to create the file handler.
        """
        self.logfile = filepath
        self._level = level
        self._mode = mode
        self._used = False

    def __enter__(self):
        """ Add the handler to project module's logger, and update state. """
        import logging

        if self._used:
            raise Exception("Cannot reuse a {}".format(self.__class__.__name__))
        handler = logging.FileHandler(self.logfile, mode="w")
        handler.setLevel(self._level)
        peppy.project._LOGGER.handlers.append(handler)
        self._used = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ Remove the added file handler from the logger. """
        del peppy.project._LOGGER.handlers[-1]

    @property
    def messages(self):
        """ Open the handler's underlying file and read the messages. """
        if not self._used:
            raise Exception(
                "Attempted to read messages from unused logfile: " "{}", self.logfile
            )
        with open(self.logfile, "r") as f:
            return f.readlines()
