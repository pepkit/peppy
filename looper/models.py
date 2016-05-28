#!/usr/bin/env python

"""
Models for NGS projects
=======================

Workflow explained:
	- Project is created
	- Add Sample sheet to project (spawns next)
		- Samples are created and added to project (automatically)

In the process, stuff is checked:
	- project structure (created if not existing)
	- existance of csv sample sheet with minimal fields
	- existance of bam files from samples
	- read type/length of samples

:Example:

from pipelines import Project
prj = Project("config.yaml")
prj.add_sample_sheet()
# that's it!

# explore!
prj.samples  # see all samples
prj.samples[0].fastq  # get fastq file of first sample
[s.mapped for s in prj.samples if s.library == "WGBS"]  # get all bam files of WGBS samples

prj.paths.results  # results directory of project
prj.sheet.to_csv(_os.path.join(prj.paths.output_dir, "sample_annotation.csv"))  # export again the project's annotation

# project options are read from the config file
# but can be changed on the fly:
prj = Project("test.yaml")
prj.config["merge_technical"] = False  # change options on the fly
prj.add_sample_sheet("sample_annotation.csv")  # annotation sheet not specified initially in config file

"""

import os as _os
import pandas as _pd
import yaml as _yaml
import warnings as _warnings


def copy(obj):
	def copy(self):
		"""
		Copy self to a new object.
		"""
		from copy import deepcopy

		return deepcopy(self)
	obj.copy = copy
	return obj


@copy
class Paths(object):
	"""
	A class to hold paths as attributes.
	"""
	def __repr__(self):
		return "Paths object."


@copy
class AttributeDict(object):
	"""
	A class to convert a nested Dictionary into an object with key-values
	accessibly using attribute notation (AttributeDict.attribute) instead of
	key notation (Dict["key"]). This class recursively sets Dicts to objects,
	allowing you to recurse down nested dicts (like: AttributeDict.attr.attr)
	"""
	def __init__(self, entries):
		self.add_entries(entries)

	def add_entries(self, entries):
		for key, value in entries.items():
			if type(value) is dict:
				# key exists
				if hasattr(self, key):
					if type(self[key]) is AttributeDict:
						print ("Updating existing key: " + key)
						# Combine them
						self.__dict__[key].add_entries(value)
					else:
						# Create new AttributeDict, replace previous value
						self.__dict__[key] = AttributeDict(value)
				else:
					# Create new AttributeDict
					self.__dict__[key] = AttributeDict(value)
			else:
				# Overwrite even if it's a dict.
				self.__dict__[key] = value

	def __getitem__(self, key):
		"""
		Provides dict-style access to attributes
		"""
		return getattr(self, key)


@copy
class Project(AttributeDict):
	"""
	A class to model a Project.

	:param config_file: Project config file (yaml).
	:type config_file: str
	:param dry: If dry mode is activated, no directories will be created upon project instantiation.
	:type dry: bool
	:param permissive: Whether a error should be thrown if a sample input file(s) do not exist or cannot be open.
	:type permissive: bool
	:param file_checks: Whether sample input files should be checked for their attributes (read type, read length) if this is not set in sample metadata.
	:type file_checks: bool

	:Example:

	from pipelines import Project
	prj = Project("config.yaml")
	"""
	def __init__(self, config_file, subproject=None, dry=False, permissive=True, file_checks=False):
		# super(Project, self).__init__(**config_file)

		# optional configs
		self.permissive = permissive
		self.file_checks = file_checks

		# include the path to the config file
		self.config_file = _os.path.abspath(config_file)

		# Parse config file
		self.parse_config_file(subproject)

		# Get project name
		# deduce from output_dir variable in config file:
		self.name = _os.path.basename(self.paths.output_dir)
		# TODO:
		# or require config file to have it:
		# self.name = self.config["project"]["name"]

		# Set project's directory structure
		if not dry:
			self.make_project_dirs()
			# self.set_project_permissions()

		# samples
		self.samples = list()

	def __repr__(self):
		if hasattr(self, "name"):
			name = self.name
		else:
			name = "[no name]"

		return "Project '%s'" % name + "\nConfig: " + str(self.config)

	def parse_config_file(self, subproject=None):
		"""
		Parse provided yaml config file and check required fields exist.
		"""
		with open(self.config_file, 'r') as handle:
			self.config = _yaml.load(handle)

		# parse yaml into the project's attributes
		self.add_entries(self.config)

		# Overwrite any config entries with entries in the subproject

		if "subprojects" in self.config and subproject:
			self.add_entries(self.config['subprojects'][subproject])

		# These are required variables which have absolute paths
		mandatory = ["output_dir", "pipelines_dir"]
		for var in mandatory:
			if not hasattr(self.paths, var):
				raise KeyError("Required field not in config file: %s" % var)
			setattr(self.paths, var, _os.path.expandvars(getattr(self.paths, var)))

		# Variables which are relative to the config file
		# All variables in these sections should be relative to the project config
		relative_sections = ["metadata", "pipeline_config"]

		for sect in relative_sections:
			if not hasattr(self, sect):
				continue
			relative_vars = getattr(self, sect)
			if not relative_vars:
				continue
			# print(relative_vars.__dict__)
			for var in relative_vars.__dict__:
				# print(type(relative_vars), var, getattr(relative_vars, var))
				if not hasattr(relative_vars, var):
					continue
				# It could have been 'null' in which case, don't do this.
				if getattr(relative_vars, var) is None:
					continue
				if not _os.path.isabs(getattr(relative_vars, var)):
					# Set the path to an absolute path, relative to project config
					setattr(relative_vars, var, _os.path.join(_os.path.dirname(self.config_file), getattr(relative_vars, var)))

		# And Variables relative to pipelines_dir
		if not _os.path.isabs(self.compute.submission_template):
			self.compute.submission_template = _os.path.join(self.paths.pipelines_dir, self.compute.submission_template)

		# Required variables check
		if not hasattr(self.metadata, "sample_annotation"):
			raise KeyError("Required field not in config file: %s" % "sample_annotation")

		# These are optional because there are defaults
		config_vars = {  # variables with defaults = {"variable": "default"}, relative to output_dir
			"results_subdir": "results_pipeline",
			"submission_subdir": "submission"
		}
		for key, value in config_vars.items():
			if hasattr(self.paths, key):
				if not _os.path.isabs(getattr(self.paths, key)):
					setattr(self.paths, key, _os.path.join(self.paths.output_dir, getattr(self.paths, key)))
			else:
				setattr(self.paths, key, _os.path.join(self.paths.output_dir, value))

	def make_project_dirs(self):
		"""
		Creates project directory structure if it doesn't exist.
		"""
		for name, path in self.paths.__dict__.items():
			if name not in ["pipelines_dir"]:   # this is a list just to support future variables
				if not _os.path.exists(path):
					try:
						_os.makedirs(path)
					except OSError("Cannot create directory %s" % path) as e:
						raise e

	def set_project_permissions(self):
		"""
		Makes the project's public_html folder executable.
		"""
		for d in [self.trackhubs.trackhub_dir]:
			try:
				_os.chmod(d, 0755)
			except OSError:
				# This currently does not fail now
				# ("cannot change folder's mode: %s" % d)
				continue

	def get_arg_string(self, pipeline_name):
		"""
		For this project, given a pipeline, return an argument string
		specified in the project config file.
		"""
		argstring = ""  # Initialize to empty
		if hasattr(self, "pipeline_args"):
			if hasattr(self.pipeline_args, pipeline_name):
				for key, value in getattr(self.pipeline_args, pipeline_name).__dict__.items():
					argstring += " " + key
					# Arguments can have null values; then print nothing
					if value:
						argstring += " " + value

		return argstring

	def add_sample_sheet(self, csv=None, permissive=None, file_checks=None):
		"""
		Build a `SampleSheet` object from a csv file and
		add it and its samples to the project.

		:param csv: Path to csv file.
		:type csv: str
		:param permissive: Should it throw error if sample input is not found/readable? Defaults to what is set to the Project.
		:type permissive: bool
		:param file_checks: Should it check for properties of sample input files (e.g. read type, length)? Defaults to what is set to the Project.
		:type file_checks: bool
		"""
		# If options are not passed, used what has been set for project
		if permissive is None:
			permissive = self.permissive
		else:
			permissive = self.permissive

		if file_checks is None:
			file_checks = self.file_checks
		else:
			file_checks = self.file_checks

		# Make SampleSheet object
		# by default read sample_annotation, but allow csv argument to be passed here explicitely
		if csv is None:
			self.sheet = SampleSheet(self.metadata.sample_annotation)
		else:
			self.sheet = SampleSheet(csv)

		# pair project and sheet
		self.sheet.prj = self

		# Generate sample objects from annotation sheet
		self.sheet.make_samples()

		# Add samples to Project
		for sample in self.sheet.samples:
			self.add_sample(sample)
			sample.merged = False  # mark sample as not merged - will be overwritten later if indeed merged

		# Merge sample files (!) using merge table if provided:
		if hasattr(self.metadata, "merge_table"):
			if self.metadata.merge_table is not None:
				if _os.path.isfile(self.metadata.merge_table):
					# read in merge table
					merge_table = _pd.read_csv(self.metadata.merge_table)

					# for each sample:
					for sample in self.sheet.samples:
						merge_rows = merge_table[merge_table['sample_name'] == sample.name]

						# check if there are rows in the merge table for this sample:
						if len(merge_rows) > 0:
							# for each row in the merge table of this sample:
							# 1) update the sample values with the merge table
							# 2) get data source (file path) for each row (which represents a file to be added)
							# 3) append file path to sample.data_path (space delimited)
							data_paths = list()
							for row in merge_rows.index:
								sample.update(merge_rows.ix[row].to_dict())  # 1)
								data_paths.append(sample.locate_data_source())  # 2)
							sample.data_path = " ".join(data_paths)  # 3)
							sample.merged = True  # mark sample as merged

		# With all samples, prepare file paths and get read type (optionally make sample dirs)
		for sample in self.samples:
			sample.set_file_paths()
			sample.get_genome()
			if not sample.check_input_exists():
				continue

			# get read type and length if not provided
			if not hasattr(sample, "read_type") and self.file_checks:
				sample.get_read_type()

			# make sample directory structure
			# sample.make_sample_dirs()

	def add_sample(self, sample):
		"""
		Adds a sample to the project's `samples`.
		"""
		# Check sample is Sample object
		if not isinstance(sample, Sample):
			raise TypeError("Provided object is not a Sample object.")

		# Tie sample and project bilateraly
		sample.prj = self
		# Append
		self.samples.append(sample)


@copy
class SampleSheet(object):
	"""
	Class to model a sample annotation sheet.

	:param csv: Path to csv file.
	:type csv: str

	Kwargs (will overule specified in config):
	:param merge_technical: Should technical replicates be merged to create biological replicate samples?
	:type merge_technical: bool
	:param merge_biological: Should biological replicates be merged?
	:type merge_biological: bool

	:Example:

	from pipelines import Project, SampleSheet
	prj = Project("ngs")
	sheet = SampleSheet("/projects/example/sheet.csv")
	"""
	def __init__(self, csv, **kwargs):

		super(SampleSheet, self).__init__()

		self.csv = csv
		self.samples = list()
		self.check_sheet()

	def __repr__(self):
		if hasattr(self, "prj"):
			return "SampleSheet for project '%s' with %i samples." % (self.prj, len(self.df))
		else:
			return "SampleSheet with %i samples." % len(self.df)

	def check_sheet(self):
		"""
		Check if csv file exists and has all required columns.
		"""
		# Read in sheet
		try:
			self.df = _pd.read_csv(self.csv)
		except IOError("Given csv file couldn't be read.") as e:
			raise e

		# Check mandatory items are there
		req = ["sample_name", "library", "organism"]
		missing = [col for col in req if col not in self.df.columns]

		if len(missing) != 0:
			raise ValueError("Annotation sheet is missing columns: %s" % " ".join(missing))

	def make_sample(self, series):
		"""
		Make a children of class Sample dependent on its "library" attribute.

		:param series: Pandas `Series` object.
		:type series: pandas.Series
		:return: An object or class `Sample` or a child of that class.
		:rtype: pipelines.Sample
		"""
		import sys
		import inspect
		try:
			import pipelines  # this will fail with ImportError if a pipelines package is not installed
		except ImportError:
			return Sample(series)  # if so, return generic Sample

		# get all class objects from installed pipelines that have a __library__ attribute
		sample_types = inspect.getmembers(
			sys.modules['pipelines'],
			lambda member: inspect.isclass(member) and hasattr(member, "__library__"))

		# get __library__ attribute from classes and make mapping of __library__: Class (a dict)
		pairing = {sample_class.__library__: sample_class for sample_type, sample_class in sample_types}

		# Match sample and sample_class
		try:
			return pairing[series.library](series)
		except KeyError:
			return Sample(series)

	def make_samples(self):
		"""
		Creates samples from annotation sheet dependent on library and adds them to the project.
		"""
		for i in range(len(self.df)):
			self.samples.append(self.make_sample(self.df.ix[i].dropna()))

	def as_data_frame(self, all=True):
		"""
		Returns a `pandas.DataFrame` representation of self.
		"""
		df = _pd.DataFrame([s.as_series() for s in self.samples])

		# One might want to filter some attributes out

		return df

	def to_csv(self, path, all=False):
		"""
		Saves a csv annotation sheet from the samples.

		:param path: Path to csv file to be written.
		:type path: str
		:param all: If all sample attributes should be kept in the annotation sheet.
		:type all: bool

		:Example:

		from pipelines import SampleSheet
		sheet = SampleSheet("/projects/example/sheet.csv")
		sheet.to_csv("/projects/example/sheet2.csv")
		"""
		df = self.as_data_frame(all=all)
		df.to_csv(path, index=False)


@copy
class Sample(object):
	"""
	Class to model Samples basd on a pandas Series.

	:param series: Pandas `Series` object.
	:type series: pandas.Series
	:param permissive: Should throw error if sample file is not found/readable?.
	:type permissive: bool

	:Example:

	from pipelines import Project, SampleSheet, Sample
	prj = Project("ngs")
	sheet = SampleSheet("/projects/example/sheet.csv", prj)
	s1 = Sample(sheet.ix[0])
	"""
	# Originally, this object was inheriting from _pd.Series,
	# but complications with serializing and code maintenance
	# made me go back and implement it as a top-level object
	def __init__(self, series, permissive=True):
		import re
		# Passed series must either be a pd.Series or a daugther class
		if not isinstance(series, _pd.Series):
			raise TypeError("Provided object is not a pandas Series.")
		super(Sample, self).__init__()

		# Set series attributes on self
		for key, value in series.to_dict().items():
			setattr(self, key, value)

		# Enforce type of name attributes as str without whitespace
		attributes = ["sample_name", "BSF_name"]
		for attr in attributes:
			if hasattr(self, attr):
				# throw error if either variable contains whitespace
				if re.search(r"\s", str(getattr(self, attr))):
					raise ValueError("Sample '%s' has whitespace in variable '%s'" % (str(getattr(self, attr)), attr))
				# else, set attribute as variable value
				setattr(self, attr, str(getattr(self, attr)))

		# Enforce type attributes as int
		attributes = ["lane"]
		for attr in attributes:
			if hasattr(self, attr):
				try:
					setattr(self, attr, int(getattr(self, attr)))
				except:
					pass

		# Check if required attributes exist and are not empty
		self.check_valid()

		# Short hand for getting sample_name
		self.name = self.sample_name

		# Get name for sample:
		# this is a concatenation of all passed Series attributes except "unmappedBam"
		# self.generate_name()

		# Sample dirs
		self.paths = Paths()
		# Only when sample is added to project, can paths be added -
		# this is because sample-specific files will be created in a data root directory dependendt on the project.
		# The SampleSheet object, after beeing added to a project, will
		# call Sample.set_file_paths(), creating the data_path of the sample (the bam file)
		# and other paths.

	def __repr__(self):
		return "Sample '%s'" % self.sample_name

	def update(self, newdata):
		"""
		Update Sample object with attributes from a dict.
		"""
		for key, value in newdata.items():
			setattr(self, key, value)

	def check_valid(self):
		"""
		Check provided sample annotation is valid.

		It requires fields `sample_name`, `library`, `organism` to be existent and non-empty.
		If `data_path` is not provided or empty, then `flowcell`, `lane`, `BSF_name` are all required.
		"""
		def check_attrs(req):
			for attr in req:
				if not hasattr(self, attr):
					raise ValueError("Missing value for " + attr + " (sample: " + str(self) + ")")
				if attr == "nan":
					raise ValueError("Empty value for " + attr + " (sample: " + str(self) + ")")

		# Check mandatory items are there.
		# this will require sample_name
		# later I will implement this in a way that sample names are not mandatory,
		# but created from the sample's attributes
		check_attrs(["sample_name", "library", "organism"])

		# Check that either data_path is specified or that BSF fields exist
		if hasattr(self, "data_source"):
			if (self.data_source == "nan") or (self.data_source == ""):
				# then it must have all of the following:
				check_attrs(["flowcell", "lane", "BSF_name"])
		else:
			check_attrs(["flowcell", "lane", "BSF_name"])

	def generate_name(self):
		"""
		Generates a name for the sample by joining some of its attribute strings.
		"""
		# fields = [
		#     "cellLine", "numberCells", "library", "ip",
		#     "patient", "patientID", "sampleID", "treatment", "condition",
		#     "biologicalReplicate", "technicalReplicate",
		#     "experimentName", "genome"]

		# attributes = [self.__getattribute__(attr) for attr in fields if hasattr(self, attr) and str(self.__getattribute__(attr)) != "nan"]
		# # for float values (if a value in a colum is nan) get a string that discards the float part
		# fields = list()
		# for attr in attributes:
		#     if type(attr) is str:
		#         fields.append(attr)
		#     elif type(attr) is _pd.np.float64:
		#         fields.append(str(int(attr)))
		# # concatenate to form the name
		# self.sample_name = "_".join([str(attr) for attr in fields])
		raise NotImplementedError("Not implemented in new code base.")

	def as_series(self):
		"""
		Returns a `pandas.Series` object with all the sample's attributes.
		"""
		return _pd.Series(self.__dict__)

	def to_yaml(self, path=None):
		"""
		Serializes itself in YAML format.

		:param path: A file path to write yaml to.
		:type path: str
		"""
		def obj2dict(obj):
			"""
			Build representation of object as a dict, recursively
			for all objects that might be attributes of itself.
			"""
			output = dict()
			obj = obj.copy().__dict__
			for key, value in obj.items():
				if type(obj[key]) in [str, int, bool]:
					output[key] = value
				elif type(obj[key]) in [Paths, Project, AttributeDict]:
					output[key] = obj2dict(obj[key])
				elif type(obj[key]) is list:
					if key != "samples":
						output[key] = [i if type(i) in [str, int, bool] else obj2dict(i) for i in obj[key]]
			return output

		# if path is not specified, use default:
		# prj.paths.submission_dir + sample_name + yaml
		if path is None:
			self.yaml_file = _os.path.join(self.prj.paths.submission_subdir, self.sample_name + ".yaml")
		else:
			self.yaml_file = path

		# transform into dict
		serial = obj2dict(self)

		# write
		with open(self.yaml_file, 'w') as outfile:
			outfile.write(_yaml.dump(serial, default_flow_style=False))

	def locate_data_source(self):
		"""
		Locates the path of input file `data_path` based on a regex.
		"""
		default_regex = "/scratch/lab_bsf/samples/{flowcell}/{flowcell}_{lane}_samples/{flowcell}_{lane}#{BSF_name}.bam"  # default regex

		# get bam file in regex form dependent on the "source" specified for each sample
		if hasattr(self, "data_source"):
			if (self.data_source is not _pd.np.nan) and (self.data_source != ""):
				try:
					return self.prj["data_sources"][self.data_source].format(**self.__dict__)
				except AttributeError:
					print("Config lacks location for data_source: " + self.data_source)
					# raise AttributeError("Config lacks location for data_source: " + self.data_source)
				return
		# if absent is the default regex
		return default_regex.format(**self.__dict__)

	def get_genome(self):
		"""
		Get genome and transcriptome, based on project config file.
		If not available (matching config), genome and transcriptome will be set to sample.organism.
		"""
		try:
			self.genome = getattr(self.prj.genomes, self.organism)
		except AttributeError:
			# self.genome = self.organism
			raise AttributeError("Config lacks a mapping of the required organism and a genome")
		# get transcriptome
		try:
			self.transcriptome = getattr(self.prj.transcriptomes, self.organism)
		except AttributeError:
			# self.genome = self.organism
			raise AttributeError("Config lacks a mapping of the required organism and a genome")

	def set_file_paths(self, overide=False):
		"""
		Sets the paths of all files for this sample.
		"""
		# If sample has data_path and is merged, then skip this because the paths are already built
		if self.merged and hasattr(self, "data_path") and not overide:
			pass

		# If sample does not have data_path, then let's build BSF path to unaligned bam.
		# this is built on a regex specified in the config file or the custom one (see `Project`).
		if hasattr(self, "data_path"):
			if (self.data_path == "nan") or (self.data_path == ""):
				self.data_path = self.locate_data_source()
		else:
			self.data_path = self.locate_data_source()

		# parent
		self.results_subdir = self.prj.paths.results_subdir
		self.paths.sample_root = _os.path.join(self.prj.paths.results_subdir, self.sample_name)

		# Track url
		try:
			# Project's public_html folder
			self.bigwig = _os.path.join(self.prj.trackhubs.trackhub_dir, self.sample_name + ".bigWig")
			self.track_url = "/".join([self.prj.trackhubs.url, self.sample_name + ".bigWig"])
		except:
			pass

	def make_sample_dirs(self):
		"""
		Creates sample directory structure if it doesn't exist.
		"""
		for path in self.paths.__dict__.values():
			if not _os.path.exists(path):
				_os.makedirs(path)

	def check_input_exists(self, permissive=True):
		"""
		Creates sample directory structure if it doesn't exist.
		"""

		l = list()
		# Sanity check:
		if not self.data_path:
			self.data_path = ""

		# There can be multiple, space-separated values here.
		for path in self.data_path.split(" "):
			if not _os.path.exists(path):
				l.append(path)

		# Only one of the inputs needs exist.
		# If any of them exists, length will be > 0
		if len(l) > 0:
			if not permissive:
				raise IOError("Input file does not exist or cannot be read: %s" % path)
			else:
				print("Input file does not exist or cannot be read: %s" % ", ".join(l))
				return False
		return True

	def get_read_type(self, n=10, permissive=True):
		"""
		Gets the read type (single, paired) and read length of bam file.

		:param n: Number of reads to read to determine read type. Default=10.
		:type n: int
		:param permissive: Should throw error if sample file is not found/readable?.
		:type permissive: bool
		"""
		import subprocess as sp
		from collections import Counter

		def bam_or_fastq(input_file):
			if ".bam" in input_file:
				return "bam"
			elif ".fastq" in input_file:
				return "fastq"
			else:
				raise TypeError("Type of input file does not end in either '.bam' or '.fastq'")

		def check_bam(bam, o):
			"""
			"""
			# view reads
			p = sp.Popen(['samtools', 'view', bam], stdout=sp.PIPE)

			# Count paired alignments
			paired = 0
			read_length = Counter()
			while o > 0:
				line = p.stdout.next().split("\t")
				flag = int(line[1])
				read_length[len(line[9])] += 1
				if 1 & flag:  # check decimal flag contains 1 (paired)
					paired += 1
				o -= 1
			p.kill()
			return (read_length, paired)

		def check_fastq(fastq, o):
			"""
			"""
			print(_warnings.warn("Detection of read type/length for fastq input is not yet implemented."))
			return (None, None)

		# Initialize the parameters in case there is no input_file,
		# so these attributes at least exist
		self.read_length = None
		self.read_type = None
		self.paired = None

		# for samples with multiple original bams, check all
		files = list()
		for input_file in self.data_path.split(" "):
			try:
				# Guess the file type, parse accordingly
				file_type = bam_or_fastq(input_file)
				if file_type == "bam":
					read_length, paired = check_bam(input_file, n)
				elif file_type == "fastq":
					read_length, paired = check_fastq(input_file, n)
				else:
					read_length, paired = (None, None)
			except:
				# If any file cannot be read, set all bam attributes to None and finish
				if not permissive:
					raise IOError("Input file does not exist or cannot be read: %s" % input_file)
				else:
					print(_warnings.warn("Input file does not exist or cannot be read: %s" % input_file))
					self.read_length = None
					self.read_type = None
					self.paired = None

					return

			# Get most abundant read length
			read_length = sorted(read_length)[-1]

			# If at least half is paired, consider paired end reads
			if paired > (n / 2):
				read_type = "paired"
				paired = True
			else:
				read_type = "single"
				paired = False

			files.append([read_length, read_type, paired])

		# Check agreement between different files
		# if all values are equal, set to that value;
		# if not, set to None and warn the user about the inconsistency
		for i, feature in enumerate(["read_length", "read_type", "paired"]):
			setattr(self, feature, files[0][i] if len(set(f[i] for f in files)) == 1 else None)

			if getattr(self, feature) is None:
				print(_warnings.warn("Not all input files agree on read type/length for sample : %s" % self.name))


@copy
class PipelineInterface(object):
	"""
	This class parses, holds, and returns information for a yaml file that
	specifies tells the looper how to interact with each individual pipeline. This
	includes both resources to request for cluster job submission, as well as
	arguments to be passed from the sample annotation metadata to the pipeline
	"""

	def __init__(self, yaml_config_file):
		import yaml
		self.looper_config_file = yaml_config_file
		self.looper_config = yaml.load(open(yaml_config_file, 'r'))

	def select_pipeline(self, pipeline_name):
		"""
		Check to make sure that pipeline has an entry and if so, return it
		"""
		if pipeline_name not in self.looper_config:
			print(
				"Missing pipeline description: '" + pipeline_name + "' not found in '" +
				self.looper_config_file + "'")
			# Should I just use defaults or force you to define this?
			raise Exception("You need to teach the looper about that pipeline")

		return(self.looper_config[pipeline_name])

	def get_pipeline_name(self, pipeline_name):
		config = self.select_pipeline(pipeline_name)

		if "name" not in config:
			# Discard extensions for the name
			name = _os.path.splitext(pipeline_name)[0]
		else:
			name = config["name"]

		return name

	def choose_resource_package(self, pipeline_name, file_size):
		"""
		Given a pipeline name (pipeline_name) and a file size (size), return the
		resource configuratio specified by the config file.
		"""
		config = self.select_pipeline(pipeline_name)

		if "resources" not in config:
			msg = "No resources found for '" + pipeline_name + "' in '" + self.looper_config_file + "'"
			# Should I just use defaults or force you to define this?
			raise IOError(msg)

		table = config['resources']
		current_pick = "default"

		for option in table:
			if table[option]['file_size'] == "0":
				continue
			if file_size < float(table[option]['file_size']):
				continue
			elif float(table[option]['file_size']) > float(table[current_pick]['file_size']):
				current_pick = option

		# print("choose:" + str(current_pick))

		return(table[current_pick])

	def get_arg_string(self, pipeline_name, sample):
		"""
		For a given pipeline and sample, return the argument string
		"""
		config = self.select_pipeline(pipeline_name)

		if "arguments" not in config:
			print(
				"No arguments found for '" + pipeline_name + "' in '" +
				self.looper_config_file + "'")
			return("")  # empty argstring

		argstring = ""
		args = config['arguments']
		for key, value in args.iteritems():
			print(key, value)
			if value is None:
				arg = ""
			else:
				try:
					arg = getattr(sample, value)
				except AttributeError as e:
					print(
						"Pipeline '" + pipeline_name + "' requests for argument '" +
						key + "' a sample attribute named '" + value + "'" +
						" but no such attribute exists for sample '" +
						sample.sample_name + "'")
					raise e

				argstring += " " + str(key) + " " + str(arg)

		return(argstring)


@copy
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
		self.mappings = {k.upper(): v for k, v in self.mappings.items()}

	def build_pipeline(self, protocol):
		# print("Building pipeline for protocol '" + protocol + "'")

		if protocol not in self.mappings:
			print("  Missing Protocol Mapping: '" + protocol + "' is not found in '" + self.mappings_file + "'")
			return([])  # empty list

		# print(self.mappings[protocol]) # The raw string with mappings
		# First list level
		split_jobs = [x.strip() for x in self.mappings[protocol].split(';')]
		# print(split_jobs) # Split into a list
		return(split_jobs)  # hack works if no parllelism

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


class CommandChecker(object):
	"""
	This class checks if programs specified in a
	pipeline config file (under "tools") exist and are callable.
	"""
	def __init__(self, config):
		import yaml

		self.config = yaml.load(open(config, 'r'))

		# Check if ALL returned elements are True
		if not all(map(self.check_command, self.config["tools"].items())):
			raise BaseException("Config file contains non-callable tools.")

	@staticmethod
	def check_command((name, command)):
		"""
		Check if command can be called.
		"""
		import os

		# Use `command` to see if command is callable, store exit code
		code = os.system("command -v {0} >/dev/null 2>&1 || {{ exit 1; }}".format(command))

		# If exit code is not 0, report which command failed and return False, else return True
		if code != 0:
			print("Command '{0}' is not callable: {1}".format(name, command))
			return False
		else:
			return True
