#!/usr/bin/Rscript

# load the library
suppressPackageStartupMessages(library(package="DiffBind"))

# parse arguments
args <- commandArgs(TRUE)
csv = args[1]
jobName = args[2]
plotsDir = args[3]


gRangesToBed <- function(df) {
    # Function to export GRanges object to bed
    bed = data.frame(
        seqnames=seqnames(df),
        starts=start(df) - 1,
        ends=end(df),
        names=names(df),
        scores=df$FDR,
        strands=c(rep(".", length(df)))
    )
    bed = cbind(bed, mcols(df))

    return(bed)
}

# load csv
samples = dba(sampleSheet=csv, bCorPlot=FALSE)


# Plot similarity based on peak intersection
pdf(paste0(plotsDir, "/", jobName, "_peakSimilarity.pdf"))
plot(samples)
dev.off()


# Calculate similarity based on factor affinity
if (nrow(samples$samples) <= 2) {
    n = 2
} else {
    n = 3
}

affinity = dba.count(samples, minOverlap=n)
# plot
pdf(paste0(plotsDir, "/", jobName, "_affinitySimilarity.pdf"))
plot(affinity)
dev.off()


# If there are replicates, run contrast analysis
if (length(unique(samples$samples$Replicate)) > 1) {

    for (contrast in c(DBA_TISSUE, DBA_CONDITION, DBA_TREATMENT)) {
        # Check there's more than one type per contrast
        if (contrast == DBA_TISSUE) {
            if (length(unique(samples$Tissue)) <= 1) {
                next
            }
            contrastName = "Tissues"
        }
        else if (contrast == DBA_CONDITION) {
            if (length(unique(samples$Condition)) <= 1) {
                next
            }
            contrastName = "Condition"
        }
        else if (contrast == DBA_TREATMENT) {
            if (length(unique(samples$Treatment)) <= 1) {
                next
            }
            contrastName = "Treatment"
        }
        # Add contrasts
        df = dba.contrast(affinity, categories=contrast)

        # Differential binding analysis
        pdf(paste0(plotsDir, "/", jobName, "_Tissue.differential_binding.pdf"))
        # produces correlation matrix using only differentially bound sites
        differential = dba.analyze(df)
        dev.off()

        # Get list of differentialy bound sites
        DBS = dba.report(differential, bCalled=TRUE)

        # MA plot
        pdf(paste0(plotsDir, "/", jobName, "_", contrastName, ".differential_binding.MA.pdf"))
        dba.plotMA(DBS)
        dev.off()

        # PCA plots
        pdf(paste0(plotsDir, "/", jobName, "_", contrastName, ".differential_binding.PCA.pdf"))
        dba.plotPCA(DBS, contrast)
        dev.off()

        pdf(paste0(plotsDir, "/", jobName, "_", contrastName, ".differential_binding.PCA_label.pdf"))
        dba.plotPCA(DBS, contrast=1, th=.05, label=contrast)
        dev.off()

        # Boxplot
        pdf(paste0(plotsDir, "/", jobName, "_", contrastName, ".differential_binding.boxplot.pdf"))
        pvals = dba.plotBox(DBS)
        dev.off()

        # Heatmaps
        pdf(paste0(plotsDir, "/", jobName, "_", contrastName, ".differential_binding.heatmap.pdf"))
        corvals = dba.plotHeatmap(DBS)
        dev.off()

        pdf(paste0(plotsDir, "/", jobName, "_", contrastName, ".differential_binding.heatmap_rpkm.pdf"))
        dba.plotHeatmap(DBS, score=DBA_SCORE_RPKM_FOLD)
        dev.off()

        pdf(paste0(plotsDir, "/", jobName, "_", contrastName, ".differential_binding.heatmap_all.pdf"))
        corvals = dba.plotHeatmap(DBS, contrast=1, correlations=FALSE))
        dev.off()

        pdf(paste0(plotsDir, "/", jobName, "_", contrastName, ".differential_binding.heatmap_all_scaled.pdf"))
        corvals = dba.plotHeatmap(DBS, contrast=1, correlations=FALSE, scale=row))
        dev.off()

        # Venn diagrams
        pdf(paste0(plotsDir, "/", jobName, "_", contrastName, ".differential_binding.algorithms.pdf"))
        dba.plotVenn(DBS, 1:3, label1="edgeR", label2="DESeq", label3="DESeq2")
        dev.off()

        # Overlap rates
        olap.rate = dba.overlap(DBS, mode=DBA_OLAP_RATE)
        pdf(paste0(plotsDir, "/", jobName, "_", contrastName, ".differential_binding.overlap.pdf"))
        plot(olap.rate, type='b', ylab='# peaks', xlab='Overlap at least this many peaksets')
        dev.off()

        pdf(paste0(plotsDir, "/", jobName, "_", contrastName, ".differential_binding.venn.pdf"))
        dba.venn(DBS, tissuesDBS$masks[contrast] & tissuesDBS$masks[contrast])
        dev.off()
    }



    # Analysis with consensus peaks between replicates #
    # Get consensus peak sets between replicates
    consensusReplicates = dba.peakset(affinity, consensus = -DBA_REPLICATE, minOverlap=0.66)
    consensus = dba(consensusReplicates, mask = consensusReplicates$masks$Consensus)

    # Add contrasts
    for (contrast in c(DBA_TISSUE, DBA_CONDITION, DBA_TREATMENT)) {
        df = dba.contrast(affinity, categories=contrast)

        # Differential binding analysis
        pdf(paste0(plotsDir, "/", jobName, "_", contrastName, ".differential_binding.pdf"))
        # produces correlation matrix using only differentially bound sites
        differential = dba.analyze(df)
        dev.off()

        # Get list of differentialy bound sites
        DBS = dba.report(differential, bCalled=TRUE)

        # Export as bed file
        bed = gRangesToBed(DBS)
        write.table(bed,
            file=paste0(plotsDir, "/", jobName, "_", contrastName, ".diffentially_bound.bed"),
            quote=FALSE, sep="\t", row.names=FALSE, col.names=FALSE
        )

    }

}
