""" Dot notation support for Mappings. """

import logging
import sys
if sys.version_info < (3, 3):
    from collections import Mapping, MutableMapping
else:
    from collections.abc import Mapping, MutableMapping

from pandas import Series

from .const import DERIVATIONS_DECLARATION, IMPLICATIONS_DECLARATION
from .utils import \
    copy, has_null_value, non_null_value, warn_derived_cols, warn_implied_cols


ATTRDICT_METADATA = {"_force_nulls": False, "_attribute_identity": False}

_LOGGER = logging.getLogger(__name__)



def is_metadata(item_name):
    """
    Determine whether an item is known to be AttributeDict metadata.

    :param str item_name: Name of key or attribute to check for status as
        known AttributeDict metadata.
    :return bool: Whether the given key/name is known to be associated with
        AttributeDict metadata.
    """
    return item_name in ATTRDICT_METADATA



@copy
class AttributeDict(MutableMapping):
    """
    A class to convert a nested mapping(s) into an object(s) with key-values
    using object syntax (attr_dict.attribute) instead of getitem syntax
    (attr_dict["key"]). This class recursively sets mappings to objects,
    facilitating attribute traversal (e.g., attr_dict.attr.attr).
    """

    def __init__(self, entries=None,
                 _force_nulls=False, _attribute_identity=False):
        """
        Establish a logger for this instance, set initial entries,
        and determine behavior with regard to null values and behavior
        for attribute requests.

        :param collections.Iterable | collections.Mapping entries: collection
            of key-value pairs, initial data for this mapping
        :param bool _force_nulls: whether to allow a null value to overwrite
            an existing non-null value
        :param bool _attribute_identity: whether to return attribute name
            requested rather than exception when unset attribute/key is queried
        """
        # Null value can squash non-null?
        self.__dict__["_force_nulls"] = _force_nulls
        # Return requested attribute name if not set?
        self.__dict__["_attribute_identity"] = _attribute_identity
        self.add_entries(entries)


    def add_entries(self, entries):
        """
        Update this `AttributeDict` with provided key-value pairs.

        :param Iterable[(object, object)] | Mapping | pandas.Series entries:
            collection of pairs of keys and values
        :return AttributeDict: the updated instance
        """
        if entries is None:
            return
        # Permit mapping-likes and iterables/generators of pairs.
        if callable(entries):
            entries = entries()
        elif isinstance(entries, Series):
            entries = entries.to_dict()
        try:
            entries_iter = entries.items()
        except AttributeError:
            entries_iter = entries
        # Assume we now have pairs; allow corner cases to fail hard here.
        for key, value in entries_iter:
            self.__setitem__(key, value)
        return self


    def is_null(self, item):
        """
        Conjunction of presence in underlying mapping and value being None

        :param object item: Key to check for presence and null value
        :return bool: True iff the item is present and has null value
        """
        return has_null_value(item, self)


    def non_null(self, item):
        """
        Conjunction of presence in underlying mapping and value not being None

        :param object item: Key to check for presence and non-null value
        :return bool: True iff the item is present and has non-null value
        """
        return non_null_value(item, self)


    def __setattr__(self, key, value):
        self.__setitem__(key, value)


    def __getattr__(self, item, default=None):
        """
        Fetch the value associated with the provided identifier.

        :param int | str item: identifier for value to fetch
        :return object: whatever value corresponds to the requested key/item
        :raises AttributeError: if the requested item has not been set,
            no default value is provided, and this instance is not configured
            to return the requested key/item itself when it's missing; also,
            if the requested item is unmapped and appears to be protected,
            i.e. by flanking double underscores, then raise AttributeError
            anyway. More specifically, respect attribute naming that appears
            to be indicative of the intent of protection.
        """
        try:
            return super(AttributeDict, self).__getattribute__(item)
        except (AttributeError, TypeError):
            # Handle potential failure from non-string or property request.
            pass
        try:
            # Route this dot notation request through the Mapping route.
            return self.__dict__[item]
        except KeyError:
            # If not, triage and cope accordingly.
            if item.startswith("__") and item.endswith("__"):
                # Accommodate security-through-obscurity approach used by some libraries.
                error_reason = "Protected-looking attribute: {}".format(item)
                raise AttributeError(error_reason)
            if default is not None:
                # For compatibility with ordinary getattr() call, allow default value.
                return default
            if self.__dict__.setdefault("_attribute_identity", False):
                # Check if we should return the attribute name itself as the value.
                return item
            # Throw up our hands in despair and resort to exception behavior.
            raise AttributeError(item)


    def __setitem__(self, key, value):
        """
        This is the key to making this a unique data type. Flag set at
        time of construction determines whether it's possible for a null
        value to squash a non-null value. The combination of that flag and
        one indicating whether request for value for unset attribute should
        return the attribute name itself determines if any attribute/key
        may be set to a null value.

        :param str key: name of the key/attribute for which to establish value
        :param object value: value to which set the given key; if the value is
            a mapping-like object, other keys' values may be combined.
        :raises _MetadataOperationException: if attempt is made
            to set value for privileged metadata key
        """
        if key == "derived_columns":
            warn_derived_cols()
            key = DERIVATIONS_DECLARATION
        elif key == "implied_columns":
            warn_implied_cols()
            key = IMPLICATIONS_DECLARATION
        if isinstance(value, Mapping):
            try:
                # Combine AttributeDict instances.
                self.__dict__[key].add_entries(value)
            except (AttributeError, KeyError):
                # Create new AttributeDict, replacing previous value.
                self.__dict__[key] = AttributeDict(value)
        elif value is not None or \
                key not in self.__dict__ or self.__dict__["_force_nulls"]:
            self.__dict__[key] = value


    def __getitem__(self, item):
        try:
            # Ability to return requested item name itself is delegated.
            return self.__getattr__(item)
        except AttributeError:
            # Requested item is unknown, but request was made via
            # __getitem__ syntax, not attribute-access syntax.
            raise KeyError(item)

    def __delitem__(self, item):
        if is_metadata(item):
            raise _MetadataOperationException(self, item)
        try:
            del self.__dict__[item]
        except KeyError:
            _LOGGER.debug("No item {} to delete".format(item))

    def __eq__(self, other):
        try:
            # Ensure target itself and any values are AttributeDict.
            other = AttributeDict(other)
        except Exception:
            return False
        if len(self) != len(other):
            # Ensure we don't have to worry about other containing self.
            return False
        for k, v in self.items():
            try:
                if v != other[k]:
                    return False
            except KeyError:
                return  False
        return True

    def __ne__(self, other):
        return not self == other

    def __iter__(self):
        return iter([k for k in self.__dict__.keys()
                     if not is_metadata(k)])

    def __len__(self):
        return sum(1 for _ in iter(self))

    def __repr__(self):
        return repr({k: v for k, v in self.__dict__.items()
                    if include_in_repr(k, klazz=self.__class__)})

    def __str__(self):
        return "{}: {}".format(self.__class__.__name__, repr(self))



def include_in_repr(attr, klazz):
    """
    Determine whether to include attribute in an object's text representation.

    :param str attr: attribute to include/exclude from object's representation
    :param str | type klazz: name of type or type itself of which the object
        to be represented is an instance
    :return bool: whether to include attribute in an object's
        text representation
    """
    # TODO: try to leverage the class hierarchy to determine these exclusions.
    ad_metadata = list(ATTRDICT_METADATA.keys())
    project_specific_exclusions = ["_samples", "sample_subannotation", "sheet",
                                   "interfaces_by_protocol"]
    exclusions_by_class = {
            "AttributeDict": ad_metadata,
            "Project": project_specific_exclusions + ad_metadata,
            "Subsample": ["sheet", "sample", "merged_cols"] + ad_metadata,
            "Sample": ["sheet", "prj", "merged_cols"] + ad_metadata}
            
    classname = klazz.__name__ if isinstance(klazz, type) else klazz
    return attr not in exclusions_by_class.get(classname, [])



class _MetadataOperationException(Exception):
    """ Illegal/unsupported operation, motivated by `AttributeDict`. """

    def __init__(self, obj, meta_item):
        """
        Instance with which the access attempt was made, along with the
        name of the reserved/privileged metadata item, define the exception.

        :param object obj: instance with which
            offending operation was attempted
        :param str meta_item: name of the reserved metadata item
        """
        try:
            classname = obj.__class__.__name__
        except AttributeError:
            # Maybe we were given a class or function not an instance?
            classname = obj.__name__
        explanation = "Attempted unsupported operation on {} item '{}'". \
                format(classname, meta_item)
        super(_MetadataOperationException, self).__init__(explanation)
