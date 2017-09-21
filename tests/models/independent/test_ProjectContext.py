""" Tests for temporary contextualization of Project's Sample objects """

import os
import pytest
import yaml    # TODO: remove once project can take raw config data?
from looper.models import Project, Sample, ProjectContext


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



@pytest.fixture
def sample_names():
    return ["atac-PE", "chip1", "rna_PE", "wgbs-hs", "rrbs_ms"]


@pytest.fixture
def protocols():
    return ["ATAC", "CHIP", "RNA", "WGBS", "RRBS"]


@pytest.fixture
def samples(sample_names, protocols):
    return [Sample({"sample_name": sn, "protocol": p})
            for sn, p in zip(sample_names, protocols)]


@pytest.fixture
def sample_by_protocol(sample_names, protocols):
    return dict(zip(protocols, sample_names))


@pytest.fixture
def protocol_by_sample(sample_names, protocols):
    return dict(zip(sample_names, protocols))


@pytest.fixture
def project(request, sample_names, protocols, tmpdir):

    outdir = os.path.join(tmpdir.strpath, "output")
    metadir = os.path.join(tmpdir.strpath, "metadata")
    # So that it's just skipped, deliberately don't create this.
    pipedir = os.path.join(tmpdir.strpath, "pipelines")
    map(os.makedirs, [outdir, metadir])

    confpath = os.path.join(metadir, "conf.yaml")
    annspath = os.path.join(metadir, "anns.csv")
    conf_data = {"metadata": {
            "sample_annotation": annspath, "output_dir": outdir}}

    with open(confpath, 'w') as conf:
        yaml.dump(conf_data, conf)
    anns_data = [("sample_name", "protocol")] + list(zip(sample_names, protocols))
    with open(annspath, 'w') as anns:
        anns.write("\n".join(["{},{}".format(sn, p) for sn, p in anns_data]))

    return Project(confpath)




class ProjectContextTests:
    """ Tests for ProjectContext """


    def test_no_filtration(self, samples, project):
        """  """
        _assert_samples(samples, project.samples)
        with ProjectContext(project) as prj:
            _assert_samples(project.samples, prj.samples)


    def test_inclusion(self):
        pass


    def test_exclusion(self):
        pass


    def test_restoration(self):
        pass



def _assert_samples(expected_samples, observed_samples):
    assert len(expected_samples) == len(observed_samples)
    assert all(map(lambda (s1, s2): s1.name == s2.name,
                   zip(expected_samples, observed_samples)))


def _assert_sample_names(expected_names, observed_samples):
    assert all(map(lambda s: isinstance(s, Sample), observed_samples))
    assert set(expected_names) == {s.name for s in observed_samples}
