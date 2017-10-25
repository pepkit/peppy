""" Handle compute job resource bundling. """

from collections import namedtuple

import abc
import sys
if sys.version_info < (3, 3):
    from collections import Mapping, MutableMapping
else:
    from collections.abc import Mapping, MutableMapping

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"





class ResourceBundle(MutableMapping):
    """ Encapsulate the notion of a bundle of resources for a compute job. """

    __metaclass__ = abc.ABCMeta

    def __init__(self, items=None):
        super(ResourceBundle, self).__init__()
        self._data = {}
        if items is not None and isinstance(items, Mapping):
            items = items.items()
        for k, v in items:
            self._data[k] = v

    def __getitem__(self, item):
        return self._data[item]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __iter__(self):
        return iter(self._data)

    def __delitem__(self, key):
        del self._data[key]

    def __len__(self):
        return sum(1 for _ in iter(self))

    @abc.abstractproperty
    def core_keys(self):
        """
        Define which keys constitute the identity of this bundle.

        :return Iterable[str]: collection of keys for which the value defines
            a component of this bundle's identity
        """
        pass

    @property
    def defining_values(self):
        """
        Fetch the collection of keys and values that define this bundle.

        :return Mapping[str, object]: collection of key-value pairs that
            defines the identity of this bundle
        """
        return {k: self[k] for k in self.core_keys}



def compare_bundles(b1, b2):
    """
    Determine whether two resource bundles are compatible.

    :param looper.ResourceBundle b1:
    :param looper.ResourceBundle b2:
    :return bool: Whether the critical values
    """

    # We're only comparing resource bundles.
    if not (isinstance(b1, ResourceBundle) and isinstance(b2, ResourceBundle)):
        raise TypeError("Only two {} may be compared".format(
                ResourceBundle.__name__))

    # For equivalence, the bundles must possess the same set of
    # identity-determining keys.
    b1_keys = set(b1.identity_keys)
    b2_keys = set(b2.identity_keys)
    if b1_keys != b2_keys:
        return False

    # If there's a value mismatch among any of the bundles' core keys, they're
    # unequal. Otherwise, they're equal.
    for k in b1_keys:
        if b1[k] != b2[k]:
            return False
    return True
