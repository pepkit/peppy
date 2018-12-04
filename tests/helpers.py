""" Test utilities. """

from functools import partial
import itertools
import numpy as np
import pytest
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
    return partial(pytest.mark.parametrize(argnames, argvalues,
                   ids=lambda arg: "{}={}".format(argnames, arg)))



def powerset(items, min_items=0, include_full_pop=True):
    """
    Build the powerset of a collection of items.

    :param Iterable[object] items: "Pool" of all items, the population for
        which to build the power set.
    :param int min_items: Minimum number of individuals from the population
        to allow in any given subset.
    :param bool include_full_pop: Whether to include the full population in
        the powerset (default True to accord with genuine definition)
    :return list[object]: Sequence of subsets of the population, in
        nondecreasing size order
    """
    items = list(items)    # Account for iterable burn possibility.
    max_items = len(items) + 1 if include_full_pop else len(items)
    min_items = min_items or 0
    return list(itertools.chain.from_iterable(
            itertools.combinations(items, k)
            for k in range(min_items, max_items)))



nonempty_powerset = partial(powerset, min_items=1)



class TempLogFileHandler(object):
    """ Context manager for temporary file handler logging attachment """

    def __init__(self, filepath, level, mode='w'):
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
        handler = logging.FileHandler(self.logfile, mode='w')
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
                "Attempted to read messages from unused logfile: "
                "{}", self.logfile)
        with open(self.logfile, 'r') as f:
            return f.readlines()
