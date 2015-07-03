#!/usr/env python

from argparse import ArgumentParser
import os
import re
from pybedtools import BedTool
import HTSeq
import numpy as np
import pandas as pd
import string
import itertools

import rpy2.robjects as robj  # for ggplot in R
import rpy2.robjects.pandas2ri  # for R dataframe conversion


def main(args):
    # Parse command-line arguments
    parser = ArgumentParser(
        description='correlations.py',
        usage='python correlations.py [options] <directory> file1 [file2 ... fileN]'
    )

    # Global options
    # positional arguments
    parser.add_argument(dest='plots_dir', type=str, help='Directory to save plots to.')
    parser.add_argument('covFiles', nargs='*', help='covFiles')
    # optional arguments

    args = parser.parse_args()

    plotFunc = robj.r("""
        function(df, path){
            # scatterplot
            pdf(path, height=7, width=7)

            par(pty="s")

            smoothScatter(
                df,
                col=rgb(104,104,104,50, maxColorValue=255),
                pch=16,
                nrpoints=0
            )
            text(
                par('usr')[1] + 1.8,
                par('usr')[4] - 0.5,
                bquote(R^2 == .(round(cor(df[1], df[2]), 3))),
                cex=1.6
            )
            title(
                xlab=colnames(df)[1],
                ylab=colnames(df)[2],
                outer=TRUE, cex.lab = 1.5
            )
            dev.off()
        }
    """)

    # pick samples pairwisely
    for sample1, sample2 in itertools.combinations(args.covFiles, 2):
        name1 = re.sub(os.path.basename(sample1), "\.cov", "")
        name2 = re.sub(os.path.basename(sample2), "\.cov", "")

        # Read
        df1 = pd.DataFrame(os.path.abspath(sample1))  
        df2 = pd.DataFrame(os.path.abspath(sample2))

        # normalize to total size
        # todo: select column with the actual data (read counts)
        # df1.apply(lambda x: np.log2(1 + (x / x.sum()) * 1000000))
        # df2.apply(lambda x: np.log2(1 + (x / x.sum()) * 1000000))

        # convert the pandas dataframe to an R dataframe
        # robj.pandas2ri.activate()
        # df_R = robj.conversion.py2ri(d)
        # run the plot function on the dataframe
        # plotFunc(df_R, os.path.join(args.plots_dir, sample1 + "_vs_" + sample2 + ".pdf"))


if __name__ == '__main__':
    main()
