""" Adapting Project for interop with Snakemake """

from copy import deepcopy
from .const import SAMPLE_NAME_COLNAME, SNAKEMAKE_SAMPLE_COL
from .project import Project, sample_table, subsample_table, MAIN_INDEX_KEY, \
    SUBS_INDEX_KEY
from .utils import count_repeats, get_logger, type_check_strict
from pandas import DataFrame

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"

__all__ = ["SnakeProject"]


UNITS_COLUMN = "unit"
_LOGGER = get_logger(__name__)


class SnakeProject(Project):
    """ Extending Project for interop with Snakemake """

    # Hook for Project's declaration of how it identifies samples.
    # Used for validation and for merge_sample (derived cols and such)
    SAMPLE_NAME_IDENTIFIER = SNAKEMAKE_SAMPLE_COL

    def __init__(self, cfg, **kwargs):
        kwds = deepcopy(kwargs)
        kwds.setdefault(MAIN_INDEX_KEY, SNAKEMAKE_SAMPLE_COL)
        kwds.setdefault(SUBS_INDEX_KEY, (SNAKEMAKE_SAMPLE_COL, UNITS_COLUMN))
        super(SnakeProject, self).__init__(cfg, **kwds)

    @property
    def sample_table(self):
        """
        Get (possibly building) Project's table of samples, naming for Snakemake.

        :return pandas.core.frame.DataFrame | NoneType: table of samples'
            metadata, if one is defined
        :raise Exception: if multiple sample identifier columns are present, or
            if any sample identifier is repeated
        """
        t = sample_table(self)
        if SAMPLE_NAME_COLNAME in t.columns and SNAKEMAKE_SAMPLE_COL in t.columns:
            raise Exception(
                "Multiple sample identifier columns present: {}".format(
                    ", ".join([SNAKEMAKE_SAMPLE_COL, SAMPLE_NAME_COLNAME])))
        t = _rename_columns(t)
        reps = count_repeats(t[SNAKEMAKE_SAMPLE_COL])
        if reps:
            raise Exception("Repeated sample identifiers (and counts): {}".
                            format(reps))
        return self._index_main_table(t)

    @property
    def subsample_table(self):
        """ The units table """
        return self._finalize_subsample_table(subsample_table(self))

    def _finalize_subsample_table(self, t):
        t = self._index_subs_table(_rename_columns(t))
        try:
            t.index.set_levels([l.astype(str) for l in t.index.levels])
        except AttributeError:
            _LOGGER.debug("Error enforcing string type on multi-index levels "
                          "for subsample table; perhaps unit columns isn't yet "
                          "available.")
        return t


    @staticmethod
    def _get_sample_ids(df):
        """ Return the sample identifiers in the given table. """
        type_check_strict(df, DataFrame)
        try:
            return df[SNAKEMAKE_SAMPLE_COL]
        except KeyError:
            return df[SAMPLE_NAME_COLNAME]


def _rename_columns(t):
    """ Update table column names to map peppy to Snakemake. """
    return t.rename({SAMPLE_NAME_COLNAME: SNAKEMAKE_SAMPLE_COL}, axis=1)
