readBedFiles = function(project) {
  cwd = getwd()
  paths = pepr::samples(project)$file_path
  sampleNames = pepr::samples(project)$sample_name
  setwd(dirname(project@file))
  result = lapply(paths, function(x){
    df = read.table(x)
    colnames(df) = c('chr', 'start', 'end')
    gr = GenomicRanges::GRanges(df) 
  })
  setwd(cwd)
  names(result) = sampleNames
  return(GenomicRanges::GRangesList(result))
}


