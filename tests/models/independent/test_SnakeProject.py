""" Basic tests for Snakemake Project type """

import os
import pytest
import yaml
from peppy import SnakeProject, SAMPLE_NAME_COLNAME
from peppy.const import SNAKEMAKE_SAMPLE_COL

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


@pytest.fixture(scope="function")
def prj(tmpdir):
    folder = tmpdir.strpath
    fp = tmpdir.join("pc.yaml").strpath
    #assert fp not in os.listdir()
    with open(tmpdir.join("")):
        pass
    #return SnakeProject()


@pytest.mark.skip("not implemented")
@pytest.mark.parametrize("validate",
    [lambda df: SAMPLE_NAME_COLNAME not in df.columns,
     lambda df: SNAKEMAKE_SAMPLE_COL in df.columns])
def test_column_renaming(validate):
    pass
