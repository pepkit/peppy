#!/usr/bin/env Rscript

library(data.table)
suppressPackageStartupMessages(library("optparse"))

##scale=10000000
##genome="mm10"
##results_dir="/scratch/lab_bock/shared/projects/geissmann/results_pipeline/results_pipeline/"
##stats_path="/scratch/lab_bock/shared/projects/geissmann/results_pipeline/results_pipeline/ALL_stats_summary.tsv"

# specify our desired options in a list
option_list = list(
  make_option(c("-r", "--results_dir"), type="character", help="Input Results folder (REQUIRED)"),
  make_option(c("-g", "--genome"), type="character", help="Genome used for alignment (REQUIRED)"),
  make_option(c("-s", "--stats"), type="character", help="Alignment stats table for all samples (REQUIRED)"),
  make_option(c("-n", "--scale"), type="character", help="Normalization scale (REQUIRED)")
  )

opt = parse_args(OptionParser(option_list=option_list))
if (length(opt)<4) {
  print_help(OptionParser(option_list=option_list))
}else {
  results_dir=opt$results_dir
  genome=opt$genome
  stats_path=opt$stats
  scale=opt$scale
}

print(results_dir)
print(genome)
print(stats_path)
print(scale)

chroSizes_path=paste0("/data/groups/lab_bock/shared/resources/genomes/",genome,"/",genome,".chromSizes")




stats=fread(stats_path)
stats=stats[pipeline=="rnaTopHat"]
stats[,wigPath:=paste0(results_dir,"/",sampleName,"/tophat_",genome,"/",sampleName,".aln_sorted.wig"),]

for (i in c(2:nrow(stats))){
  sampleName=stats[i]$sampleName
  message(sampleName)
  wigFileName=stats[i]$wigPath
  mappedReads=stats[i]$Aligned_reads
  if (file.exists(wigFileName)){
    system(paste0("sed 's/ \\+/\\t/g'  ",wigFileName," > ", wigFileName,"_temp",sep=""))
    wig=fread(paste0(wigFileName,"_temp"),header=FALSE)
    wig[V1=="variableStep",V3:=paste0(V1," ",V2)]
    wig[grep("variableStep",V3),V1:=NA]
    wig[grep("variableStep",V3),V2:=NA]
    wig[,V2:=round(as.numeric(V2)/mappedReads*scale,2),]
    wig[,c("V1","V2"):=list(as.character(V1),as.character(V2)),]
    wig[grep("variableStep",V3),c("V1","V2"):=list(V3,"")]
    wig[,V3:=NULL,]
    write.table(wig,sub(".wig","_norm.wig_temp",wigFileName),sep="\t",col.names=FALSE,row.names=FALSE,quote=FALSE)
    system(paste0("sed 's/\t$//g' ",sub(".wig","_norm.wig_temp",wigFileName)," > ", sub(".wig","_norm.wig",wigFileName)))
    system(paste("wigToBigWig",sub(".wig","_norm.wig",wigFileName),chroSizes_path,sub(".wig","_norm.bw",wigFileName),sep=" "))
    system(paste("rm ",sub(".wig",".wig_temp",wigFileName)))
    system(paste("rm ",sub(".wig","_norm.wig_temp",wigFileName)))
  }else{
    message(paste0("File not found. Skipping: ",wigFileName))
    next}
}

