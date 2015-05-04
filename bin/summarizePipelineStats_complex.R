#!/usr/bin/env Rscript
options(echo=FALSE);
library(data.table)
library(reshape2) #no longer necessary after data.table 1.9.5??
suppressPackageStartupMessages(library("optparse"))

# specify our desired options in a list
option_list = list(
make_option(c("-i", "--inputFolder"), type="character", help="Input Results folder (REQUIRED)"))

opt = parse_args(OptionParser(option_list=option_list))
if (is.null(opt$inputFolder)) {
	print_help(OptionParser(option_list=option_list));
	inputFolder = "/fhgfs/groups/lab_bock/shared/COREseq/results_pipeline3"
#	q();
} else {
	inputFolder=opt$inputFolder
}

message("input folder: ", inputFolder);
pipeDirs = list.dirs(inputFolder, recursive=FALSE)

message("Read all *_stats.txt files in the pipeline results folder")
results=list()
dir = pipeDirs[[1]];
for (dir in pipeDirs) {
	message(dir);
	statFiles = list.files(dir, pattern="_stats.txt")
	statFiles2 = list.files(dir, pattern="stats_")
	statFiles = c(statFiles, statFiles2)
	for (statFile in statFiles) {
		message(statFile);
		pipeline = gsub("_stats.txt", "", statFile)
		pipeline = gsub("stats_", "", pipeline)
		statPath = paste0(dir, "/", statFile);
		a = fread(statPath)
		setnames(a, c("key", "value"))
		a[,key:=gsub(" ", "_", key)] # Change spaces to underscores
		#Order keys as factors, to maintain order through later cast.
		a[,key:=factor(key, levels=unique(key))]
		#setkey(a, "key")
		a[,sampleName:=basename(dir)]
		a[,pipeline:=pipeline]
		sampleName = basename(dir)
		if (is.null(results[[pipeline]])) { results[[pipeline]] = list(); }
		results[[pipeline]][[sampleName]] = a;
	}
}
if (length(results) ==0) {
	stop("No stats files found.");
}
results
#Combined, divided by pipeline
resultsDT = lapply(results, function(x) { do.call(rbind, x); })

# Select latest for identical statistics
resultsDT = lapply(resultsDT, function(x) { x[,list(value=value[length(value)]), by=c("key", "sampleName", "pipeline"), roll=+Inf] })

# Cast to wide format
resultsMat = lapply(resultsDT, dcast, formula= "... ~ key")
resultsMat = lapply(resultsMat, as.data.table)
# Convert number-only cols to numerics, so I can do some stats below.
numToNumeric = function(DT) {
	return(DT[,lapply(.SD, function(x) { if(!any(grepl("[a-zA-Z:_\\-]", x))) { return(as.numeric(x)); } else { return(x)} })])
}
resultsMat = lapply(resultsMat, numToNumeric)
#lapply(resultsMat, sapply, mode)

################################################################################
# Do any pipeline-specific calculations here
################################################################################

#WGBS

if ("WGBS" %in% names(resultsMat)){
	resultsMat$WGBS[, total_efficiency := (Deduplicated_reads)/Raw_reads]
	resultsMat$WGBS[, trim_loss_rate := (Raw_reads - Trimmed_reads)/Raw_reads]
	resultsMat$WGBS[, alignment_rate := (Aligned_reads)/Trimmed_reads]
	resultsMat$WGBS[, dupe_loss_rate := (Aligned_reads - Deduplicated_reads)/Aligned_reads]
	resultsMat$WGBS[, filt_loss_rate := (Deduplicated_reads - Filtered_reads)/Deduplicated_reads]
}


# Tophat
if ("rnaTopHat" %in% names(resultsMat)){
  if ("Filtered_reads" %in% names(resultsMat$rnaTopHat)){
  resultsMat$rnaTopHat[, total_efficiency := Filtered_reads/Raw_reads]}
	resultsMat$rnaTopHat[, trim_loss_rate := (Raw_reads - Trimmed_reads)/Raw_reads]
	resultsMat$rnaTopHat[, alignment_rate := (Aligned_reads)/Trimmed_reads]
	if ("Filtered_reads" %in% names(resultsMat$rnaTopHat)){
	  if ("Deduplicated_reads" %in% names(resultsMat$rnaTopHat)){
      resultsMat$rnaTopHat[, dupe_loss_rate := (Filtered_reads - Deduplicated_reads)/Filtered_reads]}
    resultsMat$rnaTopHat[, filt_loss_rate := (Aligned_reads - Filtered_reads)/Aligned_reads]}
  else if ("Deduplicated_reads" %in% names(resultsMat$rnaTopHat)){
    resultsMat$rnaTopHat[, dupe_loss_rate := (Aligned_reads - Deduplicated_reads)/Aligned_reads]}
}
# Bitseq
if ("rnaBitSeq" %in% names(resultsMat)){
  if ("Filtered_reads" %in% names(resultsMat$rnaTopHat)){
	  resultsMat$rnaBitSeq[, total_efficiency := Filtered_reads/Raw_reads]}
	resultsMat$rnaBitSeq[, trim_loss_rate := (Raw_reads - Trimmed_reads)/Raw_reads]
	resultsMat$rnaBitSeq[, alignment_rate := (Aligned_reads)/Trimmed_reads]
  if ("Filtered_reads" %in% names(resultsMat$rnaTopHat)){
    resultsMat$rnaBitSeq[, dupe_loss_rate := (Filtered_reads - Deduplicated_reads)/Filtered_reads]
	  resultsMat$rnaBitSeq[, filt_loss_rate := (Aligned_reads - Filtered_reads)/Aligned_reads]}
  else {resultsMat$rnaBitSeq[, dupe_loss_rate := (Aligned_reads - Deduplicated_reads)/Aligned_reads]}
	resultsMat$rnaBitSeq[, ERCC_alignment_rate := (ERCC_aligned_reads)/Trimmed_reads]
}

################################################################################
# Write results
################################################################################
commonCols = Reduce(intersect, lapply(resultsMat, colnames));
commonList = lapply(resultsMat, function(x) { x[,commonCols, with=FALSE] })
commonTable = do.call(rbind, commonList)


# Write individual result tables for each pipeline
pipelines = names(resultsMat)
for (p in pipelines) {
	pipeStatFile = paste0(inputFolder, "/", p, "_stats_summary.tsv")
	message("Writing pipeline stats table: ", pipeStatFile)
	write.table(resultsMat[[p]], pipeStatFile, sep="\t",row.names=FALSE,quote=FALSE)
}

# Produce an additional table with only common features
commonTableFile = paste0(inputFolder, "/ALL_stats_summary.tsv");
message("Writing common table: ", commonTableFile);
write.table(commonTable, commonTableFile,sep="\t",row.names=FALSE,quote=FALSE)


