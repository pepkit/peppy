#!/usr/bin/env Rscript
options(stringsAsFActors=FALSE)
library(BitSeq)
library(data.table)
args=commandArgs(trailingOnly = TRUE)

wd=args[1]
#wd="/fhgfs/groups/lab_bock/shared/projects/setdb2/data/pypiper_pipeline/"
sampleAnnotationFile=args[2]  
#sampleAnnotationFile="/fhgfs/groups/lab_bock/shared/projects/setdb2/data/pypiper_pipeline/metadata/projectSampleAnnotation.csv"
dataDir=args[3]
#dataDir="/fhgfs/groups/lab_bock/shared/projects/setdb2/data/pypiper_pipeline/results_pipeline/"

group=args[4]
#group="0h"
genome=args[5]
#genome="m38_cdna"
outDir=args[6]
#outDir="/fhgfs/groups/lab_bock/shared/projects/setdb2/data/pypiper_pipeline/differentialExpression/0h_WT-KO_DE"
cond1=args[7]
#cond1="WT"
cond2=args[8]
#cond2="KO"
groups_column=args[9]
#groups_column="treatment_length"
comparison_column=args[10]
#comparison_column="treatment"

#outDir=paste0(outName,"/",cellType,"_",cond1,"-",cond2,"_DE")


transcriptAnnotation=fread(tail(system(paste0("ls /data/groups/lab_bock/shared/resources/genomes/",genome,"/transcripts_*"),intern=TRUE),n=1))
setnames(transcriptAnnotation,names(transcriptAnnotation),c("ensG","ensT","transc_start","transc_end","transcript","gene","biotype","strand","chr","ensP"))
transcriptAnnotation=unique(transcriptAnnotation[,c("ensG","ensT","transc_start","transc_end","transcript","gene","biotype","strand","chr","ensP"),with=FALSE])


setwd(wd)
IDmatrix=fread(sampleAnnotationFile,select=c("sample_name",groups_column,comparison_column,"run"))
IDmatrix=IDmatrix[run==1]
setnames(IDmatrix,c(groups_column,comparison_column),c("groups","comparison"))
IDmatrix[,rpkmPath:=unlist(lapply(sample_name,function(x){system(paste0("ls ",dataDir,"/*/*/bitSeq/",x,".rpkm"), intern=TRUE)})),]




performDE=function(outDir,rpkmList,cond1_name,cond2_name){
  system(paste0("mkdir -p ",outDir))
  
  message("calculating mean variance")
  getMeanVariance(rpkmList,outFile=paste0(outDir,"/data.means"),log=TRUE,verbose=TRUE)
  
  message("estimate hyperparameters")
  estimateHyperPar(outFile=paste0(outDir,"/data.par"),conditions=rpkmList,meanFile=paste0(outDir,"/data.means"),verbose=TRUE)
  
  message("estimating differential expression")
  estimateDE(rpkmList,outFile=paste0(outDir,"/data"),parFile=paste0(outDir,"/data.par"),verbose=TRUE,samples=TRUE)
  
  pplr=fread(paste0(outDir,"/data.pplr"))
  setnames(pplr,names(pplr),c("rna.pplr","rna.log2_fc","rna.conf_low","rna.conf_high","rna.logMean1","rna.logMean2"))
  tr=fread(gsub("rpkm","tr",rpkmList[[1]][1]))
  setnames(tr,names(tr),c("ensG","ensT","tr.length","tr.length_adj"))
  
  pplr_annot=cbind(tr,pplr)
  pplr_annot[,rna.logMeanDiff:=rna.logMean2-rna.logMean1,]
  
  #change according to conditions used
  pplr_annot[,rna.expr_hi:=ifelse(rna.logMean1>rna.logMean2,cond1,ifelse(rna.logMean2>rna.logMean1,cond2,"tie")),]
  
  pplr_annot[,rna.rank_pplr:=rank(-abs(0.5-rna.pplr),ties.method="min"),]
  pplr_annot[,rna.rank_logfc:=rank(-abs(rna.log2_fc),ties.method="min"),]
  pplr_annot[,rna.rank_logDiff:=rank(-abs(rna.logMeanDiff),ties.method="min"),]
  pplr_annot[,rna.rank_max:=pmax(rna.rank_pplr,rna.rank_logfc,rna.rank_logDiff),]
  pplr_annot=merge(transcriptAnnotation,pplr_annot,by=c("ensG","ensT"))
  pplr_annot=pplr_annot[order(rna.rank_max)]
  
  pplr_annot_unique=pplr_annot
  pplr_annot_unique[,keep:=ensT[which.min(rna.rank_max)],by="ensG"]
  pplr_annot_unique=pplr_annot_unique[keep==ensT]
  pplr_annot_unique[,keep:=NULL,]
  
  
  cond1_rank=pplr_annot_unique[,list(ensG,ensT,ensP,gene,rna.rank_pplr=rank(rna.pplr,ties.method="min"),rna.rank_logfc=rank(rna.log2_fc,ties.method="min"),rna.rank_logDiff=rank(rna.logMeanDiff,ties.method="min")),]
  cond1_rank[,rna.rank_max:=pmax(rna.rank_pplr,rna.rank_logfc,rna.rank_logDiff),]
  cond2_rank=pplr_annot_unique[,list(ensG,ensT,ensP,gene,rna.rank_pplr=rank(-rna.pplr,ties.method="min"),rna.rank_logfc=rank(-rna.log2_fc,ties.method="min"),rna.rank_logDiff=rank(-rna.logMeanDiff,ties.method="min")),]
  cond2_rank[,rna.rank_max:=pmax(rna.rank_pplr,rna.rank_logfc,rna.rank_logDiff),]
  
  cond1_rank=cond1_rank[,c("ensG","gene","rna.rank_max"),with=FALSE]
  cond2_rank=cond2_rank[,c("ensG","gene","rna.rank_max"),with=FALSE]
  setnames(cond1_rank,"rna.rank_max",paste0(cond1,"_",cond2))
  setnames(cond2_rank,"rna.rank_max",paste0(cond1,"_",cond2))
  
  write.table(cond1_rank,paste0(outDir,"/",cond1,".rank"),sep="\t",quote=FALSE,row.names=FALSE)
  write.table(cond2_rank,paste0(outDir,"/",cond2,".rank"),sep="\t",quote=FALSE,row.names=FALSE)
  
  write.table(pplr_annot,paste0(outDir,"/data.annot"),sep="\t",quote=FALSE,row.names=FALSE)
  write.table(pplr_annot_unique,paste0(outDir,"/data.annot.uniq"),sep="\t",quote=FALSE,row.names=FALSE)
}


rpkmList=list(IDmatrix[groups==group&comparison==cond1]$rpkmPath,IDmatrix[groups==group&comparison==cond2]$rpkmPath)


print(rpkmList)
performDE(outDir,rpkmList,cond1,cond2)
