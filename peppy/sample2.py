from collections import Mapping, OrderedDict
from string import Formatter
from logging import getLogger
from copy import copy as cp
import os
import glob

from attmap import PathExAttMap
from .const2 import *
from .utils import copy, grab_project_data
from .exceptions import InvalidSampleTableFileException

_LOGGER = getLogger(PKG_NAME)

@copy
class Sample2(PathExAttMap):
    """
    Class to model Samples based on a pandas Series.

    :param Mapping | pandas.core.series.Series series: Sample's data.

    :Example:

    .. code-block:: python

        from models import Project, SampleSheet, Sample
        prj = Project("ngs")
        sheet = SampleSheet("~/projects/example/sheet.csv", prj)
        s1 = Sample(sheet.iloc[0])
    """
    def __init__(self, series, prj=None):

        super(Sample2, self).__init__()

        data = OrderedDict(series)
        _LOGGER.debug("Sample data: {}".format(data))

        # Attach Project reference
        try:
            data_proj = data.pop(PRJ_REF)
        except (AttributeError, KeyError):
            data_proj = None

        self.add_entries(data)

        if data_proj and PRJ_REF not in self:
            self[PRJ_REF] = data_proj

        typefam = PathExAttMap
        if PRJ_REF in self and prj:
            _LOGGER.warning("Project data provided both in data and as separate"
                            " constructor argument; using direct argument")
        if prj:
            self[PRJ_REF] = prj
        if not self.get(PRJ_REF):
            # Force empty attmaps to null and ensure something's set.
            self[PRJ_REF] = None
            _LOGGER.debug("No project reference for sample")
        else:
            prefix = "Project reference on a sample must be an instance of {}".\
                format(typefam.__name__)
            if not isinstance(self[PRJ_REF], Mapping):
                raise TypeError(
                    prefix + "; got {}".format(type(self[PRJ_REF]).__name__))
            if self[PRJ_REF].validate():
                _LOGGER.warning(
                    prefix + " but cannot be a Project; extracting storing just"
                             " sample-independent Project data in {k}"
                    .format(k=PRJ_REF))
                self[PRJ_REF] = grab_project_data(self[PRJ_REF])
        self._derived_cols_done = []

    def derive_attribute(self, data_sources, attr_name):
        """
        Uses the template path provided in the project config section
        "data_sources" to piece together an actual path by substituting
        variables (encoded by "{variable}"") with sample attributes.

        :param Mapping data_sources: mapping from key name (as a value in
            a cell of a tabular data structure) to, e.g., filepath
        :param str attr_name: Name of sample attribute
            (equivalently, sample sheet column) specifying a derived column.
        :return str: regex expansion of data source specified in configuration,
            with variable substitutions made
        :raises ValueError: if argument to data_sources parameter is null/empty
        """

        def _format_regex(regex, items):
            """
            Format derived source with object attributes

            :param str regex: string to format,
                e.g. {identifier}{file_id}_data.txt
            :param Iterable[Iterable[Iterable | str]] items: items to format
                the string with
            :raise InvalidSampleTableFileException: if after merging
                subannotations the lengths of multi-value attrs are not even
            :return Iterable | str: formatted regex string(s)
            """
            keys = [i[1] for i in Formatter().parse(regex) if i[1] is not None]
            if not keys:
                return [regex]
            attr_lens = [len(v) for k, v in items.items()
                         if (isinstance(v, list) and k in keys)]
            if not bool(attr_lens):
                return [regex.format(**items)]
            if len(set(attr_lens)) != 1:
                msg = "All attributes to format the {} ({}) have to be the " \
                      "same length, got: {}. Correct your {}".\
                    format(DERIVED_SOURCES_KEY, regex, attr_lens,
                           SUBSAMPLE_TABLE_KEY)
                raise InvalidSampleTableFileException(msg)
            vals = []
            for i in range(0, attr_lens[0]):
                items_cpy = cp(items)
                for k in keys:
                    if isinstance(items_cpy[k], list):
                        items_cpy[k] = items_cpy[k][i]
                vals.append(regex.format(**items_cpy))
            return vals

        def _glob_regex(patterns):
            """
            Perform unix style pathname pattern expansion for multiple patterns

            :param Iterable[str] patterns: patterns to expand
            :return str| Iterable[str]: expanded patterns
            """
            outputs = []
            for p in patterns:
                if '*' in p or '[' in p:
                    _LOGGER.debug("Pre-glob: {}".format(p))
                    val_globbed = sorted(glob.glob(p))
                    if not val_globbed:
                        _LOGGER.debug("No files match the glob: '{}'".format(p))
                    else:
                        p = val_globbed
                        _LOGGER.debug("Post-glob: {}".format(p))

                outputs.extend(p if isinstance(p, list) else [p])
            return outputs if len(outputs) > 1 else outputs[0]

        if not data_sources:
            return None
        sn = self[SAMPLE_NAME_ATTR] \
            if SAMPLE_NAME_ATTR in self else "this sample"
        try:
            source_key = getattr(self, attr_name)
        except AttributeError:
            reason = "'{attr}': to locate sample's derived attribute source, " \
                     "provide the name of a key from '{sources}' or ensure " \
                     "sample has attribute '{attr}'".\
                format(attr=attr_name, sources=DERIVED_SOURCES_KEY)
            raise AttributeError(reason)

        try:
            regex = data_sources[source_key]
            _LOGGER.debug("Data sources: {}".format(data_sources))
        except KeyError:
            _LOGGER.debug("{}: config lacks entry for data_source key: "
                          "'{}' in column '{}'; known: {}".
                          format(sn, source_key, attr_name,
                                 data_sources.keys()))
            return ""
        deriv_exc_base = "In sample '{sn}' cannot correctly parse derived " \
                         "attribute source: {r}.".format(sn=sn, r=regex)
        try:
            vals = _format_regex(regex, dict(self.items()))
            _LOGGER.debug("Formatted regex: {}".format(vals))
        except KeyError as ke:
            _LOGGER.warning(deriv_exc_base + " Can't access {ke} attribute".
                            format(ke=str(ke)))
        except Exception as e:
            _LOGGER.warning(deriv_exc_base + " Exception type: {e}".
                            format(e=str(type(e).__name__)))
        else:
            return _glob_regex(vals)
        return None

    # The __reduce__ function provides an interface for
    # correct object serialization with the pickle module.
    def __reduce__(self):
        return (
            self.__class__,
            (self.as_series(),),
            (None, {}),
            iter([]),
            iter({PRJ_REF: self[PRJ_REF]}.items())
        )

    def _excl_from_eq(self, k):
        """ Exclude the Project reference from object comparison. """
        return k == PRJ_REF or super(Sample2, self)._excl_from_eq(k)

    def _excl_from_repr(self, k, cls):
        """ Exclude the Project reference from representation. """
        return k == PRJ_REF or super(Sample2, self)._excl_from_repr(k, cls)
