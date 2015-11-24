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
import yaml

try:
	from .models import Project, AttributeDict
except:
	sys.path.append(os.path.join(os.path.dirname(__file__), "../pipelines"))
	from models import Project, AttributeDict


class PipelineInterface(object):
	"""
	This class parses, holds, and returns information for a yaml
	file that specifies tells the looper how to interact with each individual
	pipeline. This includes both resources to request for cluster job submission,
	as well as arguments to be passed from the sample annotation metadata to
	the pipeline
	"""

	def __init__(self, yaml_config_file):
		import yaml
		self.looper_config_file = yaml_config_file
		self.looper_config = yaml.load(open(yaml_config_file, 'r'))

	def select_pipeline(self, pipeline_name):
		"""
		Check to make sure that pipeline has an entry and if so, return it
		"""
		if not self.looper_config.has_key(pipeline_name):
			print("Missing pipeline description: '" + pipeline_name +"' not found in '" +
					self.looper_config_file + "'")
			# Should I just use defaults or force you to define this?
			raise Exception("You need to teach the looper about that pipeline")

		return(self.looper_config[pipeline_name])

	def choose_resource_package(self, pipeline_name, file_size):
		'''
		Given a pipeline name (pipeline_name) and a file size (size), return the
		resource configuratio specified by the config file.
		'''
		config = self.select_pipeline(pipeline_name)

		if not config.has_key('resources'):
			msg = "No resources found for '" + pipeline_name +"' in '" + self.looper_config_file + "'"
			# Should I just use defaults or force you to define this?
			raise IOError(msg)

		table = config['resources']
		current_pick = "default"

		for option in table:
			if table[option]['file_size'] == "0":
				continue
			if file_size < float(table[option]['file_size']):
				continue
			elif float(table[option]['file_size']) > table[current_pick]['file_size']:
				current_pick = option

		# print("choose:" + str(current_pick))

		return(table[current_pick])


	def get_arg_string(self, pipeline_name, sample):
		"""
		For a given pipeline and sample, return the argument string
		"""
		config = self.select_pipeline(pipeline_name)

		if not config.has_key('arguments'):
			print("No arguments found for '" + pipeline_name +"' in '" +
					self.looper_config_file + "'")
			return("") # empty argstring

		argstring = ""
		args = config['arguments']
		for key, value in args.iteritems():
			# print(key, value)
			if value is None:
				arg = ""
			else:
				try:
					arg = getattr(sample, value)
				except AttributeError as e:
					print("Pipeline '" + pipeline_name + "' requests for argument '" +
							key + "' a sample attribute named '" + value + "'" +
							" but no such attribute exists for sample '" +
							sample.sample_name + "'")
					raise e

			argstring += " " + key + " " + arg

		return(argstring)



class ProtocolMapper(object):
	"""
	This class maps protocols (the library column) to pipelines. For example,
	WGBS is mapped to wgbs.py
	"""
	def __init__(self, mappings_file):
		import yaml
		# mapping libraries to pipelines
		self.mappings_file = mappings_file
		self.mappings = yaml.load(open(mappings_file, 'r'))


	def build_pipeline(self, protocol):
		# print("Building pipeline for protocol '" + protocol + "'")

		if not self.mappings.has_key(protocol):
			print("  Missing Protocol Mapping: '" + protocol + "' is not found in '" + self.mappings_file + "'")
			return([]) #empty list

		# print(self.mappings[protocol]) # The raw string with mappings
		# First list level
		split_jobs = [x.strip() for x in self.mappings[protocol].split(';')]
		# print(split_jobs) # Split into a list
		return(split_jobs) # hack works if no parllelism

		for i in range(0, len(split_jobs)):
			if i == 0:
				self.parse_parallel_jobs(split_jobs[i], None)
			else:
				self.parse_parallel_jobs(split_jobs[i], split_jobs[i - 1])


	def parse_parallel_jobs(self, job, dep):
		# Eliminate any parenthesis
		job = job.replace("(", "")
		job = job.replace(")", "")
		# Split csv entry
		split_jobs = [x.strip() for x in job.split(',')]
		if len(split_jobs) > 1:
			for s in split_jobs:
				self.register_job(s, dep)
		else:
			self.register_job(job, dep)


	def register_job(self, job, dep):
		print("Register Job Name:" + job + "\tDep:" + str(dep))



def parse_arguments():
	"""
	Argument Parsing.
	"""
	parser = ArgumentParser(description='Looper')

	parser.add_argument('-c', '--config-file', dest='conf_file', help="Supply config file [-c]. Example: /fhgfs/groups/lab_bock/shared/COREseq/config.txt")
	parser.add_argument('-d', '--dry-run', dest='dry_run', action='store_true', help="Don't actually submit.", default=False)
	# this should be changed in near future
	parser.add_argument('-pd', dest='partition', default="longq")
	# args = parser.parse_args()
	# To enable the loop to pass args directly on to the pipelines...
	args, remaining_args = parser.parse_known_args()

	print("Remaining arguments passed to pipelines: " + str(remaining_args))

	if not args.conf_file:
		parser.print_help()  # or, print_usage() for less verbosity
		raise SystemExit

	return args, remaining_args


def get_genome(config, organism, kind="dna"):
	"""
	Pick the genome matching the organism from the sample annotation sheet.
	If no mapping exists in  the organism-genome translation dictionary, then
	we assume the given organism name directly corresponds to the name of a
	reference genome. This enables the use of additional genomes without any
	need to modify the code.
	"""
	if kind == "dna":
		if organism in config['genomes'].keys():
			return config['genomes'][organism]
	elif kind == "rna":
		if organism in config['transcriptomes'].keys():
			return config['transcriptomes'][organism]
	else:
		return organism


def get_file_size(filename):
	"""
	Get file stats. Gives in GB....
	"""
	# filename can actually be a (space-separated) string listing multiple files
	if ' ' in filename:
		filesplit = filename.split()
		return(get_file_size(filesplit[0]) + get_file_size(filesplit[1:]))
	else:
		st = os.stat(filename)
		return float(st.st_size) / 1000000


def make_sure_path_exists(path):
	"""
	Create directory if it does not exist.
	"""
	try:
		os.makedirs(path)
	except OSError as exception:
		if exception.errno != errno.EEXIST:
			raise


def cluster_submit(sample, submit_template, submission_command, variables_dict,
 				submission_folder,	pipeline_outfolder, pipeline_name,
				submit=False, dry_run=False, remaining_args=list()):
	"""
	Submit job to cluster manager.
	"""
	# Some generic variables
	# Toss the file extension
	pipeline_name_short = os.path.splitext(pipeline_name)[0]
	submit_script = os.path.join(submission_folder, sample.sample_name + "_" + pipeline_name_short + ".sub")
	submit_log = os.path.join(submission_folder, sample.sample_name + "_" + pipeline_name_short + ".log")
	variables_dict["LOGFILE"] = submit_log

	# Prepare and write submission script
	sys.stdout.write("  SUBFILE: " + submit_script + " ")
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
		filedata = filedata.replace("{"+str(key).upper()+"}", str(value))
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
		print("")

	if submit:
		if dry_run:
			print("  DRY RUN: I would have submitted this")
		else:
			subprocess.call(submission_command + " " + submit_script, shell=True)
			#pass



def main():
	# Parse command-line arguments
	args, remaining_args = parse_arguments()

	y = yaml.load(open(args.conf_file, 'r'))
	s = AttributeDict(**y)
	print(s)

	# Initialize project
	prj = Project(args.conf_file)
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

	for sample in prj.samples:
		fail = False
		fail_message = ""
		sys.stdout.write("### " + sample.sample_name + "\t")

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
			sample.single_or_paired = re.sub('[_\\-]?end$', '', sample.single_or_paired)
			if sample.single_or_paired not in ["single", "paired"]:
				fail_message += "single_or_paired must be either 'single' or 'paired'."
				fail = True

		# Make sure the input data exists
		if not os.path.isfile(sample.data_path):
			fail_message += "Sample input file does not exist."
			fail = True

		if fail:
			print("Not submitted: " + fail_message)
			continue

		# Otherwise, process the sample:
		prj.processed_samples.append(sample.sample_name)
		pipeline_outfolder = os.path.join(prj.paths.results_subdir, sample.sample_name)
		input_file_size = get_file_size(sample.data_path)
		print("(" + str(round(input_file_size, 2)) + " GB)")

		# Get the base protocl to pipeline mappings
		pl_list = protocol_mappings.build_pipeline(sample.library)

		# We require that the pipelines and config files live in
		# a subdirectory called 'pipelines' -- is this the best way?
		pipelines_subdir = "pipelines"

		# Go through all pipelines to submit for this protocol
		for pl in pl_list:
			# Identify the cluster resources we will require for this submission
			submit_settings = pipeline_interface.choose_resource_package(pl, input_file_size)

			# Build basic command line string
			base_pipeline_script = os.path.join(prj.paths.pipelines_dir, pipelines_subdir, pl)
			cmd = os.path.join(prj.paths.pipelines_dir, pipelines_subdir, pl)

			# Append arguments for this pipeline
			# Sample-level arguments are handled by the pipeline interface.
			argstring = pipeline_interface.get_arg_string(pl, sample)
			cmd += argstring

			# Project-level arguments (those that do not change for each sample)
			# must be handled separately.
			# These are looper_args, -C, -O, and -P. If the pipeline implements
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
			cmd += " -O " + prj.paths.output_dir

			# Append arg for cores (number of processors to use)
			if submit_settings["cores"] > 1:
				cmd += " -P " + submit_settings["cores"]

			# Add the command string and job name to the submit_settings object
			submit_settings["JOBNAME"] = sample.sample_name + "_" + pl
			submit_settings["CODE"] = cmd

			# Submit job!
			cluster_submit(sample, prj.compute.submission_template, prj.compute.submission_command, submit_settings, prj.paths.submission_subdir, pipeline_outfolder, pl, submit=True, dry_run=args.dry_run, remaining_args=remaining_args)


if __name__ == '__main__':
	try:
		sys.exit(main())
	except KeyboardInterrupt:
		print("Program canceled by user!")
		sys.exit(1)
