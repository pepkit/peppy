#! /usr/bin/env python

# This script loops through all the samples,
# creates a summary stats table
import csv
import os
from argparse import ArgumentParser
from pypiper import AttributeDict
import yaml


# Argument Parsing
# #######################################################################################
parser = ArgumentParser(description='make_trackhubs')
parser.add_argument('-c', '--config-file', dest='config_file', help="path to YAML config file", required=True, type=str)
args = parser.parse_args()
#print '\nArguments:'
#print args

with open(args.config_file, 'r') as config_file:
	config_yaml = yaml.load(config_file)
	config = AttributeDict(config_yaml, default=True)
#print '\nYAML configuration:'
#print config
paths = config.paths

if not os.path.exists(paths.output_dir):
	raise Exception(paths.output_dir + " : that project directory does not exist!")


# Open samples CSV file
# #######################################################################################
csv_file_path = os.path.join(os.path.dirname(args.config_file),config.metadata.sample_annotation)
#print "\nOpening CSV file: " + csv_file_path
if os.path.isfile(csv_file_path):
	csv_file = open(os.path.join(os.path.dirname(args.config_file),config.metadata.sample_annotation), 'rb')
	print 'Found ' + csv_file_path
else:
	raise Exception(csv_file_path + " : that file does not exist!")
csv_reader = csv.DictReader(csv_file)


# Output TSV file
# #######################################################################################
tsv_outfile_path = os.path.join(paths.output_dir,os.path.basename(paths.output_dir)+'_stats_summary.tsv')
tsv_outfile = open(tsv_outfile_path, 'w')
fields_in = ['sample_name','instrument_model','flowcell','lane','read_length','single_or_paired','organism','Genome'\
,'cell_type','Raw_reads','Fastq_reads','PF_reads','Trimmed_reads','Trimmed_rate','Aligned_reads','Aligned_rate'\
,'Multimap_reads','Multimap_rate','Unique_CpGs','Total_CpGs','meanCoverage',\
'bisulfiteConversionRate','globalMethylationMean',\
'K1_unmethylated_count','K1_unmethylated_meth','K3_methylated_count','K3_methylated_meth']
fields_out = ['Sample','Instrument','Flowcell','Lane','Read Length','Read Type','Organism','Genome'\
,'Cell Type','Raw Reads','Fastq Reads','PF Reads','Trimmed Reads','Trimmed Rate (%)','Aligned Reads','Aligned Rate (%)'\
,'Multimap Reads','Multimap Rate (%)','Unique CpGs','Total CpGs','Mean Coverage',\
'Bisulfite Conversion Rate (%)',' Global Methylation Mean',\
'K1 Unmethylated Count','K1 Unmethylated Meth','K3 Methylated Count','K3 Methylated Meth']
tsv_writer = csv.DictWriter(tsv_outfile, fieldnames=fields_out, delimiter='\t')
tsv_writer.writeheader()


# Looping over all samples
# #######################################################################################
sample_count = 0
print '\nStart iterating over samples'
for row in csv_reader:

	sample_count += 1
	sample_name = row['sample_name']
	print '\nProcessing sample #'+ str(sample_count) + " : " + sample_name

	# Open sample TSV stat file
	stat_file_path = os.path.join(paths.output_dir,paths.results_subdir,sample_name,row['library']+'_stats.tsv')
	if os.path.isfile(csv_file_path):
		stat_file = open(stat_file_path, 'rb')
		print 'Found: ' + stat_file_path
	else:
		raise Exception(stat_file_path + " : file does not exist!")
	stats_dict = dict()
	for line in stat_file:
		key, value  = line.split('\t')
		stats_dict[key] = value.strip()


	new_row = dict()

	for i in range(0,len(fields_in)):
		field = fields_in[i]
		field_out = fields_out[i]
		if field == 'Trimmed_rate':
			new_row[field_out] = str(100.0*float(stats_dict['Trimmed_reads'])/float(stats_dict['Raw_reads']))
		elif field == 'Aligned_rate':
			new_row[field_out] = str(100.0*float(stats_dict['Aligned_reads'])/float(stats_dict['Trimmed_reads']))
		elif field == 'Multimap_rate':
			new_row[field_out] = str(100.0*float(stats_dict['Multimap_reads'])/float(stats_dict['Trimmed_reads']))
		elif row.has_key(field):
			new_row[field_out] = str(row[field].strip())
		elif stats_dict.has_key(field):
			new_row[field_out] = str(stats_dict[field])
		else:
			new_row[field_out] = 'N/A'
			print 'No field called :' + field


	tsv_writer.writerow(new_row)


csv_file.close()
tsv_outfile.close()

