""" Tests of responsiveness of sample merger """

from collections import Iterable, Mapping
import os
import pytest
import yaml
from peppy import *
from peppy.const import *
from peppy.project import NEW_PIPES_KEY


ANNS_NAME = "ann.csv"
PLIF_NAME = "plif.yaml"
SUBPROJECT_NAME = "changed_output"


@pytest.fixture
def pl_iface(tmpdir):
    """ Provide test case with path to written pipeline interface file. """
    data = {}
    fp = tmpdir.join(PLIF_NAME).strpath
    with open(fp, 'w') as f:
        yaml.dump(data, f)
    return fp


@pytest.fixture
def annsdata(tmpdir):
    """ Provide a test case with path to written annotations file. """
    lines = """sample_name,protocol,filename,data_source,read_type
ATAC-seq_human_PE,ATAC-seq,atac-seq_PE.bam,microtest,paired
ATAC-seq_human_SE,ATAC-seq,atac-seq_SE.bam,microtest,single
ChIP-seq_human_CTCF_PE,ChIP-seq,chip-seq_PE.bam,microtest,paired
ChIP-seq_human_CTCF_SE,ChIP-seq,chip-seq_SE.bam,microtest,single
ChIP-seq_human_H3K27ac_PE,ChIP-seq,chip-seq_PE.bam,microtest,paired
ChIP-seq_human_H3K27ac_SE,ChIP-seq,chip-seq_SE.bam,microtest,single
ChIPmentation_human_CTCF_PE,ChIPmentation,chipmentation_PE.bam,microtest,paired
ChIPmentation_human_CTCF_SE,ChIPmentation,chipmentation_SE.bam,microtest,single""".splitlines(True)
    return _makefile(tmpdir, ANNS_NAME, lines, newline=False)


@pytest.fixture
def conf_file(tmpdir, annsdata, pl_iface):
    """ Provide test case with project config data. """
    mainout, subout = [tmpdir.join(f).strpath for f in ["this", "that"]]
    os.makedirs(mainout)
    os.makedirs(subout)
    constant = "sleep"
    data = {
        METADATA_KEY: {
            OUTDIR_KEY: mainout,
            SAMPLE_ANNOTATIONS_KEY: annsdata,
            NEW_PIPES_KEY: pl_iface
        },
        DERIVATIONS_DECLARATION: "data_source",
        CONSTANTS_DECLARATION: {constant: 0.1},
        DATA_SOURCES_SECTION: {"microtest": os.path.join(
            "..", "..", "microtest-master", "data", "{filename}")},
        SUBPROJECTS_SECTION: {
            SUBPROJECT_NAME: {
                METADATA_KEY: {OUTDIR_KEY: subout},
                CONSTANTS_DECLARATION: {constant: 0.5}
            }
        }
    }
    return _makefile(tmpdir, "conf.yaml", data)


def test_subproject_activation_preserves_derived_path(tmpdir, conf_file):
    """ When a subproject changes no data relevant to a sample attribute, it shouldn't change. """
    old_prj = Project(conf_file)
    old_path = old_prj.samples[0].data_path
    new_prj = old_prj.activate_subproject(SUBPROJECT_NAME)
    new_path = new_prj.samples[0].data_path
    assert old_path == new_path


def _infer_write(data, newline=False):
    """
    Infer function with which to write a data structure.

    :param str | Mapping | Iterable[str] data: the data to write to disk
    :param bool newline: whether to add newline to text lines
    :return function(object, file) -> object: function that writes data to
        a file stream, possibly returning a value
    """
    if isinstance(data, Mapping):
        def write(d, f):
            yaml.dump(d, f)
    else:
        make_line = (lambda l: l + "\n") if newline else (lambda l: l)
        if isinstance(data, str):
            def write(d, f):
                f.write(make_line(d))
        elif isinstance(data, Iterable):
            def write(d, f):
                for l in d:
                    f.write(make_line(l))
        else:
            raise TypeError("Unexpected data structure type: {}".format(type(data)))
    return write


def _makefile(tmp, filename, data, newline=False):
    """
    Write data to a file and return the filepath.

    :param py.path.local.LocalPath tmp: tempfolder from a test case
    :param str filename: name f
    :param str | Mapping | Iterable[str] data:
    :param bool newline: whether to add newline to text lines
    :return str: path to the file created
    """
    fp = tmp.join(filename).strpath
    write = _infer_write(data, newline)
    with open(fp, 'w') as f:
        write(data, f)
    return fp
