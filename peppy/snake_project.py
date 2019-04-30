""" Adapting Project for interop with Snakemake """

from .const import *
from .const import SNAKEMAKE_SAMPLE_COL
from .project import Project, sample_table, subsample_table
from .utils import count_repeats, type_check_strict
from pandas import DataFrame

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"

__all__ = ["SnakeProject"]


class SnakeProject(Project):
    """ Extending Project for interop with Snakemake """

    # Hook for Project's declaration of how it identifies samples.
    # Used for validation and for merge_sample (derived cols and such)
    SAMPLE_NAME_IDENTIFIER = SNAKEMAKE_SAMPLE_COL

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
        return t.set_index(SNAKEMAKE_SAMPLE_COL, drop=False)

    @property
    def subsample_table(self):
        """
        Get (possibly building) Project's table of samples, naming for Snakemake.

        :return pandas.core.frame.DataFrame | NoneType: table of samples'
            metadata, if one is defined
        """

        def count_names(names):
            def go(rem, n, curr, acc):
                if not rem:
                    return acc + [n]
                h, tail = rem[0], rem[1:]
                return go(tail, n + 1, curr, acc) \
                    if h == curr else go(tail, 1, h, acc + [n])
            return go(names[1:], 1, names[0], []) if names else []

        t = _rename_columns(subsample_table(self))
        unit_col = "unit"
        if unit_col not in t.columns:
            units = [str(i) for n in count_names(list(t[SNAKEMAKE_SAMPLE_COL]))
                     for i in range(1, n + 1)]
            t.insert(1, unit_col, units)

        t.set_index([SNAKEMAKE_SAMPLE_COL, unit_col], drop=False, inplace=True)
        t.index.set_levels([i.astype(str) for i in t.index.levels])
        return t

    @staticmethod
    def _get_sample_ids(df):
        """ Return the sample identifiers in the given table. """
        type_check_strict(df, DataFrame)
        return df[SNAKEMAKE_SAMPLE_COL]


def _rename_columns(t):
    """ Update table column names to map peppy to Snakemake. """
    return t.rename({SAMPLE_NAME_COLNAME: SNAKEMAKE_SAMPLE_COL}, axis=1)
