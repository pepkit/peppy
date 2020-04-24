readRemoteData = function(project) {
  # get the data from the Project object
  url = pepr::sampleTable(project)$remote_url[[1]]
  # download the file
  bfc = BiocFileCache::BiocFileCache(cache=tempdir(),ask=FALSE)
  path = BiocFileCache::bfcrpath(bfc, url)
  # read it in
  df = read.table(path)
  # formatting
  colnames(df) = c('chr', 'start', 'end', 'name')
  # convert to GRanges object
  GenomicRanges::GRanges(df)
}
