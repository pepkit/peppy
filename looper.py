#!/usr/bin/env python

"""
This script creates a project and its samples,
submiting them to the appropriate pipeline.
"""

import sys
import os
import subprocess
from argparse import ArgumentParser
import glob
import errno
import re
import time

try:
	from .models import Project, PipelineInterface, ProtocolMapper
except:
	sys.path.append(os.path.join(os.path.dirname(__file__), "pipelines"))
	from pipelines.models import Project, PipelineInterface, ProtocolMapper


def parse_arguments():
	"""
	Argument Parsing.
	"""
	parser = ArgumentParser(description='Looper')

	parser.add_argument('-c', '--config-file', dest='conf_file', help="Supply config file [-c].")

	parser.add_argument('--sp', dest='subproject', help="Supply subproject", default=None)

	parser.add_argument('-d', '--dry-run', dest='dry_run', action='store_true', help="Don't actually submit.", default=False)

	parser.add_argument('-t', '--time-delay', dest='time_delay', type=int, help="Time delay in seconds between job submissions.", default=0)

	parser.add_argument('--file-checks', dest='file_checks', action='store_false', help="Perform input file checks. Default=True.", default=True)

	# this should be changed in near future
	parser.add_argument('-pd', dest='partition', default="longq")
	parser.add_argument('--cmd', dest='command', default="run")
	# args = parser.parse_args()
	# To enable the loop to pass args directly on to the pipelines...
	args, remaining_args = parser.parse_known_args()

	print("Remaining arguments passed to pipelines: " + str(remaining_args))

	if not args.conf_file:
		parser.print_help()  # or, print_usage() for less verbosity
		raise SystemExit

	return args, remaining_args


def get_file_size(filename):
	"""
	Get size of all files in string (space-separated) in gigabytes (Gb).
	"""
	return sum([float(os.stat(f).st_size) for f in filename.split(" ")]) / (1024 ** 3)


def make_sure_path_exists(path):
	"""
	Create directory if it does not exist.
	"""
	try:
		os.makedirs(path)
	except OSError as exception:
		if exception.errno != errno.EEXIST:
			raise


def cluster_submit(
	sample, submit_template, submission_command, variables_dict,
	submission_folder, pipeline_outfolder, pipeline_name, time_delay,
	submit=False, dry_run=False, remaining_args=list()):
	"""
	Submit job to cluster manager.
	"""
	# Some generic variables
	# Toss the file extension

	submit_script = os.path.join(submission_folder, sample.sample_name + "_" + pipeline_name + ".sub")
	submit_log = os.path.join(submission_folder, sample.sample_name + "_" + pipeline_name + ".log")
	variables_dict["LOGFILE"] = submit_log

	# Prepare and write submission script
	sys.stdout.write("\tSUBFILE: " + submit_script + " ")
	make_sure_path_exists(os.path.dirname(submit_script))
	# read in submit_template
	with open(submit_template, 'r') as handle:
		filedata = handle.read()
	# update variable dict with any additional arguments
	# print(variables_dict["CODE"] + " " + str(" ".join(remaining_args)))
	variables_dict["CODE"] += " " + str(" ".join(remaining_args))
	# fill in submit_template with variables
	for key, value in variables_dict.items():
		# Here we add brackets around the key names and use uppercase because
		# this is how they are encoded as variables in the submit templates.
		filedata = filedata.replace("{" + str(key).upper() + "}", str(value))
	# save submission file
	with open(submit_script, 'w') as handle:
		handle.write(filedata)

	# Prepare and write sample yaml object
	sample.to_yaml()

	# Check if job is already submitted
	flag_files = glob.glob(os.path.join(pipeline_outfolder, pipeline_name + "*.flag"))
	if (len(flag_files) > 0):
		print("Flag file found. Not submitting: " + str([os.path.basename(i) for i in flag_files]))
		submit = False
	else:
		pass
		# print("")  # Do you want to print a newline after every sample?

	if submit:
		if dry_run:
			print("\tDRY RUN: I would have submitted this")
			return 1
		else:
			subprocess.call(submission_command + " " + submit_script, shell=True)
			time.sleep(time_delay)  # sleep for `time_delay` seconds before submiting next job
			return 1
			# pass
	else:
		return 0


def query_yes_no(question, default="no"):
	"""Ask a yes/no question via raw_input() and return their answer.

	"question" is a string that is presented to the user.
	"default" is the presumed answer if the user just hits <Enter>.
		It must be "yes" (the default), "no" or None (meaning
		an answer is required of the user).

	The "answer" return value is True for "yes" or False for "no".
	"""
	valid = {
		"yes": True, "y": True, "ye": True,
		"no": False, "n": False}
	if default is None:
		prompt = " [y/n] "
	elif default == "yes":
		prompt = " [Y/n] "
	elif default == "no":
		prompt = " [y/N] "
	else:
		raise ValueError("invalid default answer: '%s'" % default)

	while True:
		sys.stdout.write(question + prompt)
		choice = raw_input().lower()
		if default is not None and choice == '':
			return valid[default]
		elif choice in valid:
			return valid[choice]
		else:
			sys.stdout.write(
				"Please respond with 'yes' or 'no' "
				"(or 'y' or 'n').\n")


def main():
	# Parse command-line arguments
	args, remaining_args = parse_arguments()

	# Keep track of how many jobs have been submitted.
	submit_count = 0
	job_count = 0
	# Initialize project
	prj = Project(args.conf_file, args.subproject, file_checks=args.file_checks)
	# add sample sheet
	prj.add_sample_sheet()
	# keep track of submited samples
	prj.processed_samples = list()

	# Look up the looper config files:
	pipeline_interface_file = os.path.join(prj.paths.pipelines_dir, "config/pipeline_interface.yaml")

	print("Pipeline interface config: " + pipeline_interface_file)
	pipeline_interface = PipelineInterface(pipeline_interface_file)

	protocol_mappings_file = os.path.join(prj.paths.pipelines_dir, "config/protocol_mappings.yaml")
	print("Protocol mappings config: " + protocol_mappings_file)
	protocol_mappings = ProtocolMapper(protocol_mappings_file)
	if args.command == "clean":
		if not query_yes_no("Are you sure you want to permanently delete all pipeline results for this project?"):
			print("Clean aborted by user.")
			sys.exit(1)

	# Create a few problem lists so we can keep track and show them at the end
	failures = []

	for sample in prj.samples:
		fail = False
		fail_message = ""
		sys.stdout.write("### " + sample.sample_name + "\t")
		pipeline_outfolder = os.path.join(prj.paths.results_subdir, sample.sample_name)

		if args.command == "clean":
			# Clean
			import shutil
			if os.path.exists(pipeline_outfolder):
				if args.dry_run:
					print("DRY RUN. I would have removed: " + pipeline_outfolder)
				else:
					print("Removing: " + pipeline_outfolder)
					shutil.rmtree(pipeline_outfolder)
			else:
				print(pipeline_outfolder + " does not exist.")

			continue

		# Don't submit samples with duplicate names
		if sample.sample_name in prj.processed_samples:
			fail_message += "Duplicate sample name. "
			fail = True

		# Check if sample should be run
		if hasattr(sample, "run"):
			if not sample.run:
				fail_message += "Run column deselected."
				fail = True

		# Check if single_or_paired value is recognized
		if hasattr(sample, "single_or_paired"):
			# drop "-end", "_end", or just "end" from the end of the column value:
			sample.single_or_paired = re.sub('[_\\-]?end$', '', sample.single_or_paired).lower()
			if sample.single_or_paired not in ["single", "paired"]:
				fail_message += "single_or_paired must be either 'single' or 'paired'."
				fail = True

		# Make sure the input data exists
		# this requires every input file (in case of merged samples) to exist.
		if not all(os.path.isfile(f) for f in sample.data_path.split(" ")):
			fail_message += "Sample input file does not exist."
			fail = True

		if fail:
			print("\nNot submitted: " + fail_message)
			failures.append([fail_message, sample.sample_name])
			continue

		# Otherwise, process the sample:
		prj.processed_samples.append(sample.sample_name)
		input_file_size = get_file_size(sample.data_path)
		print("({:.2f} Gb)".format(input_file_size))

		sample.to_yaml()

		# Get the base protocol to pipeline mappings
		pl_list = protocol_mappings.build_pipeline(sample.library.upper())

		# We require that the pipelines and config files live in
		# a subdirectory called 'pipelines' -- is this the best way?
		pipelines_subdir = "pipelines"

		# Go through all pipelines to submit for this protocol
		for pl in pl_list:
			print("Pipeline: " + pl)
			# discard any arguments to get just the (complete) script name,
			# which is the key in the pipeline interface
			pl_id = str(pl).split(" ")[0]
			# Identify the cluster resources we will require for this submission
			submit_settings = pipeline_interface.choose_resource_package(pl_id, input_file_size)

			# Pipeline name is the key used for flag checking
			pl_name = pipeline_interface.get_pipeline_name(pl_id)

			# Build basic command line string
			base_pipeline_script = os.path.join(prj.paths.pipelines_dir, pipelines_subdir, pl)
			cmd = os.path.join(prj.paths.pipelines_dir, pipelines_subdir, pl)

			# Append arguments for this pipeline
			# Sample-level arguments are handled by the pipeline interface.
			argstring = pipeline_interface.get_arg_string(pl_id, sample)
			argstring += " "  # space

			# Project-level arguments are handled by the project.
			argstring += prj.get_arg_string(pl_id)

			cmd += argstring

			# Project-level arguments (those that do not change for each sample)
			# must be handled separately.
			# These are looper_args, -C, -O, -M, and -P. If the pipeline implements
			# these arguments, then it should list looper_args=True and then we
			# should add the arguments to the command string.

			# Check for a pipeline config file
			if hasattr(prj.pipeline_config, pl):
				# First priority: pipeline config specified in project config
				pl_config_file = getattr(prj.pipeline_config, pl)
				if not os.path.isfile(pl_config_file):
					print("Pipeline config file specified but not found: " + pl_config_file)
					raise IOError(pl_config_file)
				print("Found config file:" + getattr(prj.pipeline_config, pl))
				# Append arg for config file if found
				cmd += " -C " + pl_config_file

			# Append output parent folder
			cmd += " -O " + prj.paths.results_subdir

			# Append arg for cores (number of processors to use)
			if submit_settings["cores"] > 1:
				cmd += " -P " + submit_settings["cores"]

			# Append arg for memory
			if submit_settings["mem"] > 1:
				cmd += " -M " + submit_settings["mem"]

			# Add the command string and job name to the submit_settings object
			submit_settings["JOBNAME"] = sample.sample_name + "_" + pl
			submit_settings["CODE"] = cmd

			# Submit job!
			job_count += 1
			submit_count += cluster_submit(
				sample, prj.compute.submission_template,
				prj.compute.submission_command, submit_settings,
				prj.paths.submission_subdir, pipeline_outfolder, pl_name, args.time_delay,
				submit=True, dry_run=args.dry_run, remaining_args=remaining_args)

	msg = "\nLooper finished. (" + str(submit_count) + " of " + str(job_count) + " jobs submitted)"
	if args.dry_run:
		msg += " Dry run. No jobs were actually submitted"

	print(msg)

	if (len(failures) > 0):
		print(failures)

if __name__ == '__main__':
	try:
		sys.exit(main())
	except KeyboardInterrupt:
		print("Program canceled by user!")
		sys.exit(1)
