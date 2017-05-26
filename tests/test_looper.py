"""Initial, broad-scope looper tests.

Along with tests/tests.py, this is one of the initial unit test modules.
The primary function under test here is the creation of a project instance.

"""

from functools import partial
import logging
import os

import numpy.random as nprand
import pytest
import yaml

import looper.models
from looper.models import AttributeDict, ATTRDICT_METADATA, COL_KEY_SUFFIX

from .conftest import \
    DERIVED_COLNAMES, EXPECTED_MERGED_SAMPLE_FILES, FILE_BY_SAMPLE, \
    LOOPER_ARGS_BY_PIPELINE, MERGED_SAMPLE_INDICES, NGS_SAMPLE_INDICES, \
    NUM_SAMPLES, PIPELINE_TO_REQD_INFILES_BY_SAMPLE


_LOGGER = logging.getLogger("looper.{}".format(__name__))



@pytest.mark.usefixtures("write_project_files")
class ProjectConstructorTest:

    # TODO: docstrings and atomicity/encapsulation.
    # TODO: conversion to pytest for consistency.


    @pytest.mark.parametrize(argnames="attr_name",
                             argvalues=["required_inputs", "all_input_attr"])
    def test_sample_required_inputs_not_set(self, proj, attr_name):
        """ Samples' inputs are not set in `Project` ctor. """
        # TODO: update this to check for null if design is changed as may be.
        with pytest.raises(AttributeError):
            getattr(proj.samples[nprand.randint(len(proj.samples))], attr_name)


    @pytest.mark.parametrize(argnames="sample_index",
                             argvalues=MERGED_SAMPLE_INDICES)
    def test_merge_samples_positive(self, proj, sample_index):
        """ Samples annotation lines say only sample 'b' should be merged. """
        assert proj.samples[sample_index].merged


    @pytest.mark.parametrize(argnames="sample_index",
                             argvalues=set(range(NUM_SAMPLES)) -
                                       MERGED_SAMPLE_INDICES)
    def test_merge_samples_negative(self, proj, sample_index):
        assert not proj.samples[sample_index].merged


    @pytest.mark.parametrize(argnames="sample_index",
                             argvalues=MERGED_SAMPLE_INDICES)
    def test_data_sources_derivation(self, proj, sample_index):
        """ Samples in merge file, check data_sources --> derived_columns. """
        # Make sure these columns were merged:
        merged_columns = filter(
                lambda col_key: (col_key != "col_modifier") and
                                not col_key.endswith(COL_KEY_SUFFIX),
                proj.samples[sample_index].merged_cols.keys()
        )
        # Order may be lost due to mapping.
        # We don't care about that here, or about duplicates.
        assert set(DERIVED_COLNAMES) == set(merged_columns)


    @pytest.mark.parametrize(argnames="sample_index",
                             argvalues=MERGED_SAMPLE_INDICES)
    def test_derived_columns_merge_table_sample(self, proj, sample_index):
        """ Make sure derived columns works on merged table. """
        observed_merged_sample_filepaths = \
            [os.path.basename(f) for f in
             proj.samples[sample_index].file2.split(" ")]
        assert EXPECTED_MERGED_SAMPLE_FILES == \
               observed_merged_sample_filepaths


    @pytest.mark.parametrize(argnames="sample_index",
                             argvalues=set(range(NUM_SAMPLES)) -
                                       MERGED_SAMPLE_INDICES)
    def test_unmerged_samples_lack_merged_cols(self, proj, sample_index):
        """ Samples not in the `merge_table` lack merged columns. """
        # Assert the negative to cover empty dict/AttributeDict/None/etc.
        assert not proj.samples[sample_index].merged_cols


    @pytest.mark.parametrize(argnames="sample_index",
                             argvalues=range(NUM_SAMPLES))
    def test_multiple_add_sample_sheet_calls_no_rederivation(self, proj,
                                                             sample_index):
        """ Don't rederive `derived_columns` for multiple calls. """
        expected_files = FILE_BY_SAMPLE[sample_index]
        def _observed(p):
            return [os.path.basename(f)
                    for f in p.samples[sample_index].file.split(" ")]
        assert expected_files == _observed(proj)
        proj.add_sample_sheet()
        proj.add_sample_sheet()
        assert expected_files == _observed(proj)
        proj.add_sample_sheet()
        assert expected_files == _observed(proj)


    def test_duplicate_derived_columns_still_derived(self, proj):
        sample_index = 2
        observed_nonmerged_col_basename = \
            os.path.basename(proj.samples[sample_index].nonmerged_col)
        assert "c.txt" == observed_nonmerged_col_basename
        assert "" == proj.samples[sample_index].locate_data_source('file')



@pytest.mark.usefixtures("write_project_files", "pipe_iface_config_file")
class SampleWrtProjectCtorTests:
    """ Tests for `Sample` related to `Project` construction """


    @pytest.mark.parametrize(
            argnames="sample_index",
            argvalues=(set(range(NUM_SAMPLES)) - NGS_SAMPLE_INDICES)
    )
    def test_required_inputs(self, proj, pipe_iface, sample_index):
        """ A looper Sample's required inputs are based on pipeline. """
        # Note that this is testing only the non-NGS samples for req's inputs.
        expected_required_inputs = \
            PIPELINE_TO_REQD_INFILES_BY_SAMPLE["testpipeline.sh"][sample_index]
        sample = proj.samples[sample_index]
        sample.set_pipeline_attributes(pipe_iface, "testpipeline.sh")
        observed_required_inputs = [os.path.basename(f)
                                    for f in sample.required_inputs]
        assert expected_required_inputs == observed_required_inputs
        assert sample.confirm_required_inputs()


    @pytest.mark.parametrize(argnames="sample_index",
                             argvalues=NGS_SAMPLE_INDICES)
    def test_ngs_pipe_ngs_sample(self, proj, pipe_iface, sample_index):
        """ NGS pipeline with NGS input works just fine. """
        sample = proj.samples[sample_index]
        sample.set_pipeline_attributes(pipe_iface, "testngs.sh")
        expected_required_input_basename = \
            os.path.basename(
                PIPELINE_TO_REQD_INFILES_BY_SAMPLE["testngs.sh"]
                                                  [sample_index][0])
        observed_required_input_basename = \
            os.path.basename(sample.required_inputs[0])
        assert sample.confirm_required_inputs()
        assert 1 == len(sample.required_inputs)
        assert expected_required_input_basename == \
               observed_required_input_basename


    @pytest.mark.parametrize(
            argnames="sample_index",
            argvalues=set(range(NUM_SAMPLES)) - NGS_SAMPLE_INDICES)
    @pytest.mark.parametrize(
            argnames="permissive", argvalues=[False, True],
            ids=lambda permissive: "permissive={}".format(permissive))
    def test_ngs_pipe_non_ngs_sample(
            self, proj, pipe_iface, sample_index, permissive, tmpdir):
        """ An NGS-dependent pipeline with non-NGS sample(s) is dubious. """

        # Based on the test case's parameterization,
        # get the sample and create the function call to test.
        sample = proj.samples[sample_index]
        kwargs = {"pipeline_interface": pipe_iface,
                  "pipeline_name": "testngs.sh",
                  "permissive": permissive}
        test_call = partial(sample.set_pipeline_attributes, **kwargs)

        # Permissiveness parameter determines whether
        # there's an exception or just an error message.
        if not permissive:
            with pytest.raises(TypeError):
                test_call()
        else:
            # Log to a file just for this test.

            # Get a logging handlers snapshot so that we can ensure that
            # we've successfully reset logging state upon test conclusion.
            import copy
            pre_test_handlers = copy.copy(looper.models._LOGGER.handlers)

            # Control the format to enable assertions about message content.
            logfile = tmpdir.join("captured.log").strpath
            capture_handler = logging.FileHandler(logfile, mode='w')
            logmsg_format = "{%(name)s} %(module)s:%(lineno)d [%(levelname)s] > %(message)s "
            capture_handler.setFormatter(logging.Formatter(logmsg_format))
            capture_handler.setLevel(logging.ERROR)
            looper.models._LOGGER.addHandler(capture_handler)

            # Execute the actual call under test.
            test_call()

            # Read the captured, logged lines and make content assertion(s).
            with open(logfile, 'r') as captured:
                loglines = captured.readlines()
            assert 1 == len(loglines)
            assert "ERROR" in loglines[0]

            # Remove the temporary handler and assert that we've reset state.
            del looper.models._LOGGER.handlers[-1]
            assert pre_test_handlers == looper.models._LOGGER.handlers


    @pytest.mark.parametrize(
            argnames="pipeline,expected",
            argvalues=list(LOOPER_ARGS_BY_PIPELINE.items()))
    def test_looper_args_usage(self, pipe_iface, pipeline, expected):
        """ Test looper args usage flag. """
        observed = pipe_iface.uses_looper_args(pipeline)
        assert (expected and observed) or not (observed or expected)



@pytest.mark.usefixtures("write_project_files")
class SampleRoundtripTests:
    """ Test equality of objects written to and from YAML files. """


    def test_default_behavioral_metadata_retention(self, tmpdir, proj):
        """ With default metadata, writing to file and restoring is OK. """
        tempfolder = str(tmpdir)
        sample_tempfiles = []
        for sample in proj.samples:
            path_sample_tempfile = os.path.join(tempfolder,
                                                "{}.yaml".format(sample.name))
            sample.to_yaml(path_sample_tempfile)
            sample_tempfiles.append(path_sample_tempfile)
        for original_sample, temp_sample_path in zip(proj.samples,
                                                     sample_tempfiles):
            with open(temp_sample_path, 'r') as sample_file:
                restored_sample_data = yaml.load(sample_file)
            ad = AttributeDict(restored_sample_data)
            self._metadata_equality(original_sample.prj, ad)


    def test_modified_behavioral_metadata_preservation(self, tmpdir, proj):
        """ Behavior metadata modifications are preserved to/from disk. """
        tempfolder = str(tmpdir)
        sample_tempfiles = []
        samples = proj.samples
        assert 1 < len(samples), "Too few samples: {}".format(len(samples))

        # TODO: note that this may fail if metadata
        # modification prohibition is implemented.
        samples[0].prj.__dict__["_force_nulls"] = True
        samples[1].prj.__dict__["_attribute_identity"] = True

        for sample in proj.samples[:2]:
            path_sample_tempfile = os.path.join(tempfolder,
                                                "{}.yaml".format(sample.name))
            sample.to_yaml(path_sample_tempfile)
            sample_tempfiles.append(path_sample_tempfile)

        with open(sample_tempfiles[0], 'r') as f:
            sample_0_data = yaml.load(f)
        assert AttributeDict(sample_0_data).prj._force_nulls is True

        with open(sample_tempfiles[1], 'r') as f:
            sample_1_data = yaml.load(f)
        sample_1_restored_attrdict =  AttributeDict(sample_1_data)
        assert sample_1_restored_attrdict.prj.does_not_exist == "does_not_exist"


    def _check_nested_metadata(self, original, restored):
        """
        Check equality for metadata items, accounting for nesting within
        instances of AttributeDict and its child classes.

        :param AttributeDict original: original AttributeDict (or child) object
        :param AttributeDict restored: instance restored from writing
            original object to file, then reparsing and constructing
            AttributeDict instance
        :return bool: whether metadata items are equivalent between objects
            at all nesting levels
        """
        for key, data in original.items():
            if key not in restored:
                return False
            equal_level = self._metadata_equality(original, restored)
            if not equal_level:
                return False
            if isinstance(original, AttributeDict):
                return isinstance(restored, AttributeDict) and \
                       self._check_nested_metadata(data, restored[key])
            else:
                return True


    @staticmethod
    def _metadata_equality(original, restored):
        """
        Check nested levels of metadata equality.

        :param AttributeDict original: a raw AttributeDict or an
            instance of a child class that was serialized and written to disk
        :param AttributeDict restored: an AttributeDict instance created by
            parsing the file associated with the original object
        :return bool: whether all metadata keys/items have equal value
            when comparing original object to restored version
        """
        for metadata_item in ATTRDICT_METADATA:
            if metadata_item not in original or \
                    metadata_item not in restored or \
                    original[metadata_item] != restored[metadata_item]:
                return False
        return True



@pytest.mark.skip("Not implemented")
class RunErrorReportTests:
    """ Tests for aggregation of submission failures. """
    pass
