readData = function(project,pipName="pipeline1.py") {
  lapply(outputsByPipeline(project, pipName), function(x) {
      lapply(x, function(x1){
          message("Reading: ", basename(x1))
	  df = read.table(x1, stringsAsFactors=F)
	  colnames(df)[1:3] = c('chr', 'start', 'end')
          GenomicRanges::GRanges(df)
      })
  })
}
