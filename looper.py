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

try:
	from .models import Project
except:
	sys.path.append(os.path.join(os.path.dirname(__file__), "../pipelines"))
	from models import Project


def parse_arguments():
	"""
	Argument Parsing.
	"""
	parser = ArgumentParser(description='projectSampleLoop')

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


def get_genome(organism, kind="dna"):
	"""
	Pick the genome matching the organism from the sample annotation sheet.
	If no mapping exists in  the organism-genome translation dictionary, then
	we assume the given organism name directly corresponds to the name of a
	reference genome. This enables the use of additional genomes without any
	need to modify the code.
	"""
	if kind == "dna":
		if organism in prj.config['genomes'].keys():
			return prj.config['genomes'][organism]
	elif kind == "rna":
		if organism in prj.config['transcriptomes'].keys():
			return prj.config['transcriptomes'][organism]
	else:
		return organism


def get_file_size(filename):
	"""
	Get file stats. Gives in GB....
	"""
	st = os.stat(filename)
	return float(st.st_size)/1000000


def make_sure_path_exists(path):
	"""
	Create directory if it does not exist.
	"""
	try:
		os.makedirs(path)
	except OSError as exception:
		if exception.errno != errno.EEXIST:
			raise


def slurm_submit(template, variables_dict, slurm_folder, pipeline_outfolder,
				 pipeline_name, submit=False, dry_run=False, remaining_args=list()):
	"""
	Submit job to slurm.
	"""
	# Some generic variables
	submit_script = os.path.join(slurm_folder, sample.sample_name + "_" + pipeline_name + ".sub")
	submit_log = os.path.join(slurm_folder, sample.sample_name + "_" + pipeline_name + ".log")
	variables_dict["VAR_LOGFILE"] = submit_log

	# Prepare and write submission script
	sys.stdout.write("  SUBMIT_SCRIPT: " + submit_script + " ")
	make_sure_path_exists(os.path.dirname(submit_script))
	# read in submission template
	with open(template, 'r') as handle:
		filedata = handle.read()
	# update variable dict with any additionall arguments
	print(variables_dict["VAR_CODE"] + " " + str(" ".join(remaining_args)))
	variables_dict["VAR_CODE"] += " " + str(" ".join(remaining_args))
	# fill in submission template with variables
	for key, value in variables_dict.items():
		filedata = filedata.replace(str(key), str(value))
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
			print("DRY RUN: I would have submitted this")
		else:
			subprocess.call("sbatch " + submit_script, shell=True)


class ResourceTableLookup(object):
	"""
	This class parses, holds, and returns information for a yaml
	resource file that specifies for given pipelines and file sizes,
	what resource variables should be used for the given file.
	"""

	def __init__(self, yaml_config_file):
		import yaml

		#self.resources = defaultdict(dict)
		self.resources = yaml.load(open(yaml_config_file, 'r'))
		print(self.resources)

	def resource_lookup(self, tag, size):
		'''
		Given a pipeline name (tag) and a file size (size), return the
		resource configuratio specified by the config file.
		'''
		current_pick = "default"

		table = self.resources[tag]
		for option in table:
			print(option)
			if table[option]['file_size'] == "0":
				continue
			if size < float(table[option]['file_size']):
				continue
			elif float(table[option]['file_size']) > table[current_pick]['file_size']:
				current_pick = option

		print("choose:" + str(current_pick))
		return(current_pick)

	def get_resources(self, tag, option, var):
		print(self.resources[tag].keys())
		return(self.resources[tag][option][var])



# Look up the resource table:
resource_table = "pipeline_resource_table.yaml"
if os.path.exists(resource_table):
	print("Using compute table: " + resource_table)
	rtl = ResourceTableLookup(resource_table)
 	# Call for resources with:
 	#rtl.resource_lookup("pipeline", file_size)
	print("resource test:")
 	rtl.resource_lookup("wgbs_pipeline.py", 25)


# Parse command-line arguments
args, remaining_args = parse_arguments()

# Initialize project
prj = Project(args.conf_file)
# add sample sheet
prj.add_sample_sheet()
# keep track of submited samples
prj.processed_samples = list()


for sample in prj.samples:
	fail = False
	fail_message = ""
	wgbs = False
	tophat = False
	bitseq = False
	rrbs = False

	sys.stdout.write("### " + sample.sample_name + "\t")

	# Check for duplicate sample names
	if sample.sample_name in prj.processed_samples:
		fail_message += "Duplicate sample name detected. "
		fail = True

	# Check if sample should be ran
	if hasattr(sample, "run"):
		if not sample.run:
			fail_message += "Run column deselected."
			# fail = True
			sys.stdout.write(fail_message + "\n")
			continue

	# drop "-end", "_end", or just "end" from the end of the column value:
	if hasattr(sample, "single_or_paired"):
		sample.single_or_paired = re.sub('[_\\-]?end$', '', sample.single_or_paired)
		if sample.single_or_paired not in ["single", "paired"]:
			fail_message += "Value in column single_or_paired not recognized. Needs to be either single or paired."
			fail = True

	if not os.path.isfile(sample.data_path):
		fail_message += "Sample input file does not exist."
		fail = True

	if fail:
		print("Not submitted: " + fail_message)
		continue

	# Otherwise, process the sample:
	prj.processed_samples.append(sample.sample_name)
	pipeline_outfolder = os.path.join(prj.paths.results_subdir, sample.sample_name)
	slurm_template = os.path.join(prj.paths.pipelines_dir, "src_pipeline", "slurm_template.sub")
	wgbs_param = " "
	tophat_param = " "
	bitseq_param = " "
	rrbs_param = " "

	if sample.library == "CORE":
		wgbs = True
		bitseq = True
		tophat = True
		tophat_param += " --core-seq"
		bitseq_param += " --core-seq"

	if sample.library == "SMART":
		wgbs = False
		bitseq = True
		tophat = True
		tophat_param += " -f -l " + str(sample.read_length)
		bitseq_param += " -f"

	if sample.library == "EG" or sample.library == "WGBS":
		wgbs = True
		bitseq = False
		tophat = False

	if sample.library == "RRBS":
		wgbs = False
		bitseq = False
		tophat = False
		rrbs = True

	if hasattr(sample, "single_or_paired"):
		if sample.single_or_paired == "single":
			wgbs_param += " -q"
			tophat_param += " -q"
			bitseq_param += " -q"
			rrbs_param += " -q"

	if wgbs:
		# Submit the methylation analysis
		cmd = "python " + prj.paths.pipelines_dir + "/src_pipeline/wgbs_pipeline.py"
		cmd += " -i " + sample.data_path
		cmd += " -s " + sample.sample_name
		cmd += " -g " + get_genome(sample.organism, kind="dna")
		cmd += " --project-root=" + prj.paths.results_subdir

		cmd += wgbs_param

		print("input file size: ", get_file_size(sample.data_path))
		pl = "wgbs_pipeline.py"
		opt = rtl.resource_lookup(pl, get_file_size(sample.data_path))

		# Create new dict
		slurm_settings = {}

		slurm_settings["VAR_JOBNAME"] = sample.sample_name + "_wgbs"
		slurm_settings["VAR_MEM"] = rtl.get_resources(pl, opt, "mem")
		slurm_settings["VAR_CORES"] = rtl.get_resources(pl, opt, "cores")
		slurm_settings["VAR_TIME"] = rtl.get_resources(pl, opt, "time")
		slurm_settings["VAR_PARTITION"] = rtl.get_resources(pl, opt, "partition")
		slurm_settings["VAR_CODE"] = cmd

		slurm_submit(slurm_template, slurm_settings, prj.paths.submission_subdir, pipeline_outfolder, "WGBS", submit=True, dry_run=args.dry_run, remaining_args=remaining_args)

	if bitseq:
		# Submit the RNA BitSeq analysis
		cmd = "python " + prj.paths.pipelines_dir + "/src_pipeline/rnaBitSeq_pipeline.py"
		cmd += " -i " + sample.data_path
		cmd += " -s " + sample.sample_name
		cmd += " -g " + get_genome(sample.organism, kind="rna")
		cmd += " --project-root=" + prj.paths.results_subdir
		cmd += bitseq_param

		# Create new dict
		slurm_settings = {}

		slurm_settings["VAR_JOBNAME"] = sample.sample_name + "_rnaBitSeq"
		slurm_settings["VAR_MEM"] = "6000"
		slurm_settings["VAR_CORES"] = "6"
		slurm_settings["VAR_TIME"] = "2-00:00:00"
		slurm_settings["VAR_PARTITION"] = args.partition
		slurm_settings["VAR_CODE"] = cmd

		slurm_submit(slurm_template, slurm_settings, prj.paths.submission_subdir, pipeline_outfolder, "rnaBitSeq", submit=True, dry_run=args.dry_run, remaining_args=remaining_args)

	if tophat:
		# Submit the RNA TopHat analysis
		cmd = "python " + prj.paths.pipelines_dir + "/src_pipeline/rnaTopHat_pipeline.py"
		cmd += " -i " + sample.data_path
		cmd += " -s " + sample.sample_name
		cmd += " -g " + get_genome(sample.organism, kind="dna")
		cmd += " --project-root=" + prj.paths.results_subdir
		cmd += tophat_param

		# Create new dict
		slurm_settings = {}

		slurm_settings["VAR_JOBNAME"] = sample.sample_name + "_rnatopHat"
		slurm_settings["VAR_MEM"] = "30000"
		slurm_settings["VAR_CORES"] = "2"
		slurm_settings["VAR_TIME"] = "6-00:00:00"
		slurm_settings["VAR_PARTITION"] = args.partition
		slurm_settings["VAR_CODE"] = cmd

		slurm_submit(slurm_template, slurm_settings, prj.paths.submission_subdir, pipeline_outfolder, "rnaTopHat", submit=True, dry_run=args.dry_run, remaining_args=remaining_args)

	if rrbs:
		# Submit the RRBS analysis
		cmd = "python " + prj.paths.pipelines_dir + "/src_pipeline/rrbs_pipeline.py"
		cmd += " -i " + sample.data_path
		cmd += " -s " + sample.sample_name
		cmd += " -g " + get_genome(sample.organism, kind="dna")
		cmd += " --project-root=" + prj.paths.results_subdir
		cmd += rrbs_param

		# Create new dict
		slurm_settings = {}

		slurm_settings["VAR_JOBNAME"] = sample.sample_name + "_rrbs"
		slurm_settings["VAR_MEM"] = "4000"
		slurm_settings["VAR_CORES"] = "2"
		slurm_settings["VAR_TIME"] = "1-00:00:00"
		slurm_settings["VAR_PARTITION"] = args.partition
		slurm_settings["VAR_CODE"] = cmd

		slurm_submit(slurm_template, slurm_settings, prj.paths.submission_subdir, pipeline_outfolder, "RRBS", submit=True, dry_run=args.dry_run, remaining_args=remaining_args)
