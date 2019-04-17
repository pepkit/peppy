readBedFiles_resize = function(project, resize.width) {
  cwd = getwd()
  paths = pepr::samples(project)$file_path
  sampleNames = pepr::samples(project)$sample_name
  setwd(dirname(project@file))
  result = lapply(paths, function(x){
    df = read.table(x)
    colnames(df) = c('chr', 'start', 'end')
    gr = GenomicRanges::resize(GenomicRanges::GRanges(df), width=resize.width)
  })
  setwd(cwd)
  names(result) = sampleNames
  return(GenomicRanges::GRangesList(result))
}