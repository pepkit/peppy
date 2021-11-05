""" Basic tests for Snakemake Project type """

import itertools
import os

import pytest
import yaml
from pandas import Index, MultiIndex

from peppy import SnakeProject
from peppy.const import *
from peppy.const import SNAKEMAKE_SAMPLE_COL
from peppy.project import MAIN_INDEX_KEY, SUBS_INDEX_KEY
from peppy.snake_project import UNITS_COLUMN

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


NAME_COLNAMES = [SAMPLE_NAME_COLNAME, SNAKEMAKE_SAMPLE_COL]
SAMPLE_NAMES = ["testA", "testB"]


VALIDATIONS = {
    "sample_table": [
        lambda df: SAMPLE_NAME_COLNAME not in df.columns,
        lambda df: SNAKEMAKE_SAMPLE_COL in df.columns,
        lambda df: SAMPLE_NAMES == list(df[SNAKEMAKE_SAMPLE_COL]),
    ],
    "subsample_table": [
        lambda df: SAMPLE_NAME_COLNAME not in df.columns,
        lambda df: SNAKEMAKE_SAMPLE_COL in df.columns,
        # lambda df: UNITS_COLUMN in df.columns,
        # lambda df: [str(i) for i in [1, 2, 1, 2]] == list(df[UNITS_COLUMN])
    ],
}


@pytest.fixture(
    scope="function", params=list(itertools.product(NAME_COLNAMES, NAME_COLNAMES))
)
def prj(request, tmpdir):
    """ Provide a test case with a project instance. """
    main_name, subs_name = request.param
    folder = tmpdir.strpath
    cfg, ann, subann = [
        os.path.join(folder, n) for n in ["pc.yaml", "anns.tsv", "units.tsv"]
    ]
    for f in [cfg, ann, subann]:
        assert not os.path.exists(
            f
        ), "Pretest failed; file to create already exists: {}".format(f)
    data = {
        METADATA_KEY: {SAMPLE_ANNOTATIONS_KEY: ann, SAMPLE_SUBANNOTATIONS_KEY: subann}
    }
    with open(ann, "w") as f:
        f.write("\n".join([main_name] + SAMPLE_NAMES))
    double_names, _ = make_units_table_names_and_units_vectors()
    with open(subann, "w") as f:
        f.write("\n".join([subs_name] + double_names))
    with open(cfg, "w") as f:
        yaml.dump(data, f)
    return SnakeProject(cfg)


# @pytest.mark.xfail(reason="{} may not be added; implementation decision in flux.".format(UNITS_COLUMN))
@pytest.mark.parametrize(
    ["table_name", "validate"],
    [(tn, f) for tn, checks in VALIDATIONS.items() for f in checks],
)
def test_snake_project_table(prj, table_name, validate):
    """ Validate columns/values of a metadata table from Snakemake project. """
    assert validate(getattr(prj, table_name))


def make_units_table_names_and_units_vectors():
    """ Create the sample names and units vectors for the units table. """
    names = list(itertools.chain(*zip(SAMPLE_NAMES, SAMPLE_NAMES)))
    units = [str(i) for i in [1, 2, 1, 2]]
    return names, units


@pytest.mark.parametrize(
    ["exp_dat", "observe"],
    [
        (lambda p: p.sample_names, lambda p: p.sample_table.index),
        (
            lambda p: list(itertools.chain(*[(n, n) for n in p.sample_names])),
            lambda p: p.subsample_table.index,
        ),
    ],
)
def test_default_table_indexing(prj, exp_dat, observe):
    """ Verify expected default behavior for indexing of Project tables. """
    exp = Index(name=SNAKEMAKE_SAMPLE_COL, data=exp_dat(prj))
    assert exp.equals(observe(prj))


@pytest.mark.parametrize("first_sub_index", ["a", "A"])
@pytest.mark.parametrize("sub_per_sample", [2, 3])
@pytest.mark.parametrize("main_index_column", [SNAKEMAKE_SAMPLE_COL])
@pytest.mark.parametrize(
    "subs_index_column", ["unit", "subsample_name", "random_column"]
)
def test_explicit_table_indexing(
    tmpdir, first_sub_index, sub_per_sample, main_index_column, subs_index_column
):
    step_funs = {str: lambda s, i: chr(ord(s) + i), int: lambda x, i: x + i}
    step = step_funs[type(first_sub_index)]
    main_index_data = ["testA", "testB", "testC"]
    main_vals = [x for x in range(len(main_index_data))]
    subs_names = list(itertools.chain(*[sub_per_sample * [n] for n in main_index_data]))
    print("SUBS NAMES: {}".format(subs_names))
    subs_index_data = list(
        itertools.chain(
            *[
                [step(first_sub_index, i) for i in range(sub_per_sample)]
                for _ in main_index_data
            ]
        )
    )
    subs_vals = len(main_index_data) * list(range(len(main_index_data)))
    ext, sep = ".tsv", "\t"
    dat_col = "data"
    annsfile = tmpdir.join("anns" + ext).strpath
    subsfile = tmpdir.join("subs" + ext).strpath
    conffile = tmpdir.join("conf.yaml").strpath
    annstemp = "{}{}{}"
    annslines = [
        annstemp.format(name, sep, value)
        for name, value in [(main_index_column, dat_col)]
        + list(zip(main_index_data, main_vals))
    ]
    substemp = "{n}{sep}{sub}{sep}{v}"
    subslines = [
        substemp.format(n=name, sep=sep, sub=sub, v=val)
        for name, sub, val in [(main_index_column, subs_index_column, dat_col)]
        + list(zip(subs_names, subs_index_data, subs_vals))
    ]
    with open(annsfile, "w") as f:
        f.write("\n".join(annslines))
    with open(subsfile, "w") as f:
        f.write("\n".join(subslines))
    with open(conffile, "w") as f:
        yaml.dump(
            {
                METADATA_KEY: {
                    SAMPLE_ANNOTATIONS_KEY: annsfile,
                    SAMPLE_SUBANNOTATIONS_KEY: subsfile,
                }
            },
            f,
        )
    p = SnakeProject(
        conffile,
        **{
            MAIN_INDEX_KEY: main_index_column,
            SUBS_INDEX_KEY: (main_index_column, subs_index_column),
        }
    )
    print("SUBS TABLE:\n{}".format(p.subsample_table))
    exp_main_idx = Index(main_index_data, name=main_index_column)
    assert exp_main_idx.equals(p.sample_table.index)
    obs_subs_idx = p.subsample_table.index
    assert isinstance(obs_subs_idx, MultiIndex)
    exp_subs_names = [main_index_column, subs_index_column]
    exp_subs_levels = [main_index_data, subs_index_data[:sub_per_sample]]
    print("EXP NAMES: {}".format(exp_subs_names))
    print("EXP LEVELS: {}".format(exp_subs_levels))
    print("OBS NAMES: {}".format(obs_subs_idx.names))
    print("OBS LEVELS: {}".format(obs_subs_idx.levels))
    assert exp_subs_levels == [list(l) for l in obs_subs_idx.levels]
    assert exp_subs_names == obs_subs_idx.names
