#!/usr/bin/env python

__author__ = "Nathan Sheffield"
__credits__ = []
__license__ = "GPL3"
__version__ = "0.1"
__maintainer__ = "Nathan Sheffield"
__email__ = "nathan@code.databio.org"
__status__ = "Development"

from pypiper import Pypiper
from pypiper import ngstk
from argparse import ArgumentParser 

parser = ArgumentParser(description='Pipeline')

# First, add arguments from Pypiper
# This adds options including:
# -R: Recover mode to overwrite locks
# -D: Dirty mode to make suppress cleaning intermediate files
parser = Pypiper.add_pypiper_args(parser)
 
parser.add_argument("-c", "--config", dest="config_file", default="cpgseq_pipeline_config.yaml", type=str, \
  help="optional: location of the YAML configuration file for the pipeline; defaults to: ./cpgseq_pipeline_config.yaml", metavar="")

parser.add_argument("-i", "--input", dest="input", required=True, nargs="+", \
  help="required: unmapped BAM file(s) used as input for the pipeline; will be merged if more than one file is provided.", metavar="INPUTS")
# input was previously called unmapped_bam

parser.add_argument("-o", "--output_parent", dest="output_parent", required=True, \
  help="required: parent output directory of the project", metavar="") 
# output_parent was previously called project_root

parser.add_argument("-s", "--sample_name", dest="sample_name", required=True, \
  help="required: sample name; will be used to establish the folder structure and for naming output files", metavar="SAMPLE")

args = parser.parse_args()

# Read YAML config file

with open(args.config_file, 'r') as config_file:
  config = yaml.load(config_file)

# Create a Pypiper object, forwarding args to pypiper

pipeline_outfolder = os.path.abspath(os.path.join(args.output_parent, args.sample_name))
pipe = Pypiper(name="CpGseq", outfolder=pipeline_outfolder, args=args)  

pipe.timestamp("### Running procedure")

# Add pipeline commands here


# Terminate
pipe.stop_pipeline()


