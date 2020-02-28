""" Helpers without an obvious logical home. """

from collections import Iterable
import logging
import os

_LOGGER = logging.getLogger(__name__)

__all__ = ["fetch_samples"]


def copy(obj):
    def copy(self):
        """
        Copy self to a new object.
        """
        from copy import deepcopy

        return deepcopy(self)
    obj.copy = copy
    return obj


def fetch_samples(proj, selector_attribute=None, selector_include=None, selector_exclude=None):
    """
    Collect samples of particular protocol(s).

    Protocols can't be both positively selected for and negatively
    selected against. That is, it makes no sense and is not allowed to
    specify both selector_include and selector_exclude protocols. On the other hand, if
    neither is provided, all of the Project's Samples are returned.
    If selector_include is specified, Samples without a protocol will be excluded,
    but if selector_exclude is specified, protocol-less Samples will be included.

    :param Project proj: the Project with Samples to fetch
    :param str selector_attribute: name of attribute on which to base the fetch
    :param Iterable[str] | str selector_include: protocol(s) of interest;
        if specified, a Sample must
    :param Iterable[str] | str selector_exclude: protocol(s) to include
    :return list[Sample]: Collection of this Project's samples with
        protocol that either matches one of those in selector_include, or either
        lacks a protocol or does not match one of those in selector_exclude
    :raise TypeError: if both selector_include and selector_exclude protocols are
        specified; TypeError since it's basically providing two arguments
        when only one is accepted, so remain consistent with vanilla Python2;
        also possible if name of attribute for selection isn't a string
    """
    if selector_attribute is None or (not selector_include and not selector_exclude):
        # Simple; keep all samples.  In this case, this function simply
        # offers a list rather than an iterator.
        return list(proj.samples)

    if not isinstance(selector_attribute, str):
        raise TypeError(
            "Name for attribute on which to base selection isn't string: {} "
            "({})".format(selector_attribute, type(selector_attribute)))

    # At least one of the samples has to have the specified attribute
    if proj.samples and not any([hasattr(s, selector_attribute) for s in proj.samples]):
        raise AttributeError("The Project samples do not have the attribute '{attr}'"
                             .format(attr=selector_attribute))

    # Intersection between selector_include and selector_exclude is nonsense user error.
    if selector_include and selector_exclude:
        raise TypeError("Specify only selector_include or selector_exclude parameter, "
                         "not both.")

    # Ensure that we're working with sets.
    def make_set(items):
        if isinstance(items, str):
            items = [items]
        return items

    # Use the attr check here rather than exception block in case the
    # hypothetical AttributeError would occur; we want such
    # an exception to arise, not to catch it as if the Sample lacks "protocol"
    if not selector_include:
        # Loose; keep all samples not in the selector_exclude.
        def keep(s):
            return not hasattr(s, selector_attribute) or \
                   getattr(s, selector_attribute) not in make_set(selector_exclude)
    else:
        # Strict; keep only samples in the selector_include.
        def keep(s):
            return hasattr(s, selector_attribute) and \
                   getattr(s, selector_attribute) in make_set(selector_include)

    return list(filter(keep, proj.samples))
