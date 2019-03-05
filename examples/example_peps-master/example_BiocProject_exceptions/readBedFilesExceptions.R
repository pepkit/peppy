readBedFilesExceptions = function(project) {
  warning("first test warning")
  warning("second test warning")
  stop("test error")
  paths = pepr::samples(project)$file_path
  sampleNames = pepr::samples(project)$sample_name
  setwd(dirname(project@file))
  result = lapply(paths, function(x){
    df = read.table(x)
    colnames(df) = c('chr', 'start', 'end')
    gr = GenomicRanges::GRanges(df) 
  })
  names(result) = sampleNames
  return(GenomicRanges::GRangesList(result))
}


