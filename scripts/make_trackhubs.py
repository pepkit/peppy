#! /usr/bin/env python

# This script loops through all the samples,
# creates trackhubs for them.
import csv
import os
import subprocess
import ConfigParser
from argparse import ArgumentParser
# Argument Parsing
# #######################################################################################
parser = ArgumentParser(description='make_trackhubs')

parser.add_argument('-c', '--config-file', dest='conf_file', help="Supply config file [-c]", required=True, type=str)
parser.add_argument('-f', dest='filter', action='store_false', required=False, default=True)
parser.add_argument('-v', '--visibility', dest='visibility', help='visibility mode (default: full)', required=False, default='full', type=str)
parser.add_argument('--copy', dest='copy', help='copy files instead of creating symbolic links', required=False, default=False)

args = parser.parse_args()

if not args.conf_file:
	parser.print_help() #or, print_usage() for less verbosity
	raise SystemExit

#get configurations
config = ConfigParser.ConfigParser({
	"results": "$ROOT/results_pipeline/",
	"email": "jklughammer@cemm.oeaw.ac.at",
	"short_label_column": None
})
config.readfp(open(args.conf_file))

#organism-genome translation
genomes = {"human": ["hg19", "hg19_cdna"], "mouse": ["mm10", "m38_cdna"]}

# Pick the genome matching the organism from the sample annotation sheet.
# If no mapping exists in  the organism-genome translation dictionary, then
# we assume the given organism name directly corresponds to the name of a
# reference genome. This enables the use of additional genomes without any
# need to modify the code.
# (REPLICATED FROM project_sample_loop.py -- TODO resolve rundandancy)

def get_genome(organism,dna=True):
	if organism in genomes.keys():
		if dna:
			return genomes[organism][0]
		else:
			return genomes[organism][1]
	else:
		return organism

# Create an empty object to hold paths
class Container:
	pass
paths = Container()

paths.project_root = config.get("paths","project_root")
paths.psa = config.get("paths","psa")
paths.track_dir = config.get("paths","track_dir")
paths.results = config.get("paths","results")


# Include the path to the config file
paths.config = os.path.dirname(os.path.realpath(args.conf_file))

#track configurations
matrix_x = config.get("track configurations","matrix_x")
matrix_y = config.get("track configurations","matrix_y")
sortOrder = config.get("track configurations","sortOrder")
parent_track_name = config.get("track configurations","parent_track_name")
hub_name = config.get("track configurations","hub_name")
short_label_column = config.get("track configurations", "short_label_column")
email = config.get("track configurations", "email")

if not os.path.exists(paths.project_root):
	raise Exception(paths.project_root + " : that project does not exist!")

# This loop checks for absolute paths; if a path is relative, it
# converts it to an absolute path *relative to the config file*.
# It also converts $ROOT into the project root, for relative paths.
print("Paths:")
pathsDict = paths.__dict__
for attribute in pathsDict:
	print(attribute.rjust(20) + ":\t" + str(getattr(paths,attribute)))
	if not os.path.isabs(getattr(paths,attribute)):
		newPath = getattr(paths,attribute).replace("$ROOT", paths.project_root)
		setattr(paths,attribute, os.path.join(paths.config, newPath))
		print("->".rjust(20) + "\t" + getattr(paths,attribute))


f = open(paths.psa, 'rb')  # opens the csv file
present_genomes = {}
subGroups_perGenome = {}
subGroups = {"exp_category":{},"FACS_marker":{},"cell_type":{},"treatment":{},"treatment_length":{},"cell_count":{},"library":{},"data_type":{}}

# add x- and y-dimension to subGroups even if they are not in the standard column selection:
subGroups[matrix_x] = {}
subGroups[matrix_y] = {}


try:
	input_file = csv.DictReader(f)  # creates the reader object

	paths.write_dir = ""

	if args.copy:
		paths.write_dir = paths.track_dir
		if not os.path.exists(paths.write_dir):
			os.makedirs(paths.write_dir)
	else:
		paths.write_dir = paths.project_root
		os.symlink(os.path.relpath(paths.write_dir, os.path.dirname(paths.track_dir)),paths.track_dir)

	genomes_file = open(os.path.join(paths.write_dir, "genomes.txt"), 'w')
	# write hub.txt
	hub_file = open(os.path.join(paths.write_dir, "hub.txt"), 'w')
	hub_file.writelines("hub " + hub_name + "\n")
	hub_file.writelines("shortLabel " + hub_name + "\n")
	hub_file.writelines("longLabel " + hub_name + "\n")
	hub_file.writelines("genomesFile genomes.txt\n")
	hub_file.writelines("email " + email + "\n")


	for row in input_file:  # iterates the rows of the file in orders
		# if 'run' column is absent, assume we should run them all.
		if 'run' in row:
			if not row["run"] == "1":
				print(row["sample_name"] + ": not selected")
				continue
			else:
				print(row["sample_name"] + ": SELECTED")
		else:
			print(row["sample_name"] + ":")


		present_subGroups = "\tsubGroups "
		genome = get_genome(row["organism"])
		if args.filter:
			tophat_bw_file = os.path.join(paths.results, row["sample_name"], "tophat_" + genome, row["sample_name"] + ".aln.filt_sorted.bw")
		else:
			tophat_bw_file = os.path.join(paths.results, row["sample_name"], "tophat_" + genome, row["sample_name"] + ".aln_sorted.bw")


		bismark_bw_file = os.path.join(paths.results, row["sample_name"], "bismark_" + genome, "extractor", row["sample_name"] + ".aln.dedup.filt.bw")
		tophat_bw_name = os.path.basename(tophat_bw_file)
		bismark_bw_name = os.path.basename(bismark_bw_file)

		bsmap_mapped_bam = os.path.join(paths.results, row["sample_name"], "bsmap_" + genome, row["sample_name"] + ".bam")
		bsmap_mapped_bam_name = os.path.basename(bsmap_mapped_bam)

		# With the new meth bigbeds, RRBS pipeline should yield this file:
		meth_bb_file = os.path.join(paths.results, row["sample_name"], "bigbed_" + genome, "RRBS_" + row["sample_name"] + ".bb")
		meth_bb_name = os.path.basename(meth_bb_file)

		#bigwigs are better actually
		if not os.path.isfile(bismark_bw_file):
			bismark_bw_file = os.path.join(paths.results, row["sample_name"], "bigwig_" + genome, "RRBS_" + row["sample_name"] + ".bw")
			bismark_bw_name = os.path.basename(bismark_bw_file)

		if os.path.isfile(tophat_bw_file) or os.path.isfile(bismark_bw_file)  or os.path.isfile(meth_bb_file):
			track_out = os.path.join(paths.write_dir, genome)
			track_out_file = os.path.join(track_out, "trackDB.txt")
			if not track_out_file in present_genomes.keys():
				#initialize a new genome
				if not os.path.exists(track_out):
					os.makedirs(track_out)
				open(os.path.join(track_out, "trackDB.txt"), 'w').close()
				genomes_file.writelines("genome" + " " + genome + "\n")
				genomes_file.writelines("trackDb" + " " + genome + "/trackDB.txt" + "\n")
				present_genomes[track_out_file] = []
				subGroups_perGenome[track_out_file] = subGroups

			#construct subGroups for each sample and initialize subgroups if not present
			for key in subGroups_perGenome[track_out_file].keys():
				if not key in input_file.fieldnames:
					continue
				if not row[key] in ["NA",""," "]:
					present_subGroups += key + "=" + row[key] + " "
					if not row[key] in subGroups_perGenome[track_out_file][key]:
						subGroups_perGenome[track_out_file][key][row[key]] = row[key]


		# TODO NS: we should only have build these once; like so:
		# Build short label
		if short_label_column is not None:
			shortLabel = row[short_label_column]
		else:
			shortLabel = "sl_"
			if ("Library" in row.keys()):
				shortLabel += row["library"][0]
			if ("cell_type" in row.keys()):
				shortLabel += "_" + row["cell_type"]
			if ("cell_count" in row.keys()):
				shortLabel += "_" + row["cell_count"]


		#For RNA (tophat) files
		if os.path.isfile(tophat_bw_file):
			print "  FOUND tophat bw: " + tophat_bw_file
			# copy or link the file to the hub directory
			if args.copy:
				cmd = "cp " + tophat_bw_file + " " + track_out + "\n"
				cmd += "chmod o+r " + os.path.join(track_out, tophat_bw_name)
				print(cmd)
				subprocess.call(cmd, shell=True)
			else:
				os.symlink(os.path.relpath(tophat_bw_file,track_out), os.path.join(track_out,tophat_bw_name))
			#add data_type subgroup (not included in sampleAnnotation)
			if not "RNA" in subGroups_perGenome[track_out_file]["data_type"]:
						subGroups_perGenome[track_out_file]["data_type"]["RNA"] = "RNA"
			#costruct track for data file
			track_text = "\n\ttrack " + tophat_bw_name + "_RNA" + "\n"
			track_text += "\tparent " + parent_track_name + " on\n"
			track_text += "\ttype bigWig\n"
			track_text += present_subGroups + "data_type=RNA" + "\n"
			track_text += "\tshortLabel " + shortLabel + "\n"
			track_text += "\tlongLabel " + row["sample_name"] +  "_RNA" + "\n"
			track_text += "\tbigDataUrl " + tophat_bw_name + "\n"
			track_text += "\tautoScale on" + "\n"

			present_genomes[track_out_file].append(track_text)
		else:
			print ("  No tophat bw found: " + tophat_bw_file)

		# For Methylation (bismark) files
		if os.path.isfile(bismark_bw_file):
			print "  FOUND bismark bw: " + bismark_bw_file
			# copy or link the file to the hub directory
			if args.copy:
				cmd = "cp " + bismark_bw_file + " " + track_out
				print(cmd)
 				subprocess.call(cmd, shell=True)
			else:
				os.symlink(os.path.relpath(bismark_bw_file,track_out), os.path.join(track_out,bismark_bw_name))
			#add data_type subgroup (not included in sampleAnnotation)
			if not "Meth" in subGroups_perGenome[track_out_file]["data_type"]:
						subGroups_perGenome[track_out_file]["data_type"]["Meth"] = "Meth"
			#costruct track for data file
			track_text = "\n\ttrack " + bismark_bw_name + "_Meth" + "\n"
			track_text += "\tparent " + parent_track_name + " on\n"
			track_text += "\ttype bigWig\n"
			track_text += present_subGroups + "data_type=Meth" + "\n"
			track_text += "\tshortLabel " + shortLabel + "\n"
			track_text += "\tlongLabel " + row["sample_name"] + "_Meth" + "\n"
			track_text += "\tbigDataUrl " + bismark_bw_name + "\n"
			track_text += "\tviewLimits 0:100" + "\n"
			track_text += "\tviewLimitsMax 0:100" + "\n"
			track_text += "\tmaxHeightPixels 100:30:10" + "\n"

			present_genomes[track_out_file].append(track_text)
		else:
			print ("  No bismark bw found: " + bismark_bw_file)


		if os.path.isfile(bsmap_mapped_bam):
			print "  FOUND bsmap mapped file: " + bsmap_mapped_bam
			# copy or link the file to the hub directory
			if args.copy:
				cmd = "cp " + bsmap_mapped_bam + " " + track_out
				print(cmd)
 				subprocess.call(cmd, shell=True)
			else:
				os.symlink(os.path.relpath(bsmap_mapped_bam,track_out), os.path.join(track_out,bsmap_mapped_bam_name))
			#add data_type subgroup (not included in sampleAnnotation)
			#if not "MethAlign" in subGroups_perGenome[track_out_file]["data_type"]:
			#			subGroups_perGenome[track_out_file]["data_type"]["MethAlign"] = "MethAlign"
			#costruct track for data file
			track_text = "\n\ttrack " + bsmap_mapped_bam_name + "_Meth_Align" + "\n"
			track_text += "\tparent DNA_Meth_Align on\n"
			track_text += "\ttype bam\n"
			track_text += present_subGroups + "data_type=Meth_Align" + "\n"
			track_text += "\tshortLabel " + shortLabel + "\n"
			track_text += "\tlongLabel " + row["sample_name"] + "_Meth_Align" + "\n"
			track_text += "\tbigDataUrl " + bsmap_mapped_bam_name + "\n"

			present_genomes[track_out_file].append(track_text)
		else:
			print ("  No bsmap mapped bam found: " + bsmap_mapped_bam_name)


	#write composit-header followed by the individual tracks to a genome specific trackDB.txt
	composit_text = ""
	for key in present_genomes.keys():
		#construct composite header
		composit_text += "\ntrack " + parent_track_name + "\n"
		composit_text += "compositeTrack on"
		count = 0
		dim_text = "dimensions dimX="+ matrix_x + " dimY=" + matrix_y
		for subGroup in subGroups_perGenome[key].keys():
			if len(subGroups_perGenome[key][subGroup])<1:
				continue
			if not subGroup == matrix_x and not subGroup == matrix_y:
				dim_text += " dimA=" + subGroup
			count += 1
			composit_text += "\nsubGroup" + str(count) + " " + subGroup + " " + subGroup + " "
			for type in subGroups_perGenome[key][subGroup].keys():
				composit_text += type + "=" + subGroups_perGenome[key][subGroup][type] + " "
		composit_text += "\nshortLabel " + parent_track_name + "\n"
		composit_text += "longLabel " + parent_track_name + "\n"
		composit_text += "type bigWig" + "\n"
		composit_text += "color 0,60,120" + "\n"
		composit_text += "spectrum on" + "\n"
		composit_text += "visibility " + args.visibility + "\n"
		composit_text += dim_text + "\n"
		composit_text += "sortOrder " + sortOrder + "\n"

		#write composite header
		trackDB = open(key, 'a')
		trackDB.writelines(composit_text)
		#write individual tracks
		for i in range(len(present_genomes[key])):
			trackDB.writelines(present_genomes[key][i])
		super_text = "\n"		
		super_text += "track DNA_Meth_Align\n"
		super_text += "shortLabel track DNA_Meth_Align\n"
		super_text += "longLabel track DNA_Meth_Align\n"
		super_text += "superTrack on\n"
		trackDB.writelines(super_text)
		trackDB.close()

finally:
	f.close()

