""" Tests for interaction between a Project and a Sample. """

from collections import OrderedDict
import copy
import itertools
import os
import random

import pandas as pd
import pytest
import yaml

from peppy import \
        Project, Sample, \
        SAMPLE_ANNOTATIONS_KEY, SAMPLE_NAME_COLNAME

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


# Arbitrary (but reasonable) path names/types to use to test
# Project construction behavior with respect to config file format.
PATH_BY_TYPE = {
    "output_dir": "temporary/sequencing/results",
    "results_subdir": "results",
    "submission_subdir": "submission",
    "input_dir": "dummy/sequencing/data",
    "tools_folder": "arbitrary-seq-tools-folder"}

NAME_ANNOTATIONS_FILE = "annotations.csv"
SAMPLE_NAMES = ["WGBS_mm10", "ATAC_mm10", "WGBS_rn6", "ATAC_rn6"]
PROTOCOL_COLNAME = "protocol"
COLUMNS = [SAMPLE_NAME_COLNAME, "val1", "val2", PROTOCOL_COLNAME]
VALUES1 = [random.randint(-5, 5) for _ in range(len(SAMPLE_NAMES))]
VALUES2 = [random.randint(-5, 5) for _ in range(len(SAMPLE_NAMES))]
PROTOCOLS = ["WGBS", "ATAC", "WGBS", "ATAC"]
DATA = list(zip(SAMPLE_NAMES, VALUES1, VALUES2, PROTOCOLS))
DATA_FOR_SAMPLES = [
    {SAMPLE_NAME_COLNAME: SAMPLE_NAMES},
    {"val1": VALUES1}, {"val2": VALUES2}, {PROTOCOL_COLNAME: PROTOCOLS}]
PROJECT_CONFIG_DATA = {"metadata": {"sample_annotation": NAME_ANNOTATIONS_FILE}}



def pytest_generate_tests(metafunc):
    """ Customization of test cases within this module. """
    protos = ["WGBS", "ATAC"]
    if metafunc.cls == BuildSheetTests:
        if "protocols" in metafunc.fixturenames:
            # Apply the test case to each of the possible combinations of
            # protocols, from none at all up to all of them.
            metafunc.parametrize(
                    argnames="protocols",
                    argvalues=list(itertools.chain.from_iterable(
                            itertools.combinations(protos, x)
                            for x in range(1 + len(protos)))),
                    ids=lambda ps: " protocols = {} ".format(",".join(ps)))
        if "delimiter" in metafunc.fixturenames:
            metafunc.parametrize(argnames="delimiter", argvalues=[",", "\t"])



@pytest.fixture(scope="function")
def proj_conf():
    """ Provide the basic configuration data. """
    return copy.deepcopy(PROJECT_CONFIG_DATA)



@pytest.fixture(scope="function")
def path_proj_conf_file(tmpdir, proj_conf):
    """ Write basic project configuration data and provide filepath. """
    conf_path = os.path.join(tmpdir.strpath, "project_config.yaml")
    with open(conf_path, 'w') as conf:
        yaml.safe_dump(proj_conf, conf)
    return conf_path



@pytest.fixture(scope="function")
def path_anns_file(request, tmpdir, sample_sheet):
    """ Write basic annotations, optionally using a different delimiter. """
    filepath = os.path.join(tmpdir.strpath, NAME_ANNOTATIONS_FILE)
    if "delimiter" in request.fixturenames:
        delimiter = request.getfixturevalue("delimiter")
    else:
        delimiter = ","
    with open(filepath, 'w') as anns_file:
        sample_sheet.to_csv(anns_file, sep=delimiter, index=False)
    return filepath



@pytest.fixture(scope="function")
def samples_rawdata():
    return copy.deepcopy(DATA)



@pytest.fixture(scope="function")
def sample_sheet(samples_rawdata):
    df = pd.DataFrame(samples_rawdata)
    df.columns = [SAMPLE_NAME_COLNAME, "val1", "val2", PROTOCOL_COLNAME]
    return df



@pytest.mark.usefixtures("write_project_files")
class SampleSheetAttrTests:
    """ Tests of properties of sample sheet attributes on a sample """

    def test_sheet_attr_order(self, proj):
        """ The sample's sheet attributes are ordered. """
        s = Sample(proj.sheet.iloc[0])
        d = s.get_sheet_dict()
        assert SAMPLE_NAME_COLNAME == list(d)[0]



def test_samples_are_generic(path_anns_file, path_proj_conf_file):
    """ Regardless of protocol, Samples for sheet are generic. """
    # Annotations filepath fixture is also writes that file, so
    # it's needed even though that return value isn't used locally.
    p = Project(path_proj_conf_file)
    assert len(SAMPLE_NAMES) == p.num_samples
    samples = list(p.samples)
    assert p.num_samples == len(samples)
    assert all([Sample is type(s) for s in samples])



class BuildSheetTests:
    """ Tests for construction of sheet of Project's Samples. """

    # Note: seemingly unused parameters may affect parameterization
    # logic of other fixtures used by a test case; tread lightly.

    def test_no_samples(self, protocols, delimiter, path_empty_project):
        """ Lack of Samples is unproblematic for the sheet build. """
        # Regardless of protocol(s), the sheet should be empty.
        p = Project(path_empty_project)
        sheet = p.build_sheet(*protocols)
        assert sheet.empty

    @pytest.mark.parametrize(
            argnames="which_sample_index", argvalues=range(len(SAMPLE_NAMES)))
    def test_single_sample(
            self, tmpdir, path_proj_conf_file, which_sample_index):
        """ Single Sample is perfectly valid for Project and sheet. """

        # Pull out the values for the current sample.
        values = DATA[which_sample_index]

        # Write the annotations.
        anns_path = os.path.join(tmpdir.strpath, NAME_ANNOTATIONS_FILE)
        with open(anns_path, 'w') as anns_file:
            anns_file.write("{}\n".format(",".join(COLUMNS)))
            anns_file.write("{}\n".format(",".join([str(v) for v in values])))

        # Build the sheet.
        p = Project(path_proj_conf_file)
        sheet = p.build_sheet()

        # It should be a single-row DataFrame.
        assert isinstance(sheet, pd.DataFrame)
        assert 1 == len(sheet)
        assert 1 == p.num_samples

        # There will be additional values added from the Project,
        # but the core data values will have remained the same.
        sample = list(p.samples)[0]
        for attr, exp_val in zip(COLUMNS, values):
            obs_val = getattr(sample, attr)
            try:
                assert exp_val == obs_val
            except AssertionError as e:
                try:
                    assert exp_val == int(obs_val)
                except AssertionError:
                    raise e

    def test_multiple_samples(
            self, protocols, path_anns_file, path_proj_conf_file):
        """ Project also processes multiple Sample fine. """

        p = Project(path_proj_conf_file)

        # Total sample count is constant.
        assert len(SAMPLE_NAMES) == sum(1 for _ in p.samples)

        # But the sheet permits filtering to specific protocol(s).
        exp_num_samples = len(SAMPLE_NAMES) if not protocols else \
            sum(sum(1 for p2 in PROTOCOLS if p2 == p1) for p1 in protocols)
        sheet = p.build_sheet(*protocols)
        assert exp_num_samples == len(sheet)

        if protocols:
            def as_expected(sd):
                return sd.protocol in set(protocols)
        else:
            def as_expected(sd):
                return sd.protocol not in set(protocols)

        for _, sample_data in sheet.iterrows():
            assert as_expected(sample_data)



class SampleFolderCreationTests:
    """ Tests for interaction between Project and Sample. """

    CONFIG_DATA_PATHS_HOOK = "uses_paths_section"
    EXPECTED_PATHS = {
            os.path.join(PATH_BY_TYPE[name], path) 
            if name in ["results_subdir", "submission_subdir"] 
            else path for name, path in PATH_BY_TYPE.items()}

    @pytest.mark.parametrize(
            argnames=CONFIG_DATA_PATHS_HOOK, argvalues=[False, True],
            ids=lambda has_paths: "paths_section={}".format(has_paths))
    @pytest.mark.parametrize(
            argnames="num_samples", argvalues=range(1, 4), 
            ids=lambda n_samples: "samples={}".format(n_samples))
    def test_sample_folders_creation(
            self, uses_paths_section, num_samples, project):
        """ Sample folders can be created regardless of declaration style. """

        # Not that the paths section usage flag and the sample count
        # are used by the project configuration fixture.

        assert not any([os.path.exists(path)
                        for s in project.samples for path in s.paths])
        for s in project.samples:
            s.make_sample_dirs()
            assert all([os.path.exists(path) for path in s.paths])



@pytest.fixture(scope="function")
def project(request, tmpdir, env_config_filepath):
    """ Provide requesting test case with a basic Project instance. """

    # Write just the sample names as the annotations.
    annotations_filename = "anns-fill.csv"
    anns_path = tmpdir.join(annotations_filename).strpath
    num_samples = request.getfixturevalue("num_samples")
    df = pd.DataFrame(OrderedDict(
        [(SAMPLE_NAME_COLNAME, ["sample{}".format(i) for i in range(num_samples)]),
         ("data", range(num_samples))]))
    with open(anns_path, 'w') as anns_file:
        df.to_csv(anns_file, sep="\t", index=False)

    # Create the Project config data.
    config_data = {"metadata": {SAMPLE_ANNOTATIONS_KEY: annotations_filename}}
    if request.getfixturevalue(request.cls.CONFIG_DATA_PATHS_HOOK):
        config_data["paths"] = {}
        paths_dest = config_data["paths"]
    else:
        paths_dest = config_data["metadata"]

    # Add the paths data to the Project config.
    for path_name, path in PATH_BY_TYPE.items():
        paths_dest[path_name] = os.path.join(tmpdir.strpath, path)

    # Write the Project config file.
    conf_path = tmpdir.join("proj-conf.yaml").strpath
    with open(conf_path, 'w') as conf_file:
        yaml.safe_dump(config_data, conf_file)

    return Project(conf_path, default_compute=env_config_filepath)



