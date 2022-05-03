readData = function(project, sampleName="sample1") {
  lapply(getOutputsBySample(project, sampleName), function(x) {
      lapply(x, function(x1){
          lapply(x1, function(x2){
            message("Reading: ", x2)
            df[[x2]] = read.table(x2, stringsAsFactors=F)
            colnames(df)[1:3] = c('chr', 'start', 'end')
          })
      })
  })
  GenomicRanges::GRanges(df)
}
