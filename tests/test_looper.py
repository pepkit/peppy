"""Initial, broad-scope looper tests.

Along with tests/tests.py, this is one of the initial unit test modules.
The primary function under test here is the creation of a project instance.

"""

import logging
import os
import pytest
import numpy.random as nprand

from looper.models import COL_KEY_SUFFIX

from conftest import \
    DERIVED_COLNAMES, EXPECTED_MERGED_SAMPLE_FILES, \
    FILE_BY_SAMPLE, MERGED_SAMPLE_INDICES, NGS_SAMPLE_INDICES, \
    NUM_SAMPLES, PIPELINE_TO_REQD_INFILES_BY_SAMPLE


_LOGGER = logging.getLogger(__name__)



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
        # Make sure derived columns works on merged table.
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



    @pytest.mark.parametrize(argnames="sample_index",
                             argvalues=set(range(NUM_SAMPLES)) -
                                       NGS_SAMPLE_INDICES)
    def test_ngs_pipe_non_ngs_sample(self, proj, pipe_iface, sample_index):
            sample = proj.samples[sample_index]
            with pytest.raises(TypeError):
                sample.set_pipeline_attributes(pipe_iface, "testngs.sh")
