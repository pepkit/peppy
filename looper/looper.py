#!/usr/bin/env python

"""
Looper

Looper loops through samples and submits pipelines for them.
https://github.com/epigen/looper
"""

import sys
import os
import subprocess
from argparse import ArgumentParser
import glob
import errno
import re
import time
import pandas as _pd

try:
	from .models import Project, PipelineInterface, ProtocolMapper
except:
	sys.path.append(os.path.join(os.path.dirname(__file__), "looper"))
	from looper.models import Project, PipelineInterface, ProtocolMapper


def parse_arguments():
	"""
	Argument Parsing.
	"""
	description = "%(prog)s - Loops through samples and submits pipelines for them."
	epilog = "For command line options of each command, type: %(prog)s COMMAND -h"
	epilog += "\nhttps://github.com/epigen/looper"

	parser = ArgumentParser(description=description, epilog=epilog)
	parser.add_argument("--version", action="version", version="%(prog)s " + "get version")
	subparsers = parser.add_subparsers(dest='command')

	# Run command
	run_subparser = subparsers.add_parser(
		"run", help="Main Looper function: Submit jobs for samples.")
	run_subparser.add_argument(
		'-t', '--time-delay', dest='time_delay', type=int,
		help="Time delay in seconds between job submissions.", default=0)
	run_subparser.add_argument(
		'--ignore-flags', dest="ignore_flags", action="store_true",
		default=False,
		help="Ignore run status flags? Default: false. By default, pipelines \
			will not be submitted if a pypiper flag file exists marking the \
			run (e.g. as 'running' or 'failed'). \
			Set this option to ignore flags and submit the runs anyway.")
	run_subparser.add_argument('-pd', dest='partition', default="longq")  # this should be changed in near future

	# Summarize command
	summarize_subparser = subparsers.add_parser(
		"summarize", help="Summarize statistics of project samples.")

	# Destroy command
	destroy_subparser = subparsers.add_parser(
		"destroy", help="Remove all files of the project.")

	# Common arguments
	for subparser in [run_subparser, summarize_subparser, destroy_subparser]:
		subparser.add_argument(
			'--file-checks', dest='file_checks', action='store_false',
			help="Perform input file checks. Default=True.", default=True)
		subparser.add_argument(
			'-d', '--dry-run', dest='dry_run', action='store_true',
			help="Don't actually submit.", default=False)
		subparser.add_argument(
			'--sp', dest='subproject', type=str,
			help="Supply subproject", default=None)
		subparser.add_argument(
			dest='config_file', type=str,
			help="Project YAML config file.")

	# To enable the loop to pass args directly on to the pipelines...
	args, remaining_args = parser.parse_known_args()

	if len(remaining_args) > 0:
		print("Remaining arguments passed to pipelines: {}".format(" ".join([str(x) for x in remaining_args])))

	return args, remaining_args


def run(prj, args, remaining_args):
	"""
	Main Looper function: Submit jobs for samples in project.
	"""

	# Look up the looper config files:
	pipeline_interface_file = os.path.join(prj.paths.pipelines_dir, "config/pipeline_interface.yaml")

	print("Pipeline interface config: " + pipeline_interface_file)
	pipeline_interface = PipelineInterface(pipeline_interface_file)

	protocol_mappings_file = os.path.join(prj.paths.pipelines_dir, "config/protocol_mappings.yaml")
	print("Protocol mappings config: " + protocol_mappings_file)
	protocol_mappings = ProtocolMapper(protocol_mappings_file)

	# upate to project-specific protocol mappings
	if hasattr(prj, "protocol_mappings"):
		protocol_mappings.mappings.update(prj.protocol_mappings.__dict__)

	# Keep track of how many jobs have been submitted.
	submit_count = 0
	job_count = 0
	sample_count = 0
	# keep track of submited samples
	sample_total = len(prj.samples)
	prj.processed_samples = list()

	# Create a few problem lists so we can keep track and show them at the end
	failures = []

	for sample in prj.samples:
		sample_count += 1
		sys.stdout.write("### [" + str(sample_count) + " of " + str(sample_total) + "] " + sample.sample_name + "\t")
		pipeline_outfolder = os.path.join(prj.paths.results_subdir, sample.sample_name)

		fail = False
		fail_message = ""

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
		if hasattr(sample, "read_type"):
			# drop "-end", "_end", or just "end" from the end of the column value:
			sample.read_type = re.sub('[_\\-]?end$', '', str(sample.read_type)).lower()
			if sample.read_type not in ["single", "paired"]:
				fail_message += "read_type must be either 'single' or 'paired'."
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

		# Get the base protocol-to-pipeline mappings
		pipelines = protocol_mappings.build_pipeline(sample.library.upper())

		# We require that the pipelines and config files live in
		# a subdirectory called 'pipelines' -- is this the best way?
		pipelines_subdir = "pipelines"

		# Go through all pipelines to submit for this protocol
		for pipeline in pipelines:
			print("Pipeline: " + pipeline)
			# discard any arguments to get just the (complete) script name,
			# which is the key in the pipeline interface
			pl_id = str(pipeline).split(" ")[0]
			# Identify the cluster resources we will require for this submission
			submit_settings = pipeline_interface.choose_resource_package(pl_id, input_file_size)

			# Pipeline name is the key used for flag checking
			pl_name = pipeline_interface.get_pipeline_name(pl_id)

			# Build basic command line string
			base_pipeline_script = os.path.join(prj.paths.pipelines_dir, pipelines_subdir, pipeline)
			cmd = os.path.join(prj.paths.pipelines_dir, pipelines_subdir, pipeline)

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
			if hasattr(prj.pipeline_config, pipeline):
				# First priority: pipeline config specified in project config
				pl_config_file = getattr(prj.pipeline_config, pipeline)
				if pl_config_file:  # make sure it's not null (which it could be provided as null)
					if not os.path.isfile(pl_config_file):
						print("Pipeline config file specified but not found: " + pl_config_file)
						raise IOError(pl_config_file)
					print("Found config file:" + getattr(prj.pipeline_config, pipeline))
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
			submit_settings["JOBNAME"] = sample.sample_name + "_" + pipeline
			submit_settings["CODE"] = cmd

			# Submit job!
			job_count += 1
			submit_count += cluster_submit(
				sample, prj.compute.submission_template,
				prj.compute.submission_command, submit_settings,
				prj.paths.submission_subdir, pipeline_outfolder, pl_name, args.time_delay,
				submit=True, dry_run=args.dry_run, ignore_flags=args.ignore_flags,
				remaining_args=remaining_args)

		msg = "\nLooper finished (" + str(submit_count) + " of " + str(job_count) + " jobs submitted)."
		if args.dry_run:
			msg += " Dry run. No jobs were actually submitted"

		print(msg)

		if (len(failures) > 0):
			print("Failure count: " + str(len(failures)) + ". Reasons for failure:")
			# print(failures)

			from collections import defaultdict
			groups = defaultdict(str)
			for msg, sample_name in failures:
				groups[msg] += sample_name + "; "

			for name, values in groups.iteritems():
				print("  " + str(name) + ":" + str(values))


def summarize(prj):
	"""
	Grabs the report_results stats files from each sample,
	and collates them into a single matrix (as a csv file)
	"""
	import csv
	columns = []
	stats = []

	for sample in prj.samples:
		sys.stdout.write("### " + sample.sample_name + "\t")
		pipeline_outfolder = os.path.join(prj.paths.results_subdir, sample.sample_name)

		# Grab the basic info from the annotation sheet for this sample.
		# This will correspond to a row in the output.
		sample_stats = sample.get_sheet_dict()
		columns.extend(sample_stats.keys())
		# Version 0.3 standardized all stats into a single file
		stats_file = os.path.join(pipeline_outfolder, "stats.tsv")
		if os.path.isfile(stats_file):
			print('Found: ' + stats_file)
		else:
			continue  # raise Exception(stat_file_path + " : file does not exist!")

		t = _pd.read_table(stats_file, header=None, names=['key', 'value', 'pl'])

		t.drop_duplicates(subset=['key', 'pl'], keep='last', inplace=True)
		# t.duplicated(subset= ['key'], keep = False)

		t.loc[:, 'plkey'] = t['pl'] + ":" + t['key']
		dupes = t.duplicated(subset=['key'], keep=False)
		t.loc[dupes, 'key'] = t.loc[dupes, 'plkey']

		sample_stats.update(t.set_index('key')['value'].to_dict())
		stats.append(sample_stats)
		columns.extend(t.key.tolist())

	# all samples are parsed. Produce file.

	tsv_outfile_path = os.path.join(prj.paths.output_dir, prj.name)
	if prj.subproject:
		tsv_outfile_path += '_' + prj.subproject
	tsv_outfile_path += '_stats_summary.tsv'

	tsv_outfile = open(tsv_outfile_path, 'w')

	tsv_writer = csv.DictWriter(tsv_outfile, fieldnames=uniqify(columns), delimiter='\t', extrasaction='ignore')
	tsv_writer.writeheader()

	for row in stats:
		tsv_writer.writerow(row)

	tsv_outfile.close()

	print("Summary (n=" + str(len(stats)) + "): " + tsv_outfile_path)

	# 	# There may be multiple pipeline outputs to consider.
	# 	globs = glob.glob(os.path.join(pipeline_outfolder, "*stats.tsv"))
	# 	print(globs)

	# 	for stats_filename in globs: # = os.path.join(pipeline_outfolder, pl_name, "_stats.tsv")
	# 		pl_name = re.search(".*/(.*)_stats.tsv", stats_filename, re.IGNORECASE).group(1)
	# 		print(pl_name)
	# 		# Make sure file exists
	# 		if os.path.isfile(stats_filename):
	# 			stat_file = open(stats_filename, 'rb')
	# 			print('Found: ' + stats_filename)
	# 		else:
	# 			pass # raise Exception(stat_file_path + " : file does not exist!")

	# 		# Initialize column list for this pipeline if it hasn't been done.
	# 		if not columns.has_key(pl_name):
	# 			columns[pl_name] = []
	# 		if not stats.has_key(pl_name):
	# 			stats[pl_name] = []

	# 		# add all sample attributes?
	# 		#row.update(sample.__dict__)
	# 		#row = sample.__dict__
	# 		row = sample.get_sheet_dict()
	# 		for line in stat_file:
	# 			key, value = line.split('\t')
	# 			row[key] = value.strip()

	# 		# Add these items as column names for this pipeline
	# 		# Use extend instead of append because we're adding a [list] and not items.
	# 		columns[pl_name].extend(row.keys())
	# 		#print(columns[pl_name])
	# 		stats[pl_name].append(row)

	# # For each pipeline, write a summary tsv file.
	# for pl_name, cols in columns.items():
	# 	tsv_outfile_path = os.path.join(prj.paths.output_dir, prj.name)
	# 	if prj.subproject:
	# 		tsv_outfile_path += '_' + prj.subproject
	# 	tsv_outfile_path += '_' + pl_name + '_stats_summary.tsv'

	# 	tsv_outfile = open(tsv_outfile_path, 'w')

	# 	tsv_writer = csv.DictWriter(tsv_outfile, fieldnames=uniqify(cols), delimiter='\t')
	# 	tsv_writer.writeheader()

	# 	for row in stats[pl_name]:
	# 		tsv_writer.writerow(row)

	# 	tsv_outfile.close()

	# 	print("Pipeline " + pl_name + " summary (n=" + str(len(stats[pl_name])) + "): " + tsv_outfile_path)


def destroy(prj, args):
	"""
	"""
	if not query_yes_no("Are you sure you want to permanently delete all pipeline results for this project?"):
		print("Destroy action aborted by user.")
		return 1
	else:
		for sample in prj.samples:
			sys.stdout.write("### " + sample.sample_name + "\t")
			pipeline_outfolder = os.path.join(prj.paths.results_subdir, sample.sample_name)
			clean_project(pipeline_outfolder, args)
		return 0


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
	submit=False, dry_run=False, ignore_flags=False, remaining_args=list()):
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

	# Check if job is already submitted (unless ignore_flags is set to True)
	if not ignore_flags:
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
	"""
	Ask a yes/no question via raw_input() and return their answer.

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


def clean_project(pipeline_outfolder, args):
	"""
	This function will delete all results for this project
	"""
	import shutil
	if os.path.exists(pipeline_outfolder):
		if args.dry_run:
			print("DRY RUN. I would have removed: " + pipeline_outfolder)
		else:
			print("Removing: " + pipeline_outfolder)
			shutil.rmtree(pipeline_outfolder)
	else:
		print(pipeline_outfolder + " does not exist.")


def uniqify(seq):
	"""
	Fast way to uniqify while preserving input order.
	"""
	# http://stackoverflow.com/questions/480214/
	seen = set()
	seen_add = seen.add
	return [x for x in seq if not (x in seen or seen_add(x))]


def main():
	# Parse command-line arguments
	args, remaining_args = parse_arguments()

	# Initialize project
	prj = Project(args.config_file, args.subproject, file_checks=args.file_checks)
	# add sample sheet
	prj.add_sample_sheet()

	print("Results subdir: " + prj.paths.results_subdir)
	print("Command: " + args.command)

	if args.command == "run":
		run(prj, args, remaining_args)

	if args.command == "destroy":
		return destroy(prj, args)

	if args.command == "summarize":
		summarize(prj)


if __name__ == '__main__':
	try:
		sys.exit(main())
	except KeyboardInterrupt:
		print("Program canceled by user!")
		sys.exit(1)
