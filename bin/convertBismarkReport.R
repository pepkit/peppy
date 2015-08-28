#!/usr/bin/env Rscript
options(echo=FALSE)
library("data.table")
suppressPackageStartupMessages(library("optparse"))
#d <- fread("/data/groups/lab_bock/fhalbrit/projects/hema_precursors//results_pipeline//results_pipeline/MPP_10_D1_1_R1//bismark_hg38/extractor/MPP_10_D1_1_R1.aln.dedup.filt.CpG_report_filt.txt")


optionList <- list(
	make_option( c("-i", "--input"), type="character", help="Input file. A Bismark CpG report (CHR START STRAND HITCOUNT MISSCOUNT DINUCLEOTIDE CONTEXT)"),
	make_option( c("-f", "--formats"), type="character", default="cov,min", help="A comma-separated list of output formats. Supported formats are: cov (Bismark coverage file: CHR START END METHPERCENT HITCOUNT MISSCOUNT), min (minimal coverage file: CHR START HITS TOTAL). Default: cov,min"),
	make_option( c("-c", "--noCovFilter"), default=FALSE,type="logical", action="store_true", help="Disable coverage filter. If not set, CpG's without any coverage will be removed"),
	make_option( c("-s", "--noChromFilter"), default=FALSE, type="logical", action="store_true", help="Disable chromosome filter. If not set, non-standard chromosomes (everything with an underscore in the name) will be removed"),
	make_option( c("-a", "--noAdjustMinusStrand"), default=FALSE, type="logical", action="store_true", help="Disable reverse strand adjustment. If not set, the coordiantes of all sites on the reverse strand (-) will be adjusted by subtracting 1")
)
opts <- parse_args(OptionParser(option_list=optionList))


if (is.null(opts$input)) {
	print_help(OptionParser(option_list=optionList))
	stop("No input file provided")
} else {
	cpgReport <- opts$input
	filterUncovered <- !opts$noCovFilter
	removeNonStandardChroms <- !opts$noChromFilter
	adjustMinusStrand <- !opts$noAdjustMinusStrand
	outputFormats <- strsplit(tolower(opts$formats),",")[[1]]

	message("+ Starting to convert Bismark CpG report file: ", cpgReport)

	# read in data:
	message("\tReading and modifying data...")
	d <- fread(cpgReport)
	setnames(d, paste0("V", 1:7), c("chr", "start", "strand", "hitCount", "missCount", "dinucleotide", "context"))

	# calculate total read count:
	d[, readCount:=hitCount+missCount]

	# remove unnecessary columns:
	d[, c("dinucleotide", "context", "missCount"):=NULL]

	# remove uncovered regions:
	if(filterUncovered) {
		message("\tRemove uncovered CpG's...")
		d <- d[ readCount>0,]
	}

	# adjust the coordinate of C's on the (-)-strand:
	if(adjustMinusStrand) {
		message("\tAdjusting reverse strand coordinates...")
		d[strand=="-",start := as.integer(start-1)] 
	}
	d[, strand:=NULL]

	# aggregate all regions with identical coordinates:
	message("\tAggregating regions by coordinate...")
	d <- d[,list(hitCount= sum(hitCount), readCount=sum(readCount)), by=list(chr, start)] 
	setcolorder(d,c("chr", "start", "hitCount", "readCount"));

	# remove non-standard chromosomes (_random, unintegrated contiqs, etc.)
	if(removeNonStandardChroms) {
		message("\tFiltering chromosomes...")
		d <- d[ !grep("_",chr),];
	}
		
	# write output file(s):
	for(outputFormat in outputFormats) {
		outName <- paste0(gsub(".txt$", "", cpgReport, perl=TRUE, ignore.case=TRUE), ".", outputFormat)
		if(outputFormat == "cov") {
			message("\tWriting Bismark coverage format (CHR START END METHPERCENT HITCOUNT MISSCOUNT): ", outName)
			d[, methPerc:= hitCount/readCount*100]
			d[, missCount:= readCount-hitCount]
			write.table(d[,list(chr,start,start,methPerc,hitCount,missCount)], file=outName, sep="\t", row.names=FALSE, col.names=FALSE, quote=FALSE)
		}
		else if(outputFormat == "min") {	
			message("\tWriting minimal coverage output format (CHR START HITS TOTAL): ", outName)
			write.table(d[,list(chr,start,hitCount,readCount)], file=outName, sep="\t", row.names=FALSE, col.names=FALSE, quote=FALSE)
		}
		else {
			warning("\tUnrecognized output format: ", outputFormat)
		}
	}

	message("+ Finished conversion: ", cpgReport)
}
