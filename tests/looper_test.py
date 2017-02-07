"""Initial, broad-scope looper tests.

Along with tests/tests.py, this is one of the initial unit test modules.
The primary function under test here is the creation of a project instance.

"""

import os
import pytest
from looper import setup_looper_logger
from looper.models import Project
from looper.models import PipelineInterface


class LooperTest("project_config_file"):

	# TODO: docstrings and atomicity/encapsulation.
	# TODO: conversion to pytest for consistency.


	def setUp(self):
		# TODO: embed file data as string literal here or in a data/resources directory.
		# TODO: write the file as a classmethod; keep Project() generation from that data a test instance method
		# TODO: determine why the pandas CSV read call is failing here due to lack of columns to read.
		p = Project(os.path.expandvars("tests/test_config.yaml"))
		self.p = p

		# TODO: similarly, file writing as classmethod from embedded string literal data, keeping interface instantiation as test instance method.
		pi = PipelineInterface(os.path.expandvars("tests/pipelines/config/pipeline_interface.yaml"))
		self.pi = pi

	def test1(self):
		p = self.p  # for convenience
		pi = self.pi

		# Should not be set yet.
		with self.assertRaises(AttributeError):
			p.samples[2].required_inputs
		with self.assertRaises(AttributeError):
			p.samples[1].all_inputs_attr

		self.assertFalse(self.p.samples[0].merged)
		self.assertTrue(self.p.samples[1].merged)

		#print(self.p.samples[1].merged_cols)

		# Make sure these columns were merged:
		[x in p.samples[1].merged_cols.keys() for x in ["file2", "dcol1", "file"]]
		# Make sure derived columns works on merged table.
		self.assertEqual([os.path.basename(x) for x in p.samples[1].file2.split(" ")],  ['b1.txt', 'b2.txt', 'b3.txt'])

		# This sample should not have any merged columns
		self.assertEqual(len(p.samples[2].merged_cols.keys()), 0)

		s = p.samples[0]
		s.set_pipeline_attributes(pi, "testpipeline.sh")
		self.assertEqual([os.path.basename(x) for x in s.required_inputs], ['a.txt', 'a.txt'])

		s2 = p.samples[2]
		s2.set_pipeline_attributes(pi, "testpipeline.sh")
		s2.required_inputs
		self.assertTrue(s2.confirm_required_inputs())
		self.assertEqual([os.path.basename(x) for x in s2.required_inputs], ['c.txt', 'c.txt'])

		# Make sure derived cols don't get re-derived upon multiple calls of add_sample_sheet()
		self.assertEqual(p.samples[2].file, "tests/data/c.txt")
		p.add_sample_sheet()
		p.add_sample_sheet()
		self.assertEqual(p.samples[2].file, "tests/data/c.txt")

		# Check that duplicate derived cols can still be derived
		self.assertEqual(p.samples[2].nonmerged_col, "tests/data/c.txt")
		self.assertEqual(p.samples[2].locate_data_source('file'), "")


		# Can't set a non-ngs sample to an ngs pipeline
		with self.assertRaises(TypeError):
			s.set_pipeline_attributes(pi, "testngs.sh")

		# But it works for this NGS sample:
		s3 = p.samples[3]
		s3.set_pipeline_attributes(pi, "testngs.sh")
		s3.required_inputs
		s3.confirm_required_inputs()
		self.assertEqual(os.path.basename(s3.required_inputs[0]), "d-bamfile.bam")
		self.assertTrue(s3.confirm_required_inputs())








if __name__ == '__main__':
	setup_looper_logger()
	unittest.main()

