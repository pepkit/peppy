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
        main_idx_keys = kwds.setdefault(MAIN_INDEX_KEY, SNAKEMAKE_SAMPLE_COL)
        kwds[MAIN_INDEX_KEY] = _ensure_idx_key(
            main_idx_keys, bad=SAMPLE_NAME_COLNAME, sub=SNAKEMAKE_SAMPLE_COL)
        subs_idx_keys = kwds.setdefault(
           SUBS_INDEX_KEY, (SNAKEMAKE_SAMPLE_COL, UNITS_COLUMN))
        kwds[SUBS_INDEX_KEY] = _ensure_idx_key(
            subs_idx_keys, bad=SAMPLE_NAME_COLNAME, sub=SNAKEMAKE_SAMPLE_COL)
        super(SnakeProject, self).__init__(cfg, **kwds)

    def activate_subproject(self, subproject):
        raise NotImplementedError(
            "Subproject activation implementation is likely to change and "
            "is not supported on {}".format(self.__class__.__name__))

    def deactivate_subproject(self):
        raise NotImplementedError(
            "Subproject deactivation implementation is likely to change and "
            "is not supported on {}".format(self.__class__.__name__))

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

    def _index_main_table(self, t):
        """ Index column(s) of the subannotation table. """
        if t is None:
            return
        colname = self["_" + MAIN_INDEX_KEY]
        return t.set_index(colname, drop=False)
        #return t.set_index(colname if colname in t.columns else SNAKEMAKE_SAMPLE_COL, drop=False)

    def _index_subs_table(self, t):
        """ Index column(s) of the subannotation table. """
        if t is None:
            return
        ideal_labels = self["_" + SUBS_INDEX_KEY]
        ideal_labels = [ideal_labels] if isinstance(ideal_labels, str) else ideal_labels
        labels, missing = [], []
        equiv = [SAMPLE_NAME_COLNAME, SNAKEMAKE_SAMPLE_COL]
        for l in ideal_labels:
            if l in equiv:
                for eq in equiv:
                    if eq in t.columns and eq not in labels:
                        labels.append(eq)
                        break
                else:
                    missing.append(l)
            else:
                (labels if l in t.columns else missing).append(l)
        if missing:
            _LOGGER.warning("Missing subtable index labels: {}".
                            format(", ".join(missing)))
        return t.set_index(labels, drop=False)

    def _missing_columns(self, cs):
        return set() if {self.SAMPLE_NAME_IDENTIFIER, SAMPLE_NAME_COLNAME} & cs \
            else {self.SAMPLE_NAME_IDENTIFIER}

    @staticmethod
    def _get_sample_ids(df):
        """ Return the sample identifiers in the given table. """
        type_check_strict(df, DataFrame)
        try:
            return df[SNAKEMAKE_SAMPLE_COL]
        except KeyError:
            return df[SAMPLE_NAME_COLNAME]


def _ensure_idx_key(keys, bad, sub):
    """
    Ensure index keys comply with expectation, forcing and warning if not.

    :param str | Iterable[str] keys: index key or collection of them
    :param str bad: restricted index key to prohibit
    :param str sub: index key to use instread of restricted one
    :return str | list[str]: index key or collection of them
    """
    warning_message = "Will use {} to index rather than {}".format(sub, bad)
    if isinstance(keys, str):
        if keys == bad:
            _LOGGER.warning(warning_message)
            return sub
        return keys
    ks = list(keys)
    try:
        idx = ks.index(bad)
    except ValueError:
        if not isinstance(keys, list):
            _LOGGER.debug("Converting index keys ({}) to list".format(keys))
    else:
        _LOGGER.warning(warning_message)
        ks[idx] = sub
    return ks


def _rename_columns(t):
    """ Update table column names to map peppy to Snakemake. """
    return t.rename({SAMPLE_NAME_COLNAME: SNAKEMAKE_SAMPLE_COL}, axis=1)
