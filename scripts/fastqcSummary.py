#!/usr/bin/env python

import os, inspect, ConfigParser, subprocess, sys, errno, glob, zipfile, csv
from argparse import ArgumentParser
#import csv
#import 
#import glob
#import 
#import re

# constants:
nThreadsPerCpu = 4
nMemPerThread = 1024
nCpusSlurm = 8
defaultRawDataPath = "/fhgfs/groups/lab_bsf/samples/"

# parse user-supplied arguments:
parser = ArgumentParser(description='FASTQC')
parser.add_argument('-c', '--config-file', dest='confFile', help="Supply config file with [-c]. The path of the sample annotation sheet will be parsed from this. Example: /fhgfs/groups/lab_bock/shared/COREseq/config.txt")
parser.add_argument('-a', '--annot-file', dest='annotFile', help="Specify a sample annotation sheet directly")
parser.add_argument('-o', '--output-dir', dest='outputDir', help="Directory to write results to")
parser.add_argument('-f', '--fastqc', dest='fastqcPath', help="Full path of FASTQC exectuable", default="/cm/shared/apps/FastQC/0.11.2/fastqc")
parser.add_argument('-s', '--slurm', dest='useSlurm', action='store_true', help="Execute script on SLURM cluster.", default=False)
parser.add_argument('-q', '--quick-summary', dest='quickSummary', action='store_true', help="Skip FastQC, just write the summary report", default=False)
parser.add_argument('-p', '--parallel', dest='nCpus', help="Number of CPUs to use (going to start 4 threads per CPU)", default=1)
parser.add_argument('-d', '--raw-path', dest='rawPath', help="Raw data path")
args, remaining_args = parser.parse_known_args()

# get input directory either directly as command line argument (highest priority) or from a config file:
annotFile = None
outputDir = None
rawDataPath = defaultRawDataPath
if args.annotFile:
	annotFile = args.annotFile
elif args.confFile: 
	#get configurations
	config = ConfigParser.ConfigParser({"results": None, "raw_data_path": defaultRawDataPath}) 
	config.readfp(open(os.path.abspath(args.confFile)))
	annotFile = config.get("paths","psa")
	if annotFile is None:
		print "The config file provided does not define an annotation sheet (parameter name: 'psa')"
		raise SystemExit
	outputDir = config.get("paths","project_root")
	if outputDir is not None:
		outputDir = outputDir + "/fastqc"
	rawDataPath = config.get("paths","raw_data_path")
else:
	print "Supply either a config file (--config-file=X) or the full path of the annotation sheet (--annot-file=X)"
	raise SystemExit

# define relevant paths:
scriptPath = os.path.abspath(inspect.getfile(inspect.currentframe()))
fastqcPath = os.path.abspath(args.fastqcPath)
annotFile = os.path.abspath(annotFile)
if args.outputDir:
	outputDir = args.outputDir
if outputDir is None:
	print "No output directory specified (--output-dir=X)"
	raise SystemExit
outputDir = os.path.abspath(args.outputDir)
if args.rawPath:
	rawDataPath = args.rawPath
nCpus = args.nCpus

# print some basic information:
print "FASTQC Summary"
print "----"
print "Full script path:\t" + scriptPath
print "Full FASTQC path:\t" + fastqcPath
print "Raw data root directory:\t" + rawDataPath
print "Sample sheet:\t" + annotFile
print "Output root directory:\t:" + outputDir
print "#CPUs:\t:" + str(nCpus)
print "#treads/CPU:\t:" + str(nThreadsPerCpu)
print "#mem/thread:\t:" + str(nMemPerThread)
print "----"

# create results directory if it doesn't exist yet:
try:
	os.makedirs(outputDir)
except OSError as exception:
	if exception.errno != errno.EEXIST:
		raise

### MAIN JOB EXECUTION ### 

# if desired, submit the job for execution on the cluster:
if args.useSlurm:
	slurmScript = outputDir + "/fastqc_slurm.sub"
	slurmLog = outputDir + "/fastqc_slurm.log"

	with open(slurmScript, "w") as fout:
		fout.write("#!/bin/bash\n")
		fout.write("#SBATCH --job-name=fastqc\n")
		fout.write("#SBATCH --mem-per-cpu=" + str(nThreadsPerCpu * nMemPerThread) + "\n")
		fout.write("#SBATCH --cpus-per-task=" + str(nCpus) + "\n")
		fout.write("#SBATCH -m block\n")
		fout.write("#SBATCH --partition=mediumq\n")
		fout.write("#SBATCH --time=24:00:00\n")
		fout.write("#SBATCH --output " + slurmLog + "\n")
		fout.write("echo 'Compute node:' `hostname`\n")
		fout.write("echo 'Start time:' `date +'%Y-%m-%d %T'`\n")
		fout.write("python " + scriptPath + " --raw-path=" + rawDataPath + " --annot-file=" + annotFile + " --parallel=" + str(nCpusSlurm) + " --output-dir=" + outputDir + "\n")
		fout.write("echo 'End time:' `date +'%Y-%m-%d %T'`\n")

	subprocess.check_call(["sbatch", slurmScript])

# otherwise, just execute the command directly on the current machine:
# (this is what the SLURM-based execution mode will do once the job has been allocated to a specific node)
else:
	# execute FastQC on all BAM files:
	if not args.quickSummary:
		subprocess.check_call([fastqcPath, "--version"])

		bamFolders = {}
		
		with open(annotFile, "rb") as annotF:
			annotDict = csv.DictReader(annotF)
			for row in annotDict:
				bamDir = rawDataPath + row["flowcell"] + "/" + row["flowcell"] + "_" + row["lane"] + "_samples/"
				bamFile = bamDir + row["flowcell"] + "_" + row["lane"] + "#" + row["BSF_name"] + ".bam"

				if os.path.isfile(bamFile):
					bamFolders[bamDir] = True

		for bamFolder in bamFolders:
			subprocess.check_call(fastqcPath + " " + bamFolder+"/*.bam --threads="+str(int(nCpus) * nThreadsPerCpu) + " --noextract --outdir="+outputDir, shell=True) # N.B. can't use the proper syntax with an array for args, because FastQC cannot handle the quoted string ('...') as an input path name

	allKeys = {}
	resultsMap = {}	
	zipSuffix = ".zip"
	sep = "\t"
	summaryFile = outputDir + "/summary.tsv"

	# collate summaries in one overview file:
	print "Collecting summary statistics into: " + summaryFile
	with open(summaryFile, "w") as fout:
		for fastqcZip in glob.glob(outputDir + "/*"+zipSuffix):
			curName = fastqcZip[len(outputDir+"/"):-len(zipSuffix)]
			curMap = {}
			#print curName
			with zipfile.ZipFile(fastqcZip) as z:
				with z.open(curName+"/summary.txt") as f:
					for line in f:
						tokens = line.split(sep)
						curMap[tokens[1]] = tokens[0]
						allKeys[tokens[1]] = True
			resultsMap[curName] = curMap
			
		fout.write("Dataset" + sep + sep.join(allKeys.keys())+"\n")
		for sample, curMap in resultsMap.items():
			fout.write(sample)
			for k in allKeys:
				fout.write(sep + curMap[k])
			fout.write("\n")

