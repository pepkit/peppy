#! /usr/bin/env python

# This script loops through all the samples,
# creates trackhubs for them.
import csv
import os
import subprocess
import ConfigParser
from argparse import ArgumentParser
import cgi
import datetime
import getpass
import inspect
import urllib
from pypiper import AttributeDict
import yaml


# Argument Parsing
# #######################################################################################
parser = ArgumentParser(description='make_trackhubs')

parser.add_argument('-c', '--config-file', dest='config_file', help="path to YAML config file", required=True, type=str)
parser.add_argument('-f', dest='filter', action='store_false', required=False, default=True)
parser.add_argument('-v', '--visibility', dest='visibility', help='visibility mode (default: full)', required=False, default='full', type=str)
parser.add_argument('--copy', dest='copy', help='copy all files instead of creating symbolic links', required=False, default=False)

args = parser.parse_args()
#print '\nArguments:'
#print args

with open(args.config_file, 'r') as config_file:
	config_yaml = yaml.load(config_file)
	config = AttributeDict(config_yaml, default=True)

#print '\nYAML configuration:'
#print config

trackhubs = config.trackhubs
paths = config.paths

if not os.path.exists(paths.output_dir):
	raise Exception(paths.output_dir + " : that project directory does not exist!")

present_genomes = {}
subGroups_perGenome = {}
subGroups = {"exp_category":{},"FACS_marker":{},"cell_type":{},"treatment":{},"treatment_length":{},"cell_count":{},"library":{},"data_type":{}}
# add x- and y-dimension to subGroups even if they are not in the standard column selection:
subGroups[trackhubs.matrix_x] = {}
subGroups[trackhubs.matrix_y] = {}


csv_file_path = os.path.join(os.path.dirname(args.config_file),config.metadata.sample_annotation)
print "\nOpening CSV file: "+csv_file_path
if os.path.isfile(csv_file_path):
	csv_file = open(os.path.join(os.path.dirname(args.config_file),config.metadata.sample_annotation), 'rb')  # opens the csv file
else:
	raise Exception(csv_file_path + " : that file does not exist!")

try:

	csv_file_0 = open(os.path.join(os.path.dirname(args.config_file),config.metadata.sample_annotation), 'rb')
	input_file_0 = csv.DictReader(csv_file_0)  # creates the reader object

	pipeline = ""
	genome = ""
	for row in input_file_0:
		if ("library" in row.keys()): pipeline = str(row["library"])
		if ("organism" in row.keys()): genome = str(getattr(config.genomes,str(row["organism"])))
	print 'Pipeline: ' + pipeline
	print 'Genome: ' + genome
	if pipeline != "": pipeline += '_'

	paths.write_dir = ""

	if args.copy:
		paths.write_dir = trackhubs.trackhub_dir
		if not os.path.exists(paths.write_dir):
			os.makedirs(paths.write_dir)
	else:
		paths.write_dir = paths.output_dir
		if not os.path.islink(trackhubs.trackhub_dir):
			os.symlink(os.path.relpath(paths.write_dir, os.path.dirname(trackhubs.trackhub_dir)),trackhubs.trackhub_dir)
			print 'Linking to: ' + str(trackhubs.trackhub_dir)
		else:
			print 'Link already exists: ' + str(trackhubs.trackhub_dir)
	print 'Writing files to: ' + paths.write_dir


	genomes_file = open(os.path.join(paths.write_dir, pipeline+'genomes.txt'), 'w')

	track_out = os.path.join(paths.write_dir, genome)
	if not os.path.exists(track_out):
		os.makedirs(track_out)
		print 'Writing tracks to: ' + track_out
	else:
		print 'Trackhubs already exists! Overwriting everything in ' + track_out
		for root, dirs, files in os.walk(track_out, topdown=False):
			for name in files:
				os.remove(os.path.join(root, name))
			for name in dirs:
				os.rmdir(os.path.join(root, name))

	# write hub.txt
	hub_file_name = pipeline+"hub.txt"
	hub_file = open(os.path.join(paths.write_dir, hub_file_name), 'w')
	hub_file.writelines("hub " + trackhubs.hub_name + "\n")
	hub_file.writelines("shortLabel " + trackhubs.hub_name + "\n")
	hub_file.writelines("longLabel " + trackhubs.hub_name + "\n")
	hub_file.writelines("genomesFile " + pipeline + "genomes.txt\n")
	hub_file.writelines("email " + trackhubs.email + "\n")

        # Write a HTML document.
        html_out = str()
        html_out_tab1 = str()
        html_out_tab2 = str()
	# Write HTML header and title
        html_out += '<!DOCTYPE html PUBLIC ' \
                  '"-//W3C//DTD XHTML 1.0 Transitional//EN" ' \
                  '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n'
        html_out += '\n'
        html_out += '<html xmlns="http://www.w3.org/1999/xhtml">\n'
        html_out += '<head>\n'
        html_out += '<meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1" />\n'
        html_out += '<link rel="schema.DC" href="http://purl.org/DC/elements/1.0/" />\n'
        html_out += '<meta name="DC.Creator" content="{}" />\n'.format(getpass.getuser())
        html_out += '<meta name="DC.Date" content="{}" />\n'.format(datetime.datetime.now().isoformat())
        #html_out += '<meta name="DC.Source" content="{}" />\n'.format(inspect.currentframe())
        html_out += '<meta name="DC.Title" content="{}" />\n'.format(os.path.basename(paths.output_dir))
        html_out += '<title>{}</title>\n'.format(os.path.basename(paths.output_dir))
        html_out += '</head>\n'
        html_out += '\n'

	tableDict = dict()


	input_file = csv.DictReader(csv_file)
	sample_count = 0

	print '\nStart iterating over samples'
	for row in input_file:  # iterates the rows of the file in orders

		sample_count += 1

		sample_name = row["sample_name"]
		print '\nProcessing sample #'+ str(sample_count) + " : " + sample_name

		tableDict[sample_name] = dict()

		if 'run' in row:
			if not row["run"] == "1":
				print(sample_name + ": not selected")
				continue
			else:
				print(sample_name + ": SELECTED")

		sample_path = os.path.join(paths.output_dir, paths.results_subdir, sample_name)

		present_subGroups = "\tsubGroups "

		# bsmap aligned bam files
		bsmap_mapped_bam = os.path.join(sample_path, "bsmap_" + genome, sample_name + ".bam")
		bsmap_mapped_bam_name = os.path.basename(bsmap_mapped_bam)
		bsmap_mapped_bam_index = os.path.join(sample_path, "bsmap_" + genome, sample_name + ".bam.bai")
		bsmap_mapped_bam_index_name = os.path.basename(bsmap_mapped_bam_index)

		# With the new meth bigbeds, RRBS pipeline should yield this file:
		meth_bb_file = os.path.join(sample_path, "bigbed_" + genome, "RRBS_" + sample_name + ".bb")
		meth_bb_name = os.path.basename(meth_bb_file)

		# bismark bigwig files
		bismark_bw_file = os.path.join(sample_path, "bismark_" + genome, "extractor", sample_name + ".aln.dedup.filt.bw")
		bismark_bw_name = os.path.basename(bismark_bw_file)

		#bigwigs are better actually
		if not os.path.isfile(bismark_bw_file):
			bismark_bw_file = os.path.join(sample_path, "bigwig_" + genome, "RRBS_" + sample_name + ".bw")
			bismark_bw_name = os.path.basename(bismark_bw_file)

		# biseqMethcalling bed file
		biseq_bed = os.path.join(sample_path, "biseq_" + genome, "RRBS_cpgMethylation_" + sample_name + ".bed")
		biseq_bed_name = os.path.basename(biseq_bed)

		# tophat files
		if args.filter:
			tophat_bw_file = os.path.join(sample_path, "tophat_" + genome, sample_name + ".aln.filt_sorted.bw")
		else:
			tophat_bw_file = os.path.join(sample_path, "tophat_" + genome, sample_name + ".aln_sorted.bw")
		tophat_bw_name = os.path.basename(tophat_bw_file)


		if os.path.isfile(tophat_bw_file) or os.path.isfile(bismark_bw_file)  or os.path.isfile(meth_bb_file):

			track_out_file = os.path.join(track_out, pipeline+"trackDB.txt")
			if not track_out_file in present_genomes.keys():
				#initialize a new genome
				open(track_out_file, 'w').close()
				genomes_file.writelines("genome "+ genome.split('_')[0] + "\n")
				genomes_file.writelines("trackDb " + os.path.join(genome, os.path.basename(track_out_file)) + "\n")
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
		if trackhubs.short_label_column is not None:
			shortLabel = row[trackhubs.short_label_column]
		else:
			shortLabel = "sl_"
			if ("Library" in row.keys()):
				shortLabel += row["library"][0]
			if ("cell_type" in row.keys()):
				shortLabel += "_" + row["cell_type"]
			if ("cell_count" in row.keys()):
				shortLabel += "_" + row["cell_count"]


		##########################################
		### Aligned BAM files and index files
		##########################################

		if os.path.isfile(bsmap_mapped_bam):

			print "  FOUND bsmap mapped file: " + bsmap_mapped_bam

			# copy or link the file to the hub directory
			if args.copy:
				cmd = "cp " + bsmap_mapped_bam + " " + track_out
				print(cmd)
 				subprocess.call(cmd, shell=True)
				cmd = "cp " + bsmap_mapped_bam_index + " " + track_out
				print(cmd)
 				subprocess.call(cmd, shell=True)
			else:
				os.symlink(os.path.relpath(bsmap_mapped_bam,track_out), os.path.join(track_out,pipeline+bsmap_mapped_bam_name))
				os.symlink(os.path.relpath(bsmap_mapped_bam_index,track_out), os.path.join(track_out,pipeline+bsmap_mapped_bam_index_name))

			# construct track for data file
			track_text = "\n\ttrack " + bsmap_mapped_bam_name + "_Meth_Align" + "\n"
			track_text += "\tparent DNA_Meth_Align on\n"
			track_text += "\ttype bam\n"
			track_text += present_subGroups + "data_type=Meth_Align" + "\n"
			track_text += "\tshortLabel " + shortLabel + "\n"
			track_text += "\tlongLabel " + sample_name + "_Meth_Align" + "\n"
			track_text += "\tbigDataUrl " + pipeline+bsmap_mapped_bam_name + "\n"

			tableDict[sample_name]['BAM'] = dict([('label','BAM'),('link',os.path.relpath(os.path.join(track_out,pipeline+bsmap_mapped_bam_name),track_out))])
			tableDict[sample_name]['BAI'] = dict([('label','BAI'),('link',os.path.relpath(os.path.join(track_out,pipeline+bsmap_mapped_bam_index_name),track_out))])

			present_genomes[track_out_file].append(track_text)
		else:
			print ("  No bsmap mapped bam found: " + bsmap_mapped_bam_name)


		##########################################
		### For BigBed files
		##########################################

		if os.path.isfile(meth_bb_file):

			print "  FOUND BigBed file: " + meth_bb_file

			# copy or link the file to the hub directory
			if args.copy:
				cmd = "cp " + meth_bb_file + " " + track_out
				print(cmd)
 				subprocess.call(cmd, shell=True)
			else:
				os.symlink(os.path.relpath(meth_bb_file,track_out), os.path.join(track_out,meth_bb_name))

			# construct track for data file
			track_text = "\n\ttrack " + meth_bb_name + "_Meth_BB" + "\n"
			track_text += "\tparent DNA_Meth_BB on\n"
			track_text += "\ttype bigBed\n"
			track_text += present_subGroups + "data_type=Meth_BB" + "\n"
			track_text += "\tshortLabel " + shortLabel + "\n"
			track_text += "\tlongLabel " + sample_name + "_Meth_BB" + "\n"
			track_text += "\tbigDataUrl " + pipeline+meth_bb_name + "\n"

			tableDict[sample_name]['BB'] = dict([('label','BB'),('link',os.path.relpath(os.path.relpath(os.path.join(track_out,meth_bb_name),track_out)))])

			present_genomes[track_out_file].append(track_text)
		else:
			print ("  No Bigbed file found: " + meth_bb_file)


		##########################################
		### For Methylation (bismark) BIGWIG files
		##########################################

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
			track_text += "\tparent " + trackhubs.parent_track_name + " on\n"
			track_text += "\ttype bigWig\n"
			track_text += present_subGroups + "data_type=Meth" + "\n"
			track_text += "\tshortLabel " + shortLabel + "\n"
			track_text += "\tlongLabel " + sample_name + "_Meth" + "\n"
			track_text += "\tbigDataUrl " + bismark_bw_name + "\n"
			track_text += "\tviewLimits 0:100" + "\n"
			track_text += "\tviewLimitsMax 0:100" + "\n"
			track_text += "\tmaxHeightPixels 100:30:10" + "\n"

			tableDict[sample_name]['BW'] = dict([('label','BW'),('link',os.path.relpath(os.path.relpath(os.path.join(track_out,bismark_bw_name),track_out)))])

			present_genomes[track_out_file].append(track_text)
		else:
			print ("  No bismark bw found: " + bismark_bw_file)



		##########################################
		### For biseq BED files
		##########################################

		if os.path.isfile(biseq_bed):

			print "  FOUND biseq bed file: " + biseq_bed

			# copy or link the file to the hub directory
			if args.copy:
				cmd = "cp " + biseq_bed + " " + track_out
				print(cmd)
 				subprocess.call(cmd, shell=True)
			else:
				os.symlink(os.path.relpath(biseq_bed,track_out), os.path.join(track_out,biseq_bed_name))

			tableDict[sample_name]['BED'] = dict([('label','BED'),('link',os.path.relpath(os.path.join(track_out,biseq_bed_name),track_out))])

		else:
			print ("  No biseq bed file found: " + biseq_bed)



		##########################################
		### For RNA (tophat) files
		##########################################

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
			track_text += "\tparent " + trackhubs.parent_track_name + " on\n"
			track_text += "\ttype bigWig\n"
			track_text += present_subGroups + "data_type=RNA" + "\n"
			track_text += "\tshortLabel " + shortLabel + "\n"
			track_text += "\tlongLabel " + sample_name +  "_RNA" + "\n"
			track_text += "\tbigDataUrl " + tophat_bw_name + "\n"
			track_text += "\tautoScale on" + "\n"

			tableDict[sample_name]['TH'] = dict([('label','BW'),('link',os.path.relpath(os.path.join(track_out,tophat_bw_name),track_out))])

			present_genomes[track_out_file].append(track_text)
		else:
			print ("  No tophat bw found: " + tophat_bw_file)


	#write composit-header followed by the individual tracks to a genome specific trackDB.txt
	composit_text = ""
	for key in present_genomes.keys():
		#construct composite header
		composit_text += "\ntrack " + str(trackhubs.parent_track_name) + "\n"
		composit_text += "compositeTrack on"
		count = 0
		dim_text = "dimensions dimX="+ str(trackhubs.matrix_x) + " dimY=" + str(trackhubs.matrix_y)
		for subGroup in subGroups_perGenome[key].keys():
			if len(subGroups_perGenome[key][subGroup])<1:
				continue
			if not subGroup == str(trackhubs.matrix_x) and not subGroup == str(trackhubs.matrix_y):
				dim_text += " dimA=" + subGroup
			count += 1
			composit_text += "\nsubGroup" + str(count) + " " + subGroup + " " + subGroup + " "
			for type in subGroups_perGenome[key][subGroup].keys():
				composit_text += type + "=" + subGroups_perGenome[key][subGroup][type] + " "
		composit_text += "\nshortLabel " + str(trackhubs.parent_track_name) + "\n"
		composit_text += "longLabel " + str(trackhubs.parent_track_name) + "\n"
		composit_text += "type bigWig" + "\n"
		composit_text += "color 0,60,120" + "\n"
		composit_text += "spectrum on" + "\n"
		composit_text += "visibility " + args.visibility + "\n"
		composit_text += dim_text + "\n"
		composit_text += "sortOrder " + str(trackhubs.sortOrder) + "\n"

		#write composite header
		trackDB = open(key, 'a')
		trackDB.writelines(composit_text)
		#write individual tracks
		for i in range(len(present_genomes[key])):
			trackDB.writelines(present_genomes[key][i])
		super_text = "\n"		
		super_text += "track DNA_Meth_Align\n"
		super_text += "shortLabel DNA_Meth_Align\n"
		super_text += "longLabel DNA_Meth_Align\n"
		super_text += "superTrack on\n"
		super_text += "\n"		
		super_text += "track DNA_Meth_BB\n"
		super_text += "shortLabel DNA_Meth_BB\n"
		super_text += "longLabel DNA_Meth_BB\n"
		super_text += "superTrack on\n"

		trackDB.writelines(super_text)
		trackDB.close()


	report_name = pipeline+'report.html'

        html_out += '<body>\n'
        html_out += '<h1>{} Project</h1>\n'.format(os.path.basename(paths.output_dir))
        html_out += '\n'
	html_out += '<p><br /></p>\n'

	html_out += '<h2>Useful Links</h2>\n'
	tsv_stats_name = os.path.basename(paths.output_dir)+'_stats_summary.tsv'
	tsv_stats_path = os.path.relpath(os.path.join(paths.output_dir,tsv_stats_name),track_out)
	xls_stats_name = os.path.basename(paths.output_dir)+'_stats_summary.xlsx'
	xls_stats_path = os.path.relpath(os.path.join(paths.output_dir,xls_stats_name),track_out)
	if os.path.isfile(os.path.join(paths.output_dir,tsv_stats_name)):
		if os.path.isfile(os.path.join(paths.output_dir,xls_stats_name)):
			html_out += '<p>Stats summary table: <a href="{}">{}</a> <a href="{}">{}</a></p>\n'.format(tsv_stats_path,'TSV',xls_stats_path,'XLSX')
		else:
        		html_out += '<p>Stats summary table: <a href="{}">{}</a></p>\n'.format(tsv_stats_path,'TSV')
	url = str(trackhubs.url).replace(':','%3A').replace('/','%2F')
	paths.ucsc_browser_link = 'http://genome-euro.ucsc.edu/cgi-bin/hgTracks?db='+genome.split('_')[0]+'&amp;hubUrl='+url+'%2F'+hub_file_name
        html_out += '<p>UCSC Genome Browser: <a href="{}">{}</a></p>\n'.format(paths.ucsc_browser_link,'Link')

        html_file_name = os.path.join(track_out, report_name)
        file_handle = open(name=html_file_name, mode='w')
        file_handle.write(html_out)


        html_out_tab = '<h2>Data Files</h2>\n'
        html_out_tab += '<table cellpadding="5">\n'
        html_out_tab += '<tr>\n'
        html_out_tab += '<th>Sample Name</th>\n'
        html_out_tab += '<th>Aligned BAM</th>\n'
        html_out_tab += '<th>BAM Index</th>\n'
        html_out_tab += '<th>BigBed</th>\n'
        html_out_tab += '<th>BigWig</th>\n'
        html_out_tab += '<th>Biseq Bed</th>\n'
        html_out_tab += '</tr>\n'
	for key,value in tableDict.items():
		      	html_out_tab += '<tr>\n'
        		html_out_tab += '<td>{}</td>\n'.format(key)
        		html_out_tab += '<td><a href="{}">{}</a></td>\n'.format(value['BAM']['link'],value['BAM']['label'])
        		html_out_tab += '<td><a href="{}">{}</a></td>\n'.format(value['BAI']['link'],value['BAI']['label'])
        		html_out_tab += '<td><a href="{}">{}</a></td>\n'.format(value['BB']['link'],value['BB']['label'])
        		html_out_tab += '<td><a href="{}">{}</a></td>\n'.format(value['BW']['link'],value['BW']['label'])
        		html_out_tab += '<td><a href="{}">{}</a></td>\n'.format(value['BED']['link'],value['BED']['label'])
			html_out_tab += '</tr>\n'
        html_out_tab += '</table>\n'
        file_handle.write(html_out_tab)


	html_out = '<p><br /></p>\n'
	html_out += '<p>This report was generated with software of the Biomedical Sequencing Facility: <a href="http://www.biomedical-sequencing.at">www.biomedical-sequencing.at</a></p>\n'
	html_out += '<p>Contact: <a href="mailto:bsf@cemm.oeaw.ac.at">bsf@cemm.oeaw.ac.at</a></p>\n'
	html_out += '<p><br /></p>\n'
	html_out += '</body>\n'
	html_out += '</html>\n'
	html_out += '\n'
        file_handle.write(html_out)
        file_handle.close()

	cmd = "chmod -R go+rX " + paths.output_dir
	subprocess.call(cmd, shell=True)

	hub_file_link = str(trackhubs.url) + "/" + hub_file_name
	report_link = str(trackhubs.url) + "/" + genome + "/" + report_name
	link_string = 'Hub ' + hub_file_link + '\n'
	link_string += 'Report ' + report_link + '\n'
	link_string += 'UCSCbrowser ' + paths.ucsc_browser_link + '\n'
	print '\nDONE!'
	print link_string

        link_file = open(name=os.path.join(paths.write_dir, pipeline+'links.txt'), mode='w')
        link_file.write(link_string)
        link_file.close()

finally:
	csv_file.close()


