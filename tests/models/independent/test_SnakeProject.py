""" Basic tests for Snakemake Project type """

import itertools
import os
import pytest
import yaml
from peppy import SnakeProject
from peppy.const import *
from peppy.const import SNAKEMAKE_SAMPLE_COL
from peppy.snake_project import UNITS_COLUMN

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


MAIN_TABLE_NAME_COLNAME_PARAM = "main_name_colname"
SUBS_TABLE_NAME_COLNAME_PARAM = "subs_name_colname"
NAME_COLNAMES = [SAMPLE_NAME_COLNAME, SNAKEMAKE_SAMPLE_COL]
SAMPLE_NAMES = ["testA", "testB"]


VALIDATIONS = {
    "sample_table": [
        lambda df: SAMPLE_NAME_COLNAME not in df.columns,
        lambda df: SNAKEMAKE_SAMPLE_COL in df.columns,
        lambda df: SAMPLE_NAMES == list(df[SNAKEMAKE_SAMPLE_COL])
    ],
    "subsample_table": [
        lambda df: SAMPLE_NAME_COLNAME not in df.columns,
        lambda df: SNAKEMAKE_SAMPLE_COL in df.columns,
        #lambda df: UNITS_COLUMN in df.columns,
        #lambda df: [str(i) for i in [1, 2, 1, 2]] == list(df[UNITS_COLUMN])
    ]
}


@pytest.fixture(scope="function",
                params=list(itertools.product(NAME_COLNAMES, NAME_COLNAMES)))
def prj(request, tmpdir):
    """ Provide a test case with a project instance. """
    main_name, subs_name = request.param
    folder = tmpdir.strpath
    cfg, ann, subann = [os.path.join(folder, n)
                        for n in ["pc.yaml", "anns.tsv", "units.tsv"]]
    for f in [cfg, ann, subann]:
        assert not os.path.exists(f), \
            "Pretest failed; file to create already exists: {}".format(f)
    data = {
        METADATA_KEY: {
            SAMPLE_ANNOTATIONS_KEY: ann,
            SAMPLE_SUBANNOTATIONS_KEY: subann
        }
    }
    with open(ann, 'w') as f:
        f.write("\n".join([main_name] + SAMPLE_NAMES))
    double_names, _ = make_units_table_names_and_units_vectors()
    with open(subann, 'w') as f:
        f.write("\n".join([subs_name] + double_names))
    with open(cfg, 'w') as f:
        yaml.dump(data, f)
    return SnakeProject(cfg)


#@pytest.mark.xfail(reason="{} may not be added; implementation decision in flux.".format(UNITS_COLUMN))
@pytest.mark.parametrize(
    ["table_name", "validate"],
    [(tn, f) for tn, checks in VALIDATIONS.items() for f in checks])
def test_snake_project_table(prj, table_name, validate):
    """ Validate columns/values of a metadata table from Snakemake project. """
    assert validate(getattr(prj, table_name))


def make_units_table_names_and_units_vectors():
    """ Create the sample names and units vectors for the units table. """
    names = list(itertools.chain(*zip(SAMPLE_NAMES, SAMPLE_NAMES)))
    units = [str(i) for i in [1, 2, 1, 2]]
    return names, units
