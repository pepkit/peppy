#libraries
suppressPackageStartupMessages(library(data.table))
suppressPackageStartupMessages(library(ggplot2))
suppressPackageStartupMessages(library(simpleCache))
suppressPackageStartupMessages(library(reshape2))
suppressPackageStartupMessages(library(cummeRbund))

#things to set
setwd("/data/scratch/lab_bock/jklughammer/projects/compEpi/")
results_pipeline="/data/scratch/lab_bock/jklughammer/projects/compEpi/results_pipeline/"
sampleAnnotation_path="/data/groups/lab_bock/jklughammer/gitRepos/compEpi/meta/projectSampleAnnotation.csv"
genome="hg19_cdna"
organism="human"

system(paste0("mkdir -p ",getwd(),"/RCache/"))
setCacheDir(paste0(getwd(),"/RCache/"))

cacheName=paste0("Leukos_Hum_RNA_",genome)

QC_dir=paste0("results_analysis/QC_RNA-comp",genome)
system(paste0("mkdir -p ",QC_dir))


#set theme
theme_set(theme_bw())
old <- theme_update(text = element_text(family="Arial",face="plain",colour="black",size=12,hjust=0.5,vjust=0.5,angle=0,lineheight=0.9))

#------FUNCTIONS------------

scale.vals=function(vals,upper,lower,log){
  
  pLower=quantile(vals,lower)
  pUpper=quantile(vals,upper)
  vals=ifelse(vals<pLower,pLower,ifelse(vals>pUpper,pUpper,vals))
  if (log==TRUE){
    vals=log(vals+0.00001)} 
  vals=(vals-min(vals))/(max(vals)-min(vals))*10
  return(vals)
}


collectBitSeqData = function(results_pipeline,sampleAnnotationFile,transcriptAnnotation,genome,resultsStats){
  rna_all=data.table()
  sample_no=0
  for (i in 1:nrow(sampleAnnotationFile)){
    print(sampleAnnotationFile[i]$sample_name)
    if (sampleAnnotationFile[i]$run == 1){
      tr_file=paste0(results_pipeline,"/",sampleAnnotationFile[i]$sample_name,"/bowtie1_",genome,"/bitSeq/",sampleAnnotationFile[i]$sample_name,".tr")
      means_file=paste0(results_pipeline,"/",sampleAnnotationFile[i]$sample_name,"/bowtie1_",genome,"/bitSeq/",sampleAnnotationFile[i]$sample_name,".mean")
      counts_file=paste0(results_pipeline,"/",sampleAnnotationFile[i]$sample_name,"/bowtie1_",genome,"/bitSeq/",sampleAnnotationFile[i]$sample_name,".counts")
      if (file.exists(tr_file)&file.exists(means_file)&file.exists(counts_file)){
        sample_no=sample_no+1
        tr=fread(tr_file)
        setnames(tr,names(tr),c("ensG","ensT","length","length_adj"))
        tr[,sample_name:=sampleAnnotationFile[i]$sample_name,]
        tr[,sampleID:=paste0("sample_",sample_no),]
        tr[,patient:=sampleAnnotationFile[i]$patient,]
        tr[,exp_category:=sampleAnnotationFile[i]$exp_category,]
        tr[,FACS_marker:=sampleAnnotationFile[i]$FACS_marker,]
        tr[,cell_type:=sampleAnnotationFile[i]$cell_type,]
        tr[,treatment:=sampleAnnotationFile[i]$treatment,]
        tr[,treatment_length:=sampleAnnotationFile[i]$treatment_length,]
        tr[,cell_count:=sampleAnnotationFile[i]$cell_count,]
        tr[,library:=sampleAnnotationFile[i]$library,]
        tr[,Raw_reads:=resultsStats[sampleName==sampleAnnotationFile[i]$sample_name,"Raw_reads",with=FALSE],]
        tr[,Aligned_reads:=resultsStats[sampleName==sampleAnnotationFile[i]$sample_name,"Aligned_reads",with=FALSE],]
        if ("Filtered_reads" %in% names(resultsStats)){
          tr[,Filtered_reads:=resultsStats[sampleName==sampleAnnotationFile[i]$sample_name,"Filtered_reads",with=FALSE],]  
        }
        
        means=fread(means_file)
        setnames(means,names(means),c("RPKM","RPKM_var"))
        counts=fread(counts_file)
        combined=cbind(tr,means,counts)
        merge = merge(transcriptAnnotation,combined,by=c("ensG","ensT"),all=TRUE)
        rna_all=rbindlist(list(rna_all,merge))
      }
      else{print("file not found")}
    }
    else{print("not selected")}
  }
  return(rna_all)
}


callMDS=function(RPKM,offset){
  rna.dist=JSdist(makeprobs(as.data.frame(RPKM)[,(offset+1):ncol(RPKM)]))
  rna.mds=cmdscale(rna.dist, eig = TRUE, k = 2)
  MDS = data.table(sample_name =rownames(rna.mds$points), MDS1 = rna.mds$points[,1], MDS2 = rna.mds$points[, 2])
  
  return(MDS) 
}


#load required files
sampleAnnotationFile=fread(sampleAnnotation_path)
resultsStats=fread(paste0(results_pipeline,"/rnaBitSeq_stats_summary.tsv"))
resultsStats_tophat=fread(paste0(results_pipeline,"/rnaTopHat_stats_summary.tsv"))

sampleAnnotationFile=sampleAnnotationFile[organism==organism]


transcriptAnnotation=fread(tail(system(paste0("ls /data/groups/lab_bock/shared/resources/genomes/",genome,"/transcripts_*"),intern=TRUE),n=1))
#only for m38 transcript and chromosome are includes so far. Need to be included for pther genomes.
setnames(transcriptAnnotation,names(transcriptAnnotation),c("ensG","ensT","transc_start","transc_end","transcript","gene","biotype","strand","chr","ensP"))
#Use for hg19_cdna
setnames(transcriptAnnotation,names(transcriptAnnotation),c("ensG","ensT","transc_start","transc_end","gene","biotype","strand","ensP"))

simpleCache(recreate=FALSE,cacheName,instruction="collectBitSeqData(results_pipeline,sampleAnnotationFile,transcriptAnnotation,genome,resultsStats)")
rnaCombined=get(cacheName)

#provide unchanged table of rpkm values
#Mouse
rnaCombined_wide=dcast.data.table(unique(rnaCombined[!is.na(RPKM)]),ensT+ensG+gene+transcript~sample_name,value.var="RPKM")
#Human
rnaCombined_wide=dcast.data.table(unique(rnaCombined[!is.na(RPKM)]),ensT+ensG+gene~sample_name,value.var="RPKM")
write.table(rnaCombined_wide,paste0(QC_dir,"/RPKM_combined.tsv"),sep="\t",row.names=FALSE,quote=FALSE)

#provide unchanged table of count values
#Mouse
rnaCombined_wide=dcast.data.table(unique(rnaCombined[!is.na(count)]),ensT+ensG+gene+transcript~sample_name,value.var="count")
#Human
rnaCombined_wide=dcast.data.table(unique(rnaCombined[!is.na(count)]),ensT+ensG+gene~sample_name,value.var="count")

write.table(rnaCombined_wide,paste0(QC_dir,"/counts_combined.tsv"),sep="\t",row.names=FALSE,quote=FALSE)

#rnaCombined_unique=unique(rnaCombined[!is.na(RPKM),names(rnaCombined)[!names(rnaCombined)%in%c("GO_term","GO_ID")],with=FALSE])
rnaCombined_unique=unique(rnaCombined[!is.na(RPKM)])

#add sampleID column to resultStats
resultsStats_annot=merge(unique(rnaCombined_unique[,list(sampleName=sample_name),by=c("sampleID")]),resultsStats,by="sampleName")
write.table(resultsStats_annot,paste0(QC_dir,"/rnaBitSeq_stats_summary_ID.tsv"),sep="\t",row.names=FALSE,quote=FALSE)

resultsStats_tophat_annot=merge(unique(rnaCombined_unique[,list(sampleName=sample_name),by=c("sampleID")]),resultsStats_tophat,by="sampleName")
write.table(resultsStats_tophat_annot,paste0(QC_dir,"/rnaTopHat_stats_summary_ID.tsv"),sep="\t",row.names=FALSE,quote=FALSE)

publish=merge(resultsStats_annot[,c("sampleID","Raw_reads","Trimmed_reads","Aligned_reads","ERCC_aligned_reads","alignment_rate","ERCC_alignment_rate"),with=FALSE],resultsStats_tophat_annot[,c("sampleID","Aligned_reads","alignment_rate"),with=FALSE],by="sampleID")
setnames(publish,c("Aligned_reads.x","Aligned_reads.y","alignment_rate.x","alignment_rate.y"),c("Aligned_reads_bowtie1","Aligned_reads_tophat","alignment_rate_bowtie1","alignment_rate_tophat"))
spl=unlist(strsplit(publish$sampleID,"_"))
publish=publish[order(as.numeric(spl[seq(2,length(spl),2)]))]

write.table(publish,paste0(QC_dir,"/combined_sequencing_stats.tsv"),sep="\t",row.names=FALSE,quote=FALSE)

#------------------Filtering-------------------------------------------
covThrs=25
rnaCombined_unique[,covPass:=ifelse(count<covThrs,FALSE,TRUE),]
rnaCombined_unique[count<covThrs,RPKM:=min(RPKM),]

sampleStats=rnaCombined_unique[covPass==TRUE,list(covTransc=.N),by=c("sample_name","sampleID")]
#cutPercentile=sampleStats[,quantile(covTransc,0.08),]
cutPercentile=500
sampleStats[,transcPass:=ifelse(covTransc>cutPercentile,TRUE,FALSE),]

sampleAnnotationFile=merge(sampleAnnotationFile,sampleStats,by="sample_name")
write.table(sampleStats,paste0(QC_dir,"/sampleStats_",covThrs,".tsv"),sep="\t",row.names=FALSE,quote=FALSE)


#CV=rnaCombined_unique[,list(CV=sd(RPKM)/mean(RPKM)),by="ensT"]
#CV[,CVrank:=rank(-CV,ties.method="min")]
#rnaCombined_unique=merge(CV,rnaCombined_unique,by="ensT")

#------------------wide format for clustering, MDS etc-------------------------------------------
RPKM_covPass=dcast.data.table(rnaCombined_unique[covPass==TRUE],ensT+ensG+gene~sampleID,value.var="RPKM")
RPKM_transcPass=dcast.data.table(rnaCombined_unique[sample_name %in% sampleStats[transcPass==TRUE]$sample_name],ensT+ensG+gene~sampleID,value.var="RPKM")
RPKM_transcPass_sampleName=dcast.data.table(rnaCombined_unique[sample_name %in% sampleStats[transcPass==TRUE]$sample_name],ensT+ensG+gene~sample_name,value.var="RPKM")

RPKM=dcast.data.table(rnaCombined_unique,ensT+ensG+gene~sampleID,value.var="RPKM")
RPKM_sampleName=dcast.data.table(rnaCombined_unique,ensT+ensG+gene~sample_name,value.var="RPKM")

write.table(RPKM,paste0(QC_dir,"/RPKM_covThrs",covThrs,".tsv"),sep="\t",row.names=FALSE,quote=FALSE)
write.table(RPKM_transcPass,paste0(QC_dir,"/RPKM_transcPass_covThrs",covThrs,".tsv"),sep="\t",row.names=FALSE,quote=FALSE)

#------------------quality control plots------------------------------
#covered transcripts
covered_transc=rnaCombined_unique[covPass==TRUE,list(covered_transcripts=.N,mean_rpkm=mean(RPKM)),by=c("sampleID","sample_name","Raw_reads", "Aligned_reads")]
covered_transc[,sampleID:=factor(sampleID,levels=unique(sampleID[order(covered_transcripts)]))]
#covered_transc[,sample_name:=factor(sample_name,levels=unique(sample_name[order(covered_transcripts)]))]

svg(paste0(QC_dir,"/count-passFilter",covThrs,".svg"),width=9,height=10)
ggplot(covered_transc,aes(x=factor(sampleID),y=covered_transcripts,fill=Aligned_reads))+geom_bar(stat="identity")+xlab("")+coord_flip()+geom_hline(yintercept=500,col="red")
dev.off()

svg(paste0(QC_dir,"/meanRPKMvsCoveredTranscripts-covPass","_",covThrs,".svg"),width=6,height=6)
ggplot(covered_transc,aes(x=covered_transcripts,y=log(mean_rpkm),col=Aligned_reads))+geom_point()+theme_bw()
dev.off()


#mean RPKM per Transcript/ per sample
mean_expr_perTransript=rnaCombined_unique[covPass==TRUE,list(mean_rpkm=mean(RPKM),sd=sd(RPKM)),by=c("ensT")]
mean_expr_perSample=rnaCombined_unique[covPass==TRUE,list(mean_rpkm=mean(RPKM),sd=sd(RPKM)),by=c("sample_name","Raw_reads", "Aligned_reads")]

svg(paste0(QC_dir,"/meanRPKM_perSample-covPass","_",covThrs,".svg"),width=6,height=6)
ggplot(mean_expr_perSample,aes(x=log(mean_rpkm)))+geom_bar()+ylab("number of samples")
dev.off()
svg(paste0(QC_dir,"/meanRPKM_perTranscripts-covPass","_",covThrs,".svg"),width=6,height=6)
ggplot(mean_expr_perTransript,aes(x=log(mean_rpkm)))+geom_bar()+ylab("number of transcripts")
dev.off()

#correlation between single cells
choose=sample(c(4:ncol(RPKM)),10)
panel.dens=function(x,y){
  points(x,y,col=densCols(x,y),pch=16,cex=1)
}
panel.cor <- function(x, y, digits=2, prefix="", cex.cor, ...)
{
  usr <- par("usr"); on.exit(par(usr))
  par(usr = c(0, 1, 0, 1))
  r <- abs(cor(x, y,method="spearman",use="complete.obs"))
  txt <- format(c(r, 0.123456789), digits=digits)[1]
  txt <- paste(prefix, txt, sep="")
  if(missing(cex.cor)) cex.cor <- 0.8/strwidth(txt)
  text(0.5, 0.5, txt, cex = cex.cor * r)
}
png(paste0(QC_dir,"/correlationScatter_logRPKM-covPass","_",covThrs,".png"),width=6000,height=6000)
pairs(log(RPKM_covPass[,choose,with=FALSE]),lower.panel=panel.dens,upper.panel=panel.cor)
dev.off()

#MDS
group="FACS_marker"#"exp_category" # needs to be column from sample annotation sheet

MDS=callMDS(RPKM_sampleName,3)
MDS_annot=merge(sampleAnnotationFile,MDS,by="sample_name")
svg(paste0(QC_dir,"/MDS-allTranscripts_",group,"_",covThrs,".svg"),width=7,height=6)
#ggplot(MDS_annot,aes(x=MDS1,y=MDS2,col=factor(exp_category)))+geom_point()+geom_text(aes(label=sample_name),size=3)+theme_bw()
ggplot(MDS_annot,aes(x=MDS1,y=MDS2,col=factor(get(group))))+geom_point()+geom_text(aes(label=sample_name),size=3)+theme_bw()
dev.off()

#[,-grep("Patient",names(RPKM_transcPass_sampleName)),with=FALSE]
MDS=callMDS(RPKM_transcPass_sampleName,3)
MDS_annot=merge(sampleAnnotationFile,MDS,by="sample_name")
svg(paste0(QC_dir,"/MDS-allTranscripts-transcPass_",group,"_",covThrs,".svg"),width=7,height=6)
#ggplot(MDS_annot,aes(x=MDS1,y=MDS2,col=factor(exp_category)))+geom_point()+geom_text(aes(label=sample_name),size=3)+theme_bw()
ggplot(MDS_annot,aes(x=MDS1,y=MDS2,col=factor(get(group))))+geom_point()+geom_text(aes(label=sample_name),size=3)+theme_bw()
dev.off()

MDS=callMDS(RPKM_transcPass,3)
setnames(MDS,"sample_name","sampleID")
MDS_annot=merge(sampleAnnotationFile,MDS,by="sampleID")
svg(paste0(QC_dir,"/MDS-allTranscripts-transcPass_ID_",group,"_",covThrs,".svg"),width=7,height=6)
#ggplot(MDS_annot,aes(x=MDS1,y=MDS2,col=factor(exp_category)))+geom_point()+geom_text(aes(label=sample_name),size=3)+theme_bw()
ggplot(MDS_annot,aes(x=MDS1,y=MDS2,col=factor(get(group))))+geom_point()+geom_text(aes(label=sampleID),size=3)+theme_bw()
dev.off()

