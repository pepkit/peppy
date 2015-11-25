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


class Paths(object):
	"""
	A class to hold paths as attributes.
	"""
	def __repr__(self):
		return "Paths object."


class AttributeDict(object):
	"""
	A class to convert a nested Dictionary into an object with key-values
	accessibly using attribute notation (AttributeDict.attribute) instead of
	key notation (Dict["key"]). This class recursively sets Dicts to objects,
	allowing you to recurse down nested dicts (like: AttributeDict.attr.attr)
	"""
	def __init__(self, **entries):
		self.add_entries(**entries)

	def add_entries(self, **entries):
		for key, value in entries.items():
			if type(value) is dict:
				self.__dict__[key] = AttributeDict(**value)
			else:
				self.__dict__[key] = value

	def __getitem__(self, key):
		"""
		Provides dict-style access to attributes
		"""
		return getattr(self, key)


class Project(AttributeDict):
	"""
	A class to model a Project.

	:param config_file: Project config file (yaml).
	:type config_file: str
	:param dry: If dry mode is activated, no directories will be created upon project instantiation.
	:type dry: bool

	:Example:

	from pipelines import Project
	prj = Project("config.yaml")
	"""
	def __init__(self, config_file, dry=False):
		# super(Project, self).__init__(**config_file)
		# Path structure
		# self.paths = Paths()

		# include the path to the config file
		self.config_file = _os.path.abspath(config_file)

		# Parse config file
		self.parse_config_file()

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
		return "Project '%s'" % self.name

	def parse_config_file(self):
		"""
		Parse provided yaml config file and check required fields exist.
		"""
		with open(self.config_file, 'r') as handle:
			self.config = _yaml.load(handle)

		# parse yaml into the project's attributes
		self.add_entries(**self.config)
		# All this is no longer necessary:
		# self.paths.output_dir = self.config['paths']['output_dir']
		# for key, value in self.config.items():
		# 	# set that attribute to a holder
		# 		if not hasattr(self, key):
		# 			if type(value) is dict:
		# 				setattr(self, key, Paths())
		# 			else:
		# 				print key
		# 				if value is not None:
		# 					setattr(self, key, value)

		# 		if type(value) is dict:
		# 			for key2, value2 in value.items():
		# 				if value2 is not None:
		# 					setattr(getattr(self, key), key2, value2)

		# These are required variables which have absolute paths
		mandatory = ["output_dir", "pipelines_dir"]
		for var in mandatory:
			if not hasattr(self.paths, var):
				raise KeyError("Required field not in config file: %s" % var)

		# Variables which are relative to the config file
		# All variables in these sections should be relative to the project config
		relative_sections = ["metadata", "pipeline_config"]

		for sect in relative_sections:
			if not hasattr(self, sect):
				continue
			relative_vars = getattr(self, sect)
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

	def add_sample_sheet(self, csv=None, permissive=True):
		"""
		Build a `SampleSheet` object from a csv file and
		add it and its samples to the project.

		:param csv: Path to csv file.
		:type csv: str
		:param permissive: Should it throw error if sample input is not found/readable?.
		:type permissive: bool
		"""
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
			# TODO: get organism: genome mapping into config file
			# and check is selected organism is available.
			# Check sample is from a supported genome
			# if sample.organism not in self.config["genomes"]:
			#     raise TypeError("Sample's genome is not supported.")
			self.add_sample(sample)
			sample.set_file_paths()

		# Merge samples using merge table:
		# 1. groupby "sample_name" in mergeTable, get "data_path" of all samples
		# 2. (optinal) remove existing samples "unmerged" samples with same "data_path" from project
		# 3. make new samples with merged inputs
		if "merge_table" in self.config["metadata"].keys():
			if self.config["metadata"]["merge_table"] is not None:
				if _os.path.isfile(self.config["metadata"]["merge_table"]):
					# read in merge table
					merge_table = _pd.read_csv(self.config["metadata"]["merge_table"])
					# for each, grab all input files
					for name, indices in merge_table.groupby(['sample_name']).groups.items():
						data_paths = list()
						for index in indices:
							sample = Sample(merge_table.ix[index])
							sample.prj = self
							sample.locate_data_source()
							data_paths.append(sample.data_path)
						# add merged flag to samples and
						# remove them "unmerged" ones from project if desired
						to_pop = list()
						for sample in self.samples:
							sample.merged = False  # flag all previous samples as not merged
							if True and sample.data_path in data_paths:
								print("popping %s" % sample.sample_name)
								to_pop.append(self.samples.index(sample))
						[self.samples.pop(index) for index in sorted(to_pop, reverse=True)]

						# Add merged samples
						# get organism and library from first "unmerged" samples
						sample = Sample(merge_table.ix[indices[0]])
						sample.data_path = " ".join(data_paths)
						self.add_sample(sample)
						sample.set_file_paths()
						sample.merged = True

		# With all samples, prepare make sample dirs and get read type
		for sample in self.samples:
			sample.get_genome()
			if not sample.check_input_exists():
				continue

			# get read type and length if not provided
			if not hasattr(sample, "read_type"):
				sample.get_read_type()
			if not hasattr(sample, "read_type"):
				sample.get_read_length()

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
		# Return generic sample if library is not specified
		if not hasattr(series, "library"):
			return Sample(series)

		library = series["library"].upper()

		# TODO:
		# The later will be replaced with a config-specified mapping.
		# e.g.:
		if library in ["CHIP", "CHIP-SEQ"]:
			return ChIPseqSample(series)
		elif library in ["CHIPMENTATION", "CM"]:
			return ChIPmentation(series)
		elif library in ["DNASE", "DNASESEQ", "DNASE-SEQ"]:
			return DNaseSample(series)
		elif library in ["ATAC", "ATACSEQ", "ATAC-SEQ"]:
			return ATACseqSample(series)
		elif library in ["QUANT", "QUANTSEQ", "QUANT-SEQ"]:
			return QuantseqSample(series)
		elif library in ["CHEM", "CHEMSEQ", "CHEM-SEQ"]:
			return ChemseqSample(series)
		elif library in ["RRBS"]:
			return RRBS(series)
		elif library in ["WGBS", "WGBS-SEQ"]:
			return WGBS(series)
		elif library in ["SMART", "SMARTSEQ", "SMART-SEQ"]:
			return SMARTseqSample(series)
		else:
			# raise TypeError("Sample is not in known sample class.")
			return Sample(series)

	def make_samples(self):
		"""
		Creates samples from annotation sheet dependent on library and adds them to the project.
		"""
		for i in range(len(self.df)):
			self.samples.append(self.make_sample(self.df.ix[i]))

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
		# Passed series must either be a pd.Series or a daugther class
		if not isinstance(series, _pd.Series):
			raise TypeError("Provided object is not a pandas Series.")
		super(Sample, self).__init__()

		# Set series attributes on self
		for key, value in series.to_dict().items():
			setattr(self, key, value)

		# Check if required attributes exist and are not empty
		self.check_valid()

		# Get name for sample:
		# this is a concatenation of all passed Series attributes except "unmappedBam"
		# self.generate_name()

		# check if sample is to be analysed with cuts
		# cuts = self.config["libraries"]["atacseq"] + self.config["libraries"]["cm"]
		# self.tagmented = True if self.library.upper() in cuts else False

		# Get track colour
		# self.getTrackColour()

		# Sample dirs
		self.paths = Paths()
		# Only when sample is added to project, can paths be added -
		# this is because sample-specific files will be created in a data root directory dependendt on the project.
		# The SampleSheet object, after beeing added to a project, will
		# call Sample.set_file_paths(), creating the data_path of the sample (the bam file)
		# and other paths.

	def __repr__(self):
		return "Sample '%s'" % self.sample_name

	def check_valid(self):
		"""
		Check provided sample annotation is valid.

		It requires fields `sample_name`, `library`, `organism` to be existent and non-empty.
		If `data_path` is not provided or empty, then `flowcell`, `lane`, `BSF_name` are all required.
		"""
		def check_attrs(req):
			if not all([hasattr(self, attr) for attr in req]):
				raise ValueError("Required values for sample do not exist.")

			if any([attr == "nan" for attr in req]):
				raise ValueError("Required values for sample are empty.")

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
		# if path is not specified, use default:
		# prj.paths.submission_dir + sample_name + yaml
		if path is None:
			path = _os.path.join(self.prj.paths.submission_subdir, self.sample_name + ".yaml")

		serial = self.__dict__

		# remove unserialasable fields (project and config objects, etc...)
		for key in serial.keys():
			if type(serial[key]) not in [str, int, bool]:
				del serial[key]
		# write
		with open(path, 'w') as outfile:
			outfile.write(_yaml.dump(serial, default_flow_style=False))

	def locate_data_source(self):
		"""
		Locates the path of input file `data_path` based on a regex.
		"""
		default_regex = "/scratch/lab_bsf/samples/{flowcell}/{flowcell}_{lane}_samples/{flowcell}_{lane}#{BSF_name}.bam"  # default regex

		# get bam file in regex form dependent on the "source" specified for each sample
		if hasattr(self, "data_source"):
			self.data_path = self.prj.config["data_sources"][self.data_source].format(**self.__dict__)
		# if absent is the default regex
		else:
			self.data_path = default_regex.format(**self.__dict__)

	def get_genome(self):
		"""
		Get genome and transcriptome, based on project config file.
		If not available (matching config), genome and transcriptome will be set to sample.organism.
		"""
		try:
			self.genome = getattr(self.prj.config.genomes, self.organism)
		except:
			self.genome = self.organism
		# get transcriptome
		try:
			self.transcriptome = getattr(self.prj.config.transcriptomes, self.organism)
		except:
			self.transcriptome = self.organism

	def set_file_paths(self):
		"""
		Sets the paths of all files for this sample.
		"""
		# If sample does not have data_path, then let's build BSF path to unaligned bam.
		# this is built on a regex specified in the config file or the custom one (see `Project`).
		if hasattr(self, "data_path"):
			if (self.data_path == "nan") or (self.data_path == ""):
				self.locate_data_source()
		else:
			self.locate_data_source()

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
		for path in self.data_path.split(" "):
			if not _os.path.exists(path):
				l.append(path)

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

		# for samples with multiple original bams, get only first
		if type(self.data_path) == list:
			bam = self.data_path[0]
		else:
			bam = self.data_path

		try:
			# view reads
			p = sp.Popen(['samtools', 'view', bam], stdout=sp.PIPE)

			# Count paired alignments
			paired = 0
			read_length = Counter()
			while n > 0:
				line = p.stdout.next().split("\t")
				flag = int(line[1])
				read_length[len(line[9])] += 1
				if 1 & flag:  # check decimal flag contains 1 (paired)
					paired += 1
				n -= 1
			p.kill()
		except:
			if not permissive:
				raise IOError("Bam file does not exist or cannot be read: %s" % bam)
			else:
				print(_warnings.warn("Bam file does not exist or cannot be read: %s" % bam))
				self.read_length = None
				self.read_type = None
				self.paired = None

				return

		# Get most abundant read length
		self.read_length = sorted(read_length)[-1]

		# If at least half is paired, consider paired end reads
		if paired > (n / 2):
			self.read_type = "paired"
			self.paired = True
		else:
			self.read_type = "single"
			self.paired = False

	def getTrackColour(self):
		"""
		Get a colour for a genome browser track based on the IP.
		"""
		# This is ChIP-centric, and therefore if no "ip" attrbute,
		# will just pick one color randomly from a gradient.
		import random

		if hasattr(self, "ip"):
			if self.ip in self.config["trackcolours"].keys():
				self.trackColour = self.config["trackcolours"][self.ip]
			else:
				if self.library in ["ATAC", "ATACSEQ", "ATAC-SEQ"]:
					self.trackColour = self.config["trackcolours"]["ATAC"]
				elif self.library in ["DNASE", "DNASESEQ", "DNASE-SEQ"]:
					self.trackColour = self.config["trackcolours"]["DNASE"]
				else:
					self.trackColour = random.sample(self.config["colourgradient"], 1)[0]  # pick one randomly
		else:
			self.trackColour = random.sample(self.config["colourgradient"], 1)[0]  # pick one randomly


class ChIPseqSample(Sample):
	"""
	Class to model ChIP-seq samples based on the generic Sample class (itself a pandas.Series).

	:param series: Pandas `Series` object.
	:type series: pandas.Series

	:Example:

	from pipelines import Project, SampleSheet, ChIPseqSample
	prj = Project("ngs")
	sheet = SampleSheet("/projects/example/sheet.csv", prj)
	s1 = ChIPseqSample(sheet.ix[0])
	"""
	def __init__(self, series):

		# Passed series must either be a pd.Series or a daugther class
		if not isinstance(series, _pd.Series):
			raise TypeError("Provided object is not a pandas Series.")
		super(ChIPseqSample, self).__init__(series)

		# Get type of factor
		# TODO: get config file specifying broad/narrow factors
		# e.g. self.broad = True if self.library in self.prj.config["broadfactors"] else False
		self.broad = True if self.library in ["H3K27me3", "H3K36me3"] else False
		self.histone = True if self.library in ["H3", "H2B"] else False

	def __repr__(self):
		return "ChIP-seq sample '%s'" % self.sample_name

	def set_file_paths(self):
		"""
		Sets the paths of all files for this sample.
		"""
		# Inherit paths from Sample by running Sample's set_file_paths()
		super(ChIPseqSample, self).set_file_paths()

		# Files in the root of the sample dir
		self.fastqc = _os.path.join(self.paths.sample_root, self.sample_name + ".fastqc.zip")
		self.trimlog = _os.path.join(self.paths.sample_root, self.sample_name + ".trimlog.txt")
		self.aln_rates = _os.path.join(self.paths.sample_root, self.sample_name + ".aln_rates.txt")
		self.aln_metrics = _os.path.join(self.paths.sample_root, self.sample_name + ".aln_metrics.txt")
		self.dups_metrics = _os.path.join(self.paths.sample_root, self.sample_name + ".dups_metrics.txt")

		# Unmapped: merged bam, fastq, trimmed fastq
		self.paths.unmapped = _os.path.join(self.paths.sample_root, "unmapped")
		self.unmapped = _os.path.join(self.paths.unmapped, self.sample_name + ".bam")
		self.fastq = _os.path.join(self.paths.unmapped, self.sample_name + ".fastq")
		self.fastq1 = _os.path.join(self.paths.unmapped, self.sample_name + ".1.fastq")
		self.fastq2 = _os.path.join(self.paths.unmapped, self.sample_name + ".2.fastq")
		self.fastqUnpaired = _os.path.join(self.paths.unmapped, self.sample_name + ".unpaired.fastq")
		self.trimmed = _os.path.join(self.paths.unmapped, self.sample_name + ".trimmed.fastq")
		self.trimmed1 = _os.path.join(self.paths.unmapped, self.sample_name + ".1.trimmed.fastq")
		self.trimmed2 = _os.path.join(self.paths.unmapped, self.sample_name + ".2.trimmed.fastq")
		self.trimmed1Unpaired = _os.path.join(self.paths.unmapped, self.sample_name + ".1_unpaired.trimmed.fastq")
		self.trimmed2Unpaired = _os.path.join(self.paths.unmapped, self.sample_name + ".2_unpaired.trimmed.fastq")

		# Mapped: mapped, duplicates marked, removed, reads shifted
		self.paths.mapped = _os.path.join(self.paths.sample_root, "mapped")
		self.mapped = _os.path.join(self.paths.mapped, self.sample_name + ".trimmed.bowtie2.bam")
		self.filtered = _os.path.join(self.paths.mapped, self.sample_name + ".trimmed.bowtie2.filtered.bam")

		# Files in the root of the sample dir
		self.frip = _os.path.join(self.paths.sample_root, self.sample_name + "_FRiP.txt")

		# Coverage: read coverage in windows genome-wide
		self.paths.coverage = _os.path.join(self.paths.sample_root, "coverage")
		self.coverage = _os.path.join(self.paths.coverage, self.sample_name + ".cov")

		self.qc = _os.path.join(self.paths.sample_root, self.sample_name + "_qc.tsv")
		self.qc_plot = _os.path.join(self.paths.sample_root, self.sample_name + "_qc.pdf")

		# Peaks: peaks called and derivate files
		self.paths.peaks = _os.path.join(self.paths.sample_root, "peaks")
		self.peaks = _os.path.join(self.paths.peaks, self.sample_name + ("_peaks.narrowPeak" if not self.broad else "_peaks.broadPeak"))
		self.peaks_motif_centered = _os.path.join(self.paths.peaks, self.sample_name + "_peaks.motif_centered.bed")
		self.peaks_motif_annotated = _os.path.join(self.paths.peaks, self.sample_name + "_peaks._motif_annotated.bed")

		# Motifs
		self.paths.motifs = _os.path.join(self.paths.sample_root, "motifs", self.sample_name)


class ChIPmentation(ChIPseqSample):
	"""
	Class to model ChIPmentation samples based on the ChIPseqSample class.

	:param series: Pandas `Series` object.
	:type series: pandas.Series
	"""
	def __init__(self, series):

		# Use _pd.Series object to have all sample attributes
		if not isinstance(series, _pd.Series):
			raise TypeError("Provided object is not a pandas Series.")
		super(ChIPmentation, self).__init__(series)

	def __repr__(self):
		return "ChIPmentation sample '%s'" % self.sample_name


class DNaseSample(ChIPseqSample):
	"""
	Class to model DNase-seq samples based on the ChIPseqSample class.

	:param series: Pandas `Series` object.
	:type series: pandas.Series
	"""
	def __init__(self, series):

		# Use _pd.Series object to have all sample attributes
		if not isinstance(series, _pd.Series):
			raise TypeError("Provided object is not a pandas Series.")
		super(DNaseSample, self).__init__(series)

	def __repr__(self):
		return "DNase-seq sample '%s'" % self.sample_name


class ATACseqSample(ChIPseqSample):
	"""
	Class to model ATAC-seq samples based on the ChIPseqSample class.

	:param series: Pandas `Series` object.
	:type series: pandas.Series
	"""
	def __init__(self, series):

		# Use _pd.Series object to have all sample attributes
		if not isinstance(series, _pd.Series):
			raise TypeError("Provided object is not a pandas Series.")
		super(ATACseqSample, self).__init__(series)

	def __repr__(self):
		return "ATAC-seq sample '%s'" % self.sample_name

	def set_file_paths(self):
		"""
		Sets the paths of all files for this sample.
		"""
		# Inherit paths from Sample by running Sample's set_file_paths()
		super(ATACseqSample, self).set_file_paths()

		# Files in the root of the sample dir
		self.fastqc = _os.path.join(self.paths.sample_root, self.sample_name + ".fastqc.zip")
		self.trimlog = _os.path.join(self.paths.sample_root, self.sample_name + ".trimlog.txt")
		self.aln_rates = _os.path.join(self.paths.sample_root, self.sample_name + ".aln_rates.txt")
		self.aln_metrics = _os.path.join(self.paths.sample_root, self.sample_name + ".aln_metrics.txt")
		self.dups_metrics = _os.path.join(self.paths.sample_root, self.sample_name + ".dups_metrics.txt")

		# Unmapped: merged bam, fastq, trimmed fastq
		self.paths.unmapped = _os.path.join(self.paths.sample_root, "unmapped")
		self.unmapped = _os.path.join(self.paths.unmapped, self.sample_name + ".bam")
		self.fastq = _os.path.join(self.paths.unmapped, self.sample_name + ".fastq")
		self.fastq1 = _os.path.join(self.paths.unmapped, self.sample_name + ".1.fastq")
		self.fastq2 = _os.path.join(self.paths.unmapped, self.sample_name + ".2.fastq")
		self.fastqUnpaired = _os.path.join(self.paths.unmapped, self.sample_name + ".unpaired.fastq")
		self.trimmed = _os.path.join(self.paths.unmapped, self.sample_name + ".trimmed.fastq")
		self.trimmed1 = _os.path.join(self.paths.unmapped, self.sample_name + ".1.trimmed.fastq")
		self.trimmed2 = _os.path.join(self.paths.unmapped, self.sample_name + ".2.trimmed.fastq")
		self.trimmed1Unpaired = _os.path.join(self.paths.unmapped, self.sample_name + ".1_unpaired.trimmed.fastq")
		self.trimmed2Unpaired = _os.path.join(self.paths.unmapped, self.sample_name + ".2_unpaired.trimmed.fastq")

		# Mapped: mapped, duplicates marked, removed, reads shifted
		self.paths.mapped = _os.path.join(self.paths.sample_root, "mapped")
		self.mapped = _os.path.join(self.paths.mapped, self.sample_name + ".trimmed.bowtie2.bam")
		self.filtered = _os.path.join(self.paths.mapped, self.sample_name + ".trimmed.bowtie2.filtered.bam")

		# Files in the root of the sample dir
		self.frip = _os.path.join(self.paths.sample_root, self.name + "_FRiP.txt")

		# Mapped: mapped, duplicates marked, removed, reads shifted
		# this will create additional bam files with reads shifted
		self.filteredshifted = _os.path.join(self.paths.mapped, self.name + ".trimmed.bowtie2.filtered.shifted.bam")

		# Coverage: read coverage in windows genome-wide
		self.paths.coverage = _os.path.join(self.paths.sample_root, "coverage")
		self.coverage = _os.path.join(self.paths.coverage, self.name + ".cov")

		self.insertplot = _os.path.join(self.paths.sample_root, self.name + "_insertLengths.pdf")
		self.insertdata = _os.path.join(self.paths.sample_root, self.name + "_insertLengths.csv")
		self.qc = _os.path.join(self.paths.sample_root, self.name + "_qc.tsv")
		self.qc_plot = _os.path.join(self.paths.sample_root, self.name + "_qc.pdf")

		# Peaks: peaks called and derivate files
		self.paths.peaks = _os.path.join(self.paths.sample_root, "peaks")
		self.peaks = _os.path.join(self.paths.peaks, self.name + "_peaks.narrowPeak")
		self.filteredPeaks = _os.path.join(self.paths.peaks, self.name + "_peaks.filtered.bed")


class QuantseqSample(Sample):
	"""
	Class to model Quant-seq samples based on the generic Sample class (itself a pandas.Series).

	:param series: Pandas `Series` object.
	:type series: pandas.Series

	:Example:

	from pipelines import Project, SampleSheet, QuantseqSample
	prj = Project("ngs")
	sheet = SampleSheet("/projects/example/sheet.csv", prj)
	s1 = QuantseqSample(sheet.ix[0])
	"""
	def __init__(self, series):

		# Passed series must either be a pd.Series or a daugther class
		if not isinstance(series, _pd.Series):
			raise TypeError("Provided object is not a pandas Series.")
		super(QuantseqSample, self).__init__(series)

	def __repr__(self):
		return "Quant-seq sample '%s'" % self.sample_name

	def set_file_paths(self):
		"""
		Sets the paths of all files for this sample.
		"""
		# Inherit paths from Sample by running Sample's set_file_paths()
		super(QuantseqSample, self).set_file_paths()

		# Files in the root of the sample dir
		self.fastqc = _os.path.join(self.paths.sample_root, self.sample_name + ".fastqc.zip")
		self.trimlog = _os.path.join(self.paths.sample_root, self.sample_name + ".trimlog.txt")
		self.aln_rates = _os.path.join(self.paths.sample_root, self.sample_name + ".aln_rates.txt")
		self.aln_metrics = _os.path.join(self.paths.sample_root, self.sample_name + ".aln_metrics.txt")
		self.dups_metrics = _os.path.join(self.paths.sample_root, self.sample_name + ".dups_metrics.txt")

		# Unmapped: merged bam, fastq, trimmed fastq
		self.paths.unmapped = _os.path.join(self.paths.sample_root, "unmapped")
		self.unmapped = _os.path.join(self.paths.unmapped, self.sample_name + ".bam")
		self.fastq = _os.path.join(self.paths.unmapped, self.sample_name + ".fastq")
		self.fastq1 = _os.path.join(self.paths.unmapped, self.sample_name + ".1.fastq")
		self.fastq2 = _os.path.join(self.paths.unmapped, self.sample_name + ".2.fastq")
		self.fastqUnpaired = _os.path.join(self.paths.unmapped, self.sample_name + ".unpaired.fastq")
		self.trimmed = _os.path.join(self.paths.unmapped, self.sample_name + ".trimmed.fastq")
		self.trimmed1 = _os.path.join(self.paths.unmapped, self.sample_name + ".1.trimmed.fastq")
		self.trimmed2 = _os.path.join(self.paths.unmapped, self.sample_name + ".2.trimmed.fastq")
		self.trimmed1Unpaired = _os.path.join(self.paths.unmapped, self.sample_name + ".1_unpaired.trimmed.fastq")
		self.trimmed2Unpaired = _os.path.join(self.paths.unmapped, self.sample_name + ".2_unpaired.trimmed.fastq")

		# Mapped: mapped, duplicates marked, removed, reads shifted
		self.paths.mapped = _os.path.join(self.paths.sample_root, "mapped")
		self.mapped = _os.path.join(self.paths.mapped, self.sample_name + ".trimmed.bowtie2.bam")
		self.filtered = _os.path.join(self.paths.mapped, self.sample_name + ".trimmed.bowtie2.filtered.bam")

		self.ercc_aln_rates = _os.path.join(self.paths.sample_root, self.name + "_ercc.aln_rates.txt")
		self.ercc_aln_metrics = _os.path.join(self.paths.sample_root, self.name + "_ercc.aln_metrics.txt")
		self.ercc_dups_metrics = _os.path.join(self.paths.sample_root, self.name + "_ercc.dups_metrics.txt")

		# Mapped: Tophat mapped, duplicates marked, removed
		self.paths.mapped = _os.path.join(self.paths.sample_root, "mapped")
		self.mapped = _os.path.join(self.paths.mapped, "accepted_hits.bam")
		self.filtered = _os.path.join(self.paths.mapped, self.name + ".trimmed.bowtie2.filtered.bam")
		# ercc alignments
		self.ercc_mapped = _os.path.join(self.paths.mapped, self.name + "_ercc.bam")
		self.ercc_filtered = _os.path.join(self.paths.mapped, self.name + "_ercc.filtered.bam")
		# kallisto pseudoalignments
		self.pseudomapped = _os.path.join(self.paths.mapped, self.name + ".pseudoalignment.bam")

		# RNA quantification
		self.paths.quant = _os.path.join(self.paths.sample_root, "quantification")
		self.quant = _os.path.join(self.paths.quant, "tophat-htseq_quantification.tsv")
		self.erccQuant = _os.path.join(self.paths.quant, "tophat-htseq_quantification_ercc.tsv")
		self.kallistoQuant = _os.path.join(self.paths.quant, "abundance.tsv")


class ChemseqSample(ChIPseqSample):
	"""
	Class to model Chem-seq samples based on the ChIPseqSample class.

	:param series: Pandas `Series` object.
	:type series: pandas.Series
	"""
	def __init__(self, series):

		# Use _pd.Series object to have all sample attributes
		if not isinstance(series, _pd.Series):
			raise TypeError("Provided object is not a pandas Series.")
		super(ChemseqSample, self).__init__(series)

	def __repr__(self):
		return "Chem-seq sample '%s'" % self.sample_name


class COREseq(Sample):
	"""
	Class to model Chem-seq samples based on the Sample class.

	:param series: Pandas `Series` object.
	:type series: pandas.Series
	"""
	def __init__(self, series):

		# Use _pd.Series object to have all sample attributes
		if not isinstance(series, _pd.Series):
			raise TypeError("Provided object is not a pandas Series.")
		super(COREseq, self).__init__(series)

	def __repr__(self):
		return "CORE-seq sample '%s'" % self.sample_name


class RRBS(Sample):
	"""
	Class to model Chem-seq samples based on the Sample class.

	:param series: Pandas `Series` object.
	:type series: pandas.Series
	"""
	def __init__(self, series):

		# Use _pd.Series object to have all sample attributes
		if not isinstance(series, _pd.Series):
			raise TypeError("Provided object is not a pandas Series.")
		super(RRBS, self).__init__(series)

	def __repr__(self):
		return "RRBS sample '%s'" % self.sample_name


class WGBS(Sample):
	"""
	Class to model Chem-seq samples based on the Sample class.

	:param series: Pandas `Series` object.
	:type series: pandas.Series
	"""
	def __init__(self, series):

		# Use _pd.Series object to have all sample attributes
		if not isinstance(series, _pd.Series):
			raise TypeError("Provided object is not a pandas Series.")
		super(WGBS, self).__init__(series)

	def __repr__(self):
		return "WGBS-seq sample '%s'" % self.sample_name


class SMARTseqSample(Sample):
	"""
	Class to model Chem-seq samples based on the Sample class.

	:param series: Pandas `Series` object.
	:type series: pandas.Series
	"""
	def __init__(self, series):

		# Use _pd.Series object to have all sample attributes
		if not isinstance(series, _pd.Series):
			raise TypeError("Provided object is not a pandas Series.")
		super(SMARTseqSample, self).__init__(series)

	def __repr__(self):
		return "SMART-seq sample '%s'" % self.sample_name
