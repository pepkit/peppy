#!/usr/bin/env python

"""
Looper

a pipeline submission engine.
https://github.com/epigen/looper
"""

import argparse
import errno
import glob
import logging
import os
import re
import subprocess
import sys
import time
import pandas as _pd
from . import setup_looper_logger

try:
	from .models import \
		Project, PipelineInterface, ProtocolMapper, LOOPERENV_VARNAME
except:
	sys.path.append(os.path.join(os.path.dirname(__file__), "looper"))
	from looper.models import \
		Project, PipelineInterface, ProtocolMapper, LOOPERENV_VARNAME


_LOGGER = logging.getLogger(__name__)


def parse_arguments():
	"""
	Argument Parsing.
	"""

	description = "%(prog)s - Loops through samples and submits pipelines for them."
	epilog = "For command line options of each command, type: %(prog)s COMMAND -h"
	epilog += "\nhttps://github.com/epigen/looper"

	parser = argparse.ArgumentParser(
		description=description, epilog=epilog,
		formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument("--version", action="version",
				  version="%(prog)s " + "get version")

	# Logging control
	parser.add_argument("--logging-level", default="INFO",
				  choices=["DEBUG", "INFO", "WARN", "WARNING", "ERROR"],
				  help="Minimum level of interest w.r.t. log messages")
	parser.add_argument("--logfile", help="Path to central logfile location")
	parser.add_argument("--logging-fmt",  help="Logging message template")
	parser.add_argument("--logging-datefmt", help="Time formatter for logs")

	subparsers = parser.add_subparsers(dest='command')

	# Run command
	run_subparser = subparsers.add_parser(
		"run", help="Main Looper function: Submit jobs for samples.")
	run_subparser.add_argument(
		'-t', '--time-delay', dest='time_delay', type=int, default=0,
		help="Time delay in seconds between job submissions.")
	run_subparser.add_argument(
		'--ignore-flags', action="store_true", default=False,
		help=("Ignore run status flags? Default: False. "
			"By default, pipelines will not be submitted if a pypiper "
			"flag file exists marking the run "
			"(e.g. as 'running' or 'failed'). Set this option "
			"to ignore flags and submit the runs anyway."))
	run_subparser.add_argument(
		'--compute', dest='compute',
		help="YAML file with looper environment compute settings.")
	run_subparser.add_argument(
		'--env',
		default=os.getenv("{}".format(LOOPERENV_VARNAME), ""),
		help="Employ looper environment compute settings.")
	run_subparser.add_argument(
		'--limit', type=int, help="Limit to n samples.")

	# Summarize command
	summarize_subparser = subparsers.add_parser(
		"summarize", help="Summarize statistics of project samples.")

	# Destroy command
	destroy_subparser = subparsers.add_parser(
		"destroy", help="Remove all files of the project.")

	# Check command
	check_subparser = subparsers.add_parser(
		"check", help="Checks flag status of current runs.")

	clean_subparser = subparsers.add_parser(
		"clean", help="Runs clean scripts to remove intermediate "
			    "files of already processed jobs.")

	# Common arguments
	for subparser in [run_subparser, summarize_subparser,
				destroy_subparser, check_subparser, clean_subparser]:
		subparser.add_argument(
			'--file-checks', dest='file_checks',
		action='store_false', default=True,
			help="Perform input file checks. Default=True.")
		subparser.add_argument(
			'-d', '--dry-run', dest='dry_run', action='store_true',
			help="Don't actually submit.", default=False)
		subparser.add_argument(
			'--sp', dest='subproject', help="Supply subproject")
		subparser.add_argument(
			dest='config_file',
			help="Project YAML config file.")

	# To enable the loop to pass args directly on to the pipelines...
	args, remaining_args = parser.parse_known_args()
	global _LOGGER
	_LOGGER = setup_looper_logger(
		args.logging_level, (args.logfile, ),
		fmt=args.logging_fmt, datefmt=args.logging_datefmt)

	if len(remaining_args) > 0:
		logging.info("Remaining arguments passed to pipelines: {}".
				 format(" ".join([str(x) for x in remaining_args])))

	return args, remaining_args


def run(prj, args, remaining_args):
	"""
	Main Looper function: Submit jobs for samples in project.
	"""

	# Look up the looper config files:
	pipeline_interface_file = os.path.join(prj.metadata.pipelines_dir,
							 "config/pipeline_interface.yaml")

	_LOGGER.info("Pipeline interface config: %s", pipeline_interface_file)
	pipeline_interface = PipelineInterface(pipeline_interface_file)

	protocol_mappings_file = os.path.join(prj.metadata.pipelines_dir,
							"config/protocol_mappings.yaml")
	_LOGGER.info("Protocol mappings config: %s", protocol_mappings_file)
	protocol_mappings = ProtocolMapper(protocol_mappings_file)

	# Update to project-specific protocol mappings
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
		pipeline_outfolder = os.path.join(prj.metadata.results_subdir, sample.sample_name)

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
		# NS: Move this check to within pipeline loop, since it's pipeline dependent.
		#if not all(os.path.isfile(f) for f in sample.data_path.split(" ")):
		#	fail_message += "Sample input file does not exist."
		#	fail = True

		if fail:
			_LOGGER.warn("\nNot submitted: %s", fail_message)
			failures.append([fail_message, sample.sample_name])
			continue

		# Otherwise, process the sample:
		prj.processed_samples.append(sample.sample_name)

		# serialize sample
		sample.to_yaml()

		# Get the base protocol-to-pipeline mappings
		if hasattr(sample, "library"):
			pipelines = protocol_mappings.build_pipeline(sample.library.upper())
		else:
			_LOGGER.warn(
				"Sample '%s' does not have a 'library' attribute and "
				"therefore cannot be mapped to any pipeline, skipping",
				str(sample.name))
			continue

		# We require that the pipelines and config files live in
		# a subdirectory called 'pipelines' -- is this the best way?
		pipelines_subdir = "pipelines"

		# Go through all pipelines to submit for this protocol
		for pipeline in pipelines:
			_LOGGER.info("Pipeline: '%s'", pipeline)
			# discard any arguments to get just the (complete) script name,
			# which is the key in the pipeline interface
			pl_id = str(pipeline).split(" ")[0]

			# add pipeline-specific attributes (read type and length, inputs, etc)
			sample.set_pipeline_attributes(pipeline_interface, pl_id)
			_LOGGER.info("({.2f} Gb)".format(sample.input_file_size))

			# Check for any required inputs before submitting
			try:
				inputs = sample.confirm_required_inputs()
			except IOError:
				fail_message = "Required input files not found"
				_LOGGER.error("\nNot submitted: %s", fail_message)
				failures.append([fail_message, sample.sample_name])
				continue

			# Identify the cluster resources we will require for this submission
			submit_settings = pipeline_interface.choose_resource_package(pl_id, sample.input_file_size)

			# Reset the partition if it was specified on the command-line
			if hasattr(prj.compute, "partition"):
				submit_settings["partition"] = prj.compute["partition"]

			# Pipeline name is the key used for flag checking
			pl_name = pipeline_interface.get_pipeline_name(pl_id)

			# Build basic command line string
			base_pipeline_script = os.path.join(prj.metadata.pipelines_dir, pipelines_subdir, pipeline)
			cmd = os.path.join(prj.metadata.pipelines_dir, pipelines_subdir, pipeline)

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

			if pipeline_interface.uses_looper_args(pl_id):

				# Check for a pipeline config file
				if hasattr(prj, "pipeline_config"):
					# Index with 'pl_id' instead of 'pipeline' because we don't care about
					# parameters here.
					if hasattr(prj.pipeline_config, pl_id):
						# First priority: pipeline config specified in project config
						pl_config_file = getattr(prj.pipeline_config, pl_id)
						if pl_config_file:  # make sure it's not null (which it could be provided as null)
							if not os.path.isfile(pl_config_file):
								_LOGGER.error("Pipeline config file specified but not found: %s", str(pl_config_file))
								raise IOError(pl_config_file)
							_LOGGER.info("Found config file: %s", str(getattr(prj.pipeline_config, pl_id)))
							# Append arg for config file if found
							cmd += " -C " + pl_config_file

				# Append output parent folder
				cmd += " -O " + prj.metadata.results_subdir

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
				prj.metadata.submission_subdir, pipeline_outfolder, pl_name, args.time_delay,
				submit=True, dry_run=args.dry_run, ignore_flags=args.ignore_flags,
				remaining_args=remaining_args)

	msg = "\nLooper finished (" + str(submit_count) + " of " + str(job_count) + " jobs submitted)."
	if args.dry_run:
		msg += " Dry run. No jobs were actually submitted"

	_LOGGER.info(msg)

	if len(failures) > 0:
		_LOGGER.info("Failure count: %d; Reasons for failure:",
				 len(failures))

		from collections import defaultdict
		groups = defaultdict(str)
		for msg, sample_name in failures:
			groups[msg] += sample_name + "; "

		for name, values in groups.iteritems():
			_LOGGER.info("  " + str(name) + ":" + str(values))


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
		pipeline_outfolder = os.path.join(prj.metadata.results_subdir, sample.sample_name)

		# Grab the basic info from the annotation sheet for this sample.
		# This will correspond to a row in the output.
		sample_stats = sample.get_sheet_dict()
		columns.extend(sample_stats.keys())
		# Version 0.3 standardized all stats into a single file
		stats_file = os.path.join(pipeline_outfolder, "stats.tsv")
		if os.path.isfile(stats_file):
			_LOGGER.info("Found stats file: '%s'", stats_file)
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

	tsv_outfile_path = os.path.join(prj.metadata.output_dir, prj.name)
	if prj.subproject:
		tsv_outfile_path += '_' + prj.subproject
	tsv_outfile_path += '_stats_summary.tsv'

	tsv_outfile = open(tsv_outfile_path, 'w')

	tsv_writer = csv.DictWriter(tsv_outfile, fieldnames=uniqify(columns), delimiter='\t', extrasaction='ignore')
	tsv_writer.writeheader()

	for row in stats:
		tsv_writer.writerow(row)

	tsv_outfile.close()

	_LOGGER.info("Summary (n=" + str(len(stats)) + "): " + tsv_outfile_path)

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
	# 	tsv_outfile_path = os.path.join(prj.metadata.output_dir, prj.name)
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


def destroy(prj, args, preview_flag=True):
	"""
	Completely removes all output files and folders produced by any pipelines.
	"""
	_LOGGER.info("Results to destroy:")

	for sample in prj.samples:
		sys.stdout.write("### " + sample.sample_name + "\t")
		pipeline_outfolder = os.path.join(prj.metadata.results_subdir, sample.sample_name)
		if preview_flag:
			# Preview: Don't actually delete, just show files.
			_LOGGER.info(str(pipeline_outfolder))
		else:
			destroy_sample_results(pipeline_outfolder, args)

	if not preview_flag:
		_LOGGER.info("Destroy complete.")
		return 0

	if args.dry_run:
		_LOGGER.info("Dry run. No files destroyed.")
		return 0

	if not query_yes_no("Are you sure you want to permanently delete all pipeline results for this project?"):
		_LOGGER.info("Destroy action aborted by user.")
		return 1

	# Finally, run the true destroy:

	return destroy(prj, args, preview_flag=False)


def clean(prj, args, preview_flag=True):
	"""
	Clean will remove all intermediate files, defined by pypiper clean scripts, in the project.
	"""

	_LOGGER.info("Files to clean:")
	for sample in prj.samples:
		sys.stdout.write("### " + sample.sample_name + "\t")
		pipeline_outfolder = os.path.join(prj.metadata.results_subdir, sample.sample_name)
		cleanup_files = glob.glob(os.path.join(pipeline_outfolder, "*_cleanup.sh"))
		if preview_flag:
			# Preview: Don't actually clean, just show what we're going to clean.
			_LOGGER.info(str(cleanup_files))
		else:
			for file in cleanup_files:
				_LOGGER.info(file)
				subprocess.call(["sh", file])

	if not preview_flag:
		_LOGGER.info("Clean complete.")
		return 0

	if args.dry_run:
		_LOGGER.info("Dry run. No files cleaned.")
		return 0

	if not query_yes_no("Are you sure you want to permanently delete all intermediate pipeline results for this project?"):
		_LOGGER.info("Clean action aborted by user.")
		return 1

	# Finally, run the true clean:

	return clean(prj, args, preview_flag=False)


def get_file_size(filename):
	"""
	Get size of all files in string (space-separated) in gigabytes (Gb).
	"""
	return sum([float(os.stat(f).st_size) for f in filename.split(" ") if f is not '']) / (1024 ** 3)


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
			_LOGGER.info("Flag file found. Not submitting: " + str([os.path.basename(i) for i in flag_files]))
			submit = False
		else:
			pass
			# print("")  # Do you want to print a newline after every sample?

	if submit:
		if dry_run:
			_LOGGER.info("\tDRY RUN: I would have submitted this")
			return 1
		else:
			subprocess.call(submission_command + " " + submit_script, shell=True)
			time.sleep(time_delay)  # sleep for `time_delay` seconds before submitting next job
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


def destroy_sample_results(result_outfolder, args):
	"""
	This function will delete all results for this sample
	"""
	import shutil
	if os.path.exists(result_outfolder):
		if args.dry_run:
			_LOGGER.info("DRY RUN. I would have removed: " + result_outfolder)
		else:
			_LOGGER.info("Removing: " + result_outfolder)
			shutil.rmtree(result_outfolder)
	else:
		_LOGGER.info(result_outfolder + " does not exist.")


def uniqify(seq):
	"""
	Fast way to uniqify while preserving input order.
	"""
	# http://stackoverflow.com/questions/480214/
	seen = set()
	seen_add = seen.add
	return [x for x in seq if not (x in seen or seen_add(x))]


def check(prj):
	"""
	Checks flag status
	"""
	# prefix
	pf = "ls " + prj.metadata.results_subdir + "/"
	cmd = os.path.join(pf + "*/*.flag | xargs -n1 basename | sort | uniq -c")
	_LOGGER.info(cmd)
	subprocess.call(cmd, shell=True)

	flags = ["completed", "running", "failed", "waiting"]

	counts = {}
	for f in flags:
		counts[f] = int(subprocess.check_output(pf + "*/*" + f + ".flag 2> /dev/null | wc -l", shell=True))
		# print(f + ": " + str(counts[f]))

	for f, count in counts.items():
		if count < 30 and count > 0:
			_LOGGER.info(f + " (" + str(count) + ")")
			subprocess.call(pf + "*/*" + f + ".flag 2> /dev/null", shell=True)


def main():

	# Parse command-line arguments and establish logger.
	args, remaining_args = parse_arguments()

	setup_looper_logger(args.logging_level or logging.INFO)

	# Initialize project
	prj = Project(
		args.config_file, args.subproject,
		file_checks=args.file_checks,
		looperenv_file=getattr(args, 'env', None))

	_LOGGER.info("Results subdir: " + prj.metadata.results_subdir)
	_LOGGER.info("Command: " + args.command)

	if args.command == "run":
		if args.compute:
			prj.set_compute(args.compute)
		run(prj, args, remaining_args)

	if args.command == "destroy":
		return destroy(prj, args)

	if args.command == "summarize":
		summarize(prj)

	if args.command == "check":
		check(prj)

	if args.command == "clean":
		clean(prj, args)


if __name__ == '__main__':
	try:
		sys.exit(main())
	except KeyboardInterrupt:
		_LOGGER.error("Program canceled by user!")
		sys.exit(1)
