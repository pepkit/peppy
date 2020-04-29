readData = function(project, sampleName="sample1") {
  lapply(getOutputsBySample(project, sampleName), function(x) {
      lapply(x, function(x1){
          message("Reading: ", basename(x1))
      df = read.table(x1, stringsAsFactors=F)
      colnames(df)[1:3] = c('chr', 'start', 'end')
          GenomicRanges::GRanges(df)
      })
  })
}
