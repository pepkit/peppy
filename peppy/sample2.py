from collections import Mapping, OrderedDict
from logging import getLogger
import os

from pandas import Series

from attmap import PathExAttMap
from .const import *
from .utils import copy, grab_project_data

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
