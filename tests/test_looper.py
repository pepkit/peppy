"""Initial, broad-scope looper tests.

Along with tests/tests.py, this is one of the initial unit test modules.
The primary function under test here is the creation of a project instance.

"""

from collections import defaultdict
from functools import partial
import itertools
import logging
import os
import random

import numpy.random as nprand
import pytest
import yaml

from looper.looper import aggregate_exec_skip_reasons
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
        expected = set(DERIVED_COLNAMES)
        observed = set(merged_columns)
        assert expected == observed


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


    def test_duplicate_derived_columns_still_derived(self, proj):
        sample_index = 2
        observed_nonmerged_col_basename = \
            os.path.basename(proj.samples[sample_index].nonmerged_col)
        assert "c.txt" == observed_nonmerged_col_basename
        assert "" == proj.samples[sample_index].locate_data_source(
                proj.data_sources, 'file')



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
        error_type, error_message = sample.determine_missing_requirements()
        assert error_type is None and not error_message


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
        error_type, error_message = sample.determine_missing_requirements()
        assert error_type is None and not error_message
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



class RunErrorReportTests:
    """ Tests for aggregation of submission failures. """

    SKIP_REASONS = ["Missing attribute.", "No metadata.",
                    "No config file.", "Missing input(s)."]
    SAMPLE_NAMES = {"Kupffer-control", "Kupffer-hepatitis",
                    "microglia-control", "microglia-cancer",
                    "Teff", "Treg", "Tmem",
                    "MC-circ", "Mac-tissue-res"}


    @pytest.mark.parametrize(
            argnames="empty_skips",
            argvalues=[tuple(), set(), list(), dict()])
    def test_no_failures(self, empty_skips):
        """ Aggregation step returns empty collection for no-fail case. """
        assert defaultdict(list) == aggregate_exec_skip_reasons(empty_skips)


    def test_many_samples_once_each_few_failures(self):
        """ One/few reasons for several/many samples, one skip each. """

        # Looping is to boost confidence from randomization.
        # We don't really want each case to be a parameterization.
        for reasons in itertools.combinations(self.SKIP_REASONS, 2):
            original_reasons = []
            expected = defaultdict(list)

            # Choose one or both reasons as single-fail for this sample.
            for sample in self.SAMPLE_NAMES:
                this_sample_reasons = nprand.choice(
                    reasons, size=nprand.choice([1, 2]), replace=False)
                for reason in this_sample_reasons:
                    expected[reason].append(sample)
                original_reasons.append((this_sample_reasons, sample))

            observed = aggregate_exec_skip_reasons(original_reasons)
            assert expected == observed


    def test_same_skip_same_sample(self):
        """ Multiple submission skips for one sample collapse by reason. """

        # Designate all-but-one of the failure reasons as the observations.
        for failures in itertools.combinations(
                self.SKIP_REASONS, len(self.SKIP_REASONS) - 1):

            # Build up the expectations and the input.
            all_skip_reasons = []

            # Randomize skip/fail count for each reason.
            for skip in failures:
                n_skip = nprand.randint(low=2, high=5, size=1)[0]
                all_skip_reasons.extend([skip] * n_skip)

            # Aggregation is order-agnostic...
            random.shuffle(all_skip_reasons)
            original_skip_reasons = [(all_skip_reasons, "control-sample")]
            # ...and maps each reason to pair of sample and count.
            expected_aggregation = {skip: ["control-sample"]
                                    for skip in set(all_skip_reasons)}

            # Validate.
            observed_aggregation = aggregate_exec_skip_reasons(
                    original_skip_reasons)
            assert expected_aggregation == observed_aggregation
