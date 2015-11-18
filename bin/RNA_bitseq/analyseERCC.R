#libraries
suppressPackageStartupMessages(library(data.table))
suppressPackageStartupMessages(library(ggplot2))
suppressPackageStartupMessages(library(simpleCache))
suppressPackageStartupMessages(library(reshape2))
suppressPackageStartupMessages(library(cummeRbund))
suppressPackageStartupMessages(library(gtools))

#things to set
setwd("/data/scratch/lab_bock/jklughammer/projects/compEpi/")
results_pipeline="/data/scratch/lab_bock/jklughammer/projects/compEpi/results_pipeline/"
sampleAnnotation_path="/data/groups/lab_bock/jklughammer/gitRepos/compEpi/meta/projectSampleAnnotation.csv"
genome="ERCC92"
organism="human"
sampleAnnotationFile=fread(sampleAnnotation_path)

system(paste0("mkdir -p ",getwd(),"/RCache/"))
setCacheDir(paste0(getwd(),"/RCache/"))

cacheName=paste0("Leukos_Hum_RNA_",genome)

QC_dir=paste0("results_analysis/QC_",genome)
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


collectBitSeqERCC = function(results_pipeline,sampleAnnotationFile,transcriptAnnotation,genome,resultsStats){
  rna_all=data.table()
  sample_no=0
  for (i in 1:nrow(sampleAnnotationFile)){
    print(sampleAnnotationFile[i]$sample_name)
    if (sampleAnnotationFile[i]$run == 1){
      tr_file=paste0(results_pipeline,"/",sampleAnnotationFile[i]$sample_name,"/bowtie1_",genome,"/bitSeq/",sampleAnnotationFile[i]$sample_name,"_ERCC.tr")
      means_file=paste0(results_pipeline,"/",sampleAnnotationFile[i]$sample_name,"/bowtie1_",genome,"/bitSeq/",sampleAnnotationFile[i]$sample_name,"_ERCC.mean")
      counts_file=paste0(results_pipeline,"/",sampleAnnotationFile[i]$sample_name,"/bowtie1_",genome,"/bitSeq/",sampleAnnotationFile[i]$sample_name,"_ERCC.counts")
      if (file.exists(tr_file)&file.exists(means_file)&file.exists(counts_file)){
        sample_no=sample_no+1
        tr=fread(tr_file,drop="V1")
        setnames(tr,names(tr),c("ID","length","length_adj"))
        tr[,sample_name:=sampleAnnotationFile[i]$sample_name,]
        tr[,sampleID:=paste0("sample_",sample_no),]
        tr[,exp_category:=sampleAnnotationFile[i]$exp_category,]
        tr[,ERCC_spikein:=sampleAnnotationFile[i]$ERCC_spikein,]
        tr[,ERCC_spikein_dilution:=sampleAnnotationFile[i]$ERCC_spikein_dilution,]
        tr[,cell_type:=sampleAnnotationFile[i]$cell_type,]
        tr[,cell_count:=sampleAnnotationFile[i]$cell_count,]
        tr[,library:=sampleAnnotationFile[i]$library,]
        tr[,Raw_reads:=resultsStats[sampleName==sampleAnnotationFile[i]$sample_name,"Raw_reads",with=FALSE],]
        tr[,Aligned_reads:=resultsStats[sampleName==sampleAnnotationFile[i]$sample_name,"Aligned_reads",with=FALSE],]
        if ("Filtered_reads" %in% names(resultsStats)){
          tr[,Filtered_reads:=resultsStats[sampleName==sampleAnnotationFile[i]$sample_name,"Filtered_reads",with=FALSE],]  
        }
        tr[,ERCC_aligned_reads:=resultsStats[sampleName==sampleAnnotationFile[i]$sample_name,"ERCC_aligned_reads",with=FALSE],]
        means=fread(means_file)
        setnames(means,names(means),c("RPKM","RPKM_var"))
        counts=fread(counts_file)
        combined=cbind(tr,means,counts)
        merge = merge(transcriptAnnotation,combined,by="ID",all=TRUE)
        merge[,ERCC_molecules:=ifelse(ERCC_spikein=="mix1",concMix1*6.0223*10^23*(1/ERCC_spikein_dilution)*10^(-18),ifelse(ERCC_spikein=="mix2",concMix2*6.0223*10^23*(1/ERCC_spikein_dilution)*10^(-18),NA)),]
        merge[,ERCC_molecules_group:=10^floor(log10(ERCC_molecules)),]
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



#load files

transcriptAnnotation=fread("/data/groups/lab_bock/shared/resources/genomes/ERCC92/ERCC_Controls_Analysis.txt")
setnames(transcriptAnnotation,names(transcriptAnnotation),c("sortID","ID","subgroup","concMix1","concMix2","expectedFoldChange","log2_Mix1-Mix2"))
resultsStats=fread(paste0(results_pipeline,"/rnaBitSeq_stats_summary.tsv"))

#-------------------------

simpleCache(recreate=FALSE,cacheName,instruction="collectBitSeqERCC(results_pipeline,sampleAnnotationFile,transcriptAnnotation,genome,resultsStats)")
rnaCombined=get(cacheName)
rnaCombined[,ID:=factor(ID,levels=unique(ID[order(ERCC_molecules)])),]
rnaCombined[,sampleID:=factor(sampleID,levels=unique(mixedsort(sampleID))),]



#-------------Filter-----------------------------
covThrs=4
rnaCombined[,covPass:=ifelse(count<covThrs,FALSE,TRUE),]
#rnaCombined[count<covThrs,RPKM:=min(RPKM),]

ERCCs=unique(rnaCombined[,list(ID,ERCC_molecules),])

sampleStats=rnaCombined[covPass==TRUE,list(covTransc=.N),by=c("sample_name","sampleID")]
cutPercentile=0.9*nrow(ERCCs[ERCC_molecules>20])
sampleStats[,transcPass:=ifelse(covTransc>cutPercentile,TRUE,FALSE),]

write.table(sampleStats,paste0(QC_dir,"/sampleStats_",covThrs,".tsv"),sep="\t",row.names=FALSE,quote=FALSE)


#--------------QC plots----------------------------

#influence of length of transcript
rnaCombined[,measurements:=.N,by=c("ERCC_molecules","sampleID")]
rnaCombined[,correlation_RPKM:=round(cor(length,log(RPKM),method="pearson"),2),by="ERCC_molecules"]  #correlation probably not very reasonable if there are only two measurements
rnaCombined[,correlation_count:=round(cor(length,log(count),method="pearson"),2),by="ERCC_molecules"]
rnaCombined[,ERCC_molecules_round:=round(ERCC_molecules,0),]
rnaCombined[,length_n:=paste0(ERCC_molecules_round," molecules/sample"),]
rnaCombined[,length_n:=factor(length_n,levels=unique(length_n[order(ERCC_molecules_round)])),]

svg(paste0(QC_dir,"/length-RPKM.svg"),width=10,height=14)
ggplot(rnaCombined[measurements>=2&ERCC_molecules>200000],aes(y=log(RPKM),x=factor(length),col=covPass))+geom_point(size=2.6,position=position_jitter(width=0.16),alpha=0.5)+facet_wrap(~length_n,scale="free_x",ncol=2)+geom_smooth(aes(group = covPass,col=covPass),method=lm,se=FALSE,size=1)+xlab("ERCC length (bases)")+scale_color_discrete(name=paste0("coverage\n> ",covThrs," reads"))+theme(legend.position="bottom")
dev.off()

svg(paste0(QC_dir,"/length-count.svg"),width=10,height=14)
ggplot(rnaCombined[measurements>=2&ERCC_molecules>200000],aes(y=log(count),x=factor(length),col=covPass))+geom_point(size=2.6,position=position_jitter(width=0.16),alpha=0.5)+facet_wrap(~length_n,scale="free_x",ncol=2)+geom_smooth(aes(group = covPass,col=covPass),method=lm,se=FALSE,size=1)+xlab("ERCC length (bases)")+scale_color_discrete(name=paste0("coverage\n> ",covThrs," reads"))+theme(legend.position="bottom")
dev.off()

#Mean coverage of ERCCs
covered_transc=rnaCombined[covPass==TRUE,list(covered_transcripts=.N,mean_rpkm=mean(RPKM)),by=c("sampleID","sample_name","Raw_reads", "ERCC_aligned_reads")]
covered_transc[,sampleID:=factor(sampleID,levels=unique(sampleID[order(covered_transcripts)]))]
#covered_transc[,sample_name:=factor(sample_name,levels=unique(sample_name[order(covered_transcripts)]))]

svg(paste0(QC_dir,"/count-passFilter",covThrs,".svg"),width=9,height=10)
ggplot(covered_transc,aes(x=factor(sampleID),y=covered_transcripts,fill=ERCC_aligned_reads))+geom_bar(stat="identity")+xlab("")+coord_flip()+geom_hline(yintercept=92,col="red")
dev.off()

#plot expression of selected ERCCs in selected samples
sub=rnaCombined[ERCC_spikein=="mix1"&ERCC_spikein_dilution==250]
sub[,ID:=factor(ID,levels=unique(ID[order(concMix1)])),]
sub[,sel:=all(count>=4),by=ID]

svg(paste0(QC_dir,"/log10RPKM_boxplot_sel.svg"),width=9,height=6)
ggplot(sub[sel==TRUE],aes(x=ID,y=log(RPKM)))+geom_point(aes(fill=log(concMix1)),col="black",alpha=0.6,size=3.5,shape=21,position=position_jitter(width=0.2,height=0))+geom_boxplot(fill="transparent",col="darkgrey",outlier.shape=NA,width=1,size=0.8)+theme(axis.text.x=element_text(angle=90,vjust=0.5))+scale_fill_gradient(low="blue",high="red")
dev.off()


#boxplot of RPKM vs. ERCC concentration
svg(paste0(QC_dir,"/log10RPKM_boxplot.svg"),width=12,height=7)
ggplot(rnaCombined[],aes(x=ID,y=log10(RPKM),fill=factor(ERCC_molecules_group)))+geom_boxplot()+theme(axis.text.x = element_text(angle = 90, hjust = 1))+theme(legend.position="bottom")+guides(fill = guide_legend(nrow = 1,title="ERCC_molecules_group"))+facet_wrap(~library,nrow=2,scales="free")+theme_bw()
dev.off()

svg(paste0(QC_dir,"/log10RPKM_boxplot-covPass.svg"),width=9,height=7)
ggplot(rnaCombined[covPass==TRUE],aes(x=ID,y=log10(RPKM),fill=factor(ERCC_molecules_group)))+geom_boxplot()+theme(axis.text.x = element_text(angle = 90, hjust = 1))+theme(legend.position="bottom")+guides(fill = guide_legend(nrow = 1,title="ERCC_molecules_group"))+facet_wrap(~library,nrow=2,scales="free")+theme_bw()
dev.off()

svg(paste0(QC_dir,"/log10RPKMvsERCCmol_boxplot.svg"),width=12,height=7)
ggplot(rnaCombined[],aes(x=log10(ERCC_molecules),y=log10(RPKM),group=log10(ERCC_molecules),fill=factor(ERCC_molecules_group)))+geom_boxplot()+theme(axis.text.x = element_text(angle = 90, hjust = 1))+theme(legend.position="bottom")+guides(fill = guide_legend(nrow = 1,title="ERCC_molecules_group"))+facet_wrap(~library,nrow=2,scales="free")+theme_bw()
dev.off()

svg(paste0(QC_dir,"/log10RPKMvsERCCmol_boxplot-covPass.svg"),width=9,height=7)
ggplot(rnaCombined[covPass==TRUE],aes(x=log10(ERCC_molecules),y=log10(RPKM),group=log10(ERCC_molecules),fill=factor(ERCC_molecules_group)))+geom_boxplot()+theme(axis.text.x = element_text(angle = 90, hjust = 1))+theme(legend.position="bottom")+guides(fill = guide_legend(nrow = 1,title="ERCC_molecules_group"))+facet_wrap(~library,nrow=2,scales="free")+theme_bw()
dev.off()


#Plot RPKM vs input molecules per sample

cors=rnaCombined[count>covThrs,list(max_rpkm=max(RPKM),max_molERCC=max(ERCC_molecules),cor=round(cor(log2(RPKM),log2(ERCC_molecules)),2)),by=c("sampleID","ERCC_aligned_reads")]

rnaCombined[,col:=ifelse(ERCC_molecules>1,ifelse(covPass==TRUE,NA,paste0("< ",covThrs," reads")),ifelse(covPass==TRUE,"< 1 ERCC molecule","both")),]


svg(paste0(QC_dir,"/log2RPKMvsERCCmol_perSample.svg"),width=22,height=20)
ggplot(rnaCombined,aes(x=log2(ERCC_molecules),y=log2(RPKM)))+geom_point(aes(col=factor(col)))+geom_text(data=cors,aes(hjust=1,x=log2(max_molERCC),y=0.5,label=cor),col="black")+geom_text(data=cors,aes(hjust=0,y=log2(max_rpkm),x=-2,label=paste0(round(ERCC_aligned_reads/1000000,2),"M")),col="black")+facet_wrap(~sampleID,nrow=sqrt(nrow(cors)),scales="free")+guides(col = guide_legend(title=""))+theme(legend.position="bottom")+theme_bw()
#+geom_smooth(aes(group=col),method=lm,se=FALSE,size=1)
dev.off()


#plot ratio of ERCC to actual sample reads 

sample_ERCC_ratio=rnaCombined[,list(sample_ERCC_ratio=Aligned_reads/ERCC_aligned_reads,mean_rpkm=mean(RPKM)),by=c("sampleID","exp_category","library","Aligned_reads","ERCC_aligned_reads")]
sample_ERCC_ratio[,sampleID:=factor(sampleID,levels=unique(sampleID[order(sample_ERCC_ratio)]))]

svg(paste0(QC_dir,"/sample_ERCC_ratio.svg"),width=7,height=11)
ggplot(sample_ERCC_ratio,aes(x=factor(sampleID),y=sample_ERCC_ratio,fill=Aligned_reads))+geom_bar(stat="identity")+xlab("")+coord_flip()
dev.off()+theme_bw()

cor=sample_ERCC_ratio[,list(max_ERCC_aligned_reads=max(log(ERCC_aligned_reads)),max_Aligned_reads=max(log(Aligned_reads)),cor=round(cor(log(ERCC_aligned_reads),log(Aligned_reads)),2)),]

svg(paste0(QC_dir,"/sample_ERCC_cor.svg"),width=6,height=6)
ggplot(sample_ERCC_ratio,aes(x=log(ERCC_aligned_reads),y=log(Aligned_reads),col=library))+geom_point()+geom_text(x=cor$max_ERCC_aligned_reads,y=cor$max_Aligned_reads,label=cor$cor,col="black")+theme_bw()
dev.off()




