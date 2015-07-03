# load the library
library(spp);

args <- commandArgs(TRUE)

sample = args[1]
input = args[2]
sample_name = args[3]
input_name = args[4]
outputDir = args[5]
broad_peaks = args[6]
nCPUs = args[7]

# The following section shows how to initialize a cluster of 8 nodes for parallel processing
# see "snow" package manual for details.
library(snow)
cluster <- makeCluster(nCPUs);

chip.data <- read.bam.tags(sample)
input.data <- read.bam.tags(input)

# get binding info from cross-correlation profile
# srange gives the possible range for the size of the protected region;
# srange should be higher than tag length; making the upper boundary too high will increase calculation time
#
# bin - bin tags within the specified number of basepairs to speed up calculation;
# increasing bin size decreases the accuracy of the determined parameters
binding.characteristics <- get.binding.characteristics(chip.data, srange = c(50,500), bin = 5, cluster = cluster);

# print out binding peak separation distance
print(paste("binding peak separation distance =",binding.characteristics$peak$x))

# plot cross-correlation profile
pdf(file = paste0(outputDir, "/", sample_name, ".crosscorrelation.pdf"), width = 5, height = 5)
par(mar = c(3.5,3.5,1.0,0.5), mgp = c(2,0.65,0), cex = 0.8);
plot(binding.characteristics$cross.correlation, type = 'l', xlab = "strand shift", ylab = "cross-correlation");
abline(v = binding.characteristics$peak$x, lty = 2, col = 2)
dev.off();


# select informative tags based on the binding characteristics
chip.data <- select.informative.tags(chip.data,binding.characteristics);
input.data <- select.informative.tags(input.data,binding.characteristics);

# restrict or remove singular positions with very high tag counts
chip.data <- remove.local.tag.anomalies(chip.data);
input.data <- remove.local.tag.anomalies(input.data);


# output smoothed tag density (subtracting re-scaled input) into a WIG file
# note that the tags are shifted by half of the peak separation distance
#tag.shift <- round(binding.characteristics$peak$x/2)
#smoothed.density <- get.smoothed.tag.density(chip.data,control.tags=input.data,bandwidth=200,step=100,tag.shift=tag.shift);
#writewig(smoothed.density,"example.density.wig","Example smoothed, background-subtracted tag density");
#rm(smoothed.density);


#smoothed.enrichment.estimate <- get.smoothed.enrichment.mle(chip.data,input.data,bandwidth=200,step=100,tag.shift=tag.shift)
#writewig(smoothed.enrichment.estimate,"example.enrichment.wig","Example smoothed maximum likelihood log2 enrichment estimate");

# output conservative enrichment estimates
# alpha specifies significance level at which confidence intervals will be estimated
#enrichment.estimates <- get.conservative.fold.enrichment.profile(chip.data,input.data,fws=500,step=100,alpha=0.01);
#writewig(enrichment.estimates,"example.enrichment.estimates.wig","Example conservative fold-enrichment/depletion estimates shown on log2 scale");
#rm(enrichment.estimates);

if (broad_peaks){
    broad.clusters <- get.broad.enrichment.clusters(chip.data,input.data,window.size=1e3,z.thr=3,tag.shift=round(binding.characteristics$peak$x/2))
    # write out in broadPeak format
    write.broadpeak.info(broad.clusters, paste0(dataDir, "/spp_peaks/", sample_name, ".broadPeak"))
}


# binding detection parameters
# desired FDR (1%). Alternatively, an E-value can be supplied to the method calls below instead of the fdr parameter
fdr <- 1e-2; 
# the binding.characteristics contains the optimized half-size for binding detection window
detection.window.halfsize <- binding.characteristics$whs;
  
# determine binding positions using wtd method
bp <- find.binding.positions(signal.data=chip.data,control.data=input.data,fdr=fdr,whs=detection.window.halfsize,cluster=cluster)

print(paste("detected",sum(unlist(lapply(bp$npl,function(d) length(d$x)))),"peaks"));
  
# output detected binding positions
output.binding.results(bp, paste0(dataDir, "/", sample_name, ".binding.positions.txt", sep = ""));

bp <- find.binding.positions(signal.data=chip.data,control.data=input.data,fdr=fdr,method=tag.lwcc,whs=detection.window.halfsize,cluster=cluster)
# output narrowPeaks
write.narrowpeak.binding(bp, paste0(dataDir, "/", sample_name, ".narrowPeak", sep = ""))

if (broad_peaks){
    bp <- add.broad.peak.regions(chip.data,input.data,bp,window.size=1000,z.thr=3)
    # output narrowPeaks and broad peaks toghether
    write.narrowpeak.binding(bp, paste0(dataDir, "/", sample_name, ".narrow+BroadPeak"))
}


# determine MSER
# note: this will take approximately 10-15x the amount of time the initial binding detection did
# The saturation criteria here is 99% consistency in the set of binding positions when adding 1e5 tags.
# To ensure convergence the number of subsampled chains (n.chains) should be higher (80)
#mser <- get.mser(chip.data,input.data,step.size=1e5,test.agreement=0.99,n.chains=8,cluster=cluster,fdr=fdr,method=tag.wtd,whs=detection.window.halfsize)

#print(paste("MSER at a current depth is",mser));



# interpolate MSER dependency on tag count
# note: this requires considerably more calculations than the previous steps (~ 3x more than the first MSER calculation)
# Here we interpolate MSER dependency to determine a point at which MSER of 2 is reached
# The interpolation will be based on the difference in MSER at the current depth, and a depth at 5e5 fewer tags (n.steps=6);
# evaluation of the intermediate points is omitted here to speed up the calculation (excluded.steps parameter)
# A total of 7 chains is used here to speed up calculation, whereas a higher number of chains (50) would give good convergence
#msers <- get.mser.interpolation(chip.data,input.data,step.size=1e5,test.agreement=0.99, target.fold.enrichment=2,
# n.chains=7,n.steps=6,cluster=cluster,fdr=fdr,method=tag.wtd,whs=detection.window.halfsize)

#print(paste("predicted sequencing depth =",round(unlist(lapply(msers,function(x) x$prediction))/1e6,5)," million tags"))

