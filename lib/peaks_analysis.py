#!/usr/env python

#############################################################################################
#
# This code produces plots of average signal and heatmaps around motifs under peaks.
# Also produces clusters of peaks, and outputs heatmap
#
#############################################################################################

"""
TODO: Adapt to allow run without --strand-specific!
"""

from argparse import ArgumentParser
from collections import OrderedDict
import cPickle as pickle
import HTSeq
import numpy as np
import os
import pandas as pd
import pybedtools
import re
import matplotlib
# Force matplotlib to not use any Xwindows backend.
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import sys


def main():
    # Parse command-line arguments
    parser = ArgumentParser()

    # Global options
    # positional arguments
    parser.add_argument(dest='bam_file', type=str, help='Bam file location.')
    parser.add_argument(dest='peak_file', type=str, help='Peak file location.')
    parser.add_argument(dest='plots_dir', type=str, help='Directory to save plots to.')
    # optional arguments
    parser.add_argument('--duplicates', dest='duplicates', action='store_true')
    parser.add_argument('--window-width', dest='window_width', type=int, default=2000)
    parser.add_argument('--fragment-size', dest='fragment_size', type=int, default=1)
    parser.add_argument('--strand-specific', dest='strand_specific', action='store_true')
    parser.add_argument('--genome', dest='genome', type=str, default='hg19')
    parser.add_argument('--n_clusters', dest='n_clusters', type=int, default=5)
    args = parser.parse_args()

    sample_name = re.sub("\..*", "", re.sub("\.bam", "", os.path.basename(args.bam_file)))
    exportName = os.path.join(args.plots_dir, sample_name + "_coverage_%ibp" % args.window_width)
    window_range = (-abs(args.window_width) / 2, abs(args.window_width) / 2)

    # Loop through all samples, compute coverage in peak regions centered on motifs,
    # save dicts with coverage and average profiles
    # Load peak file from bed files, centered on motif

    # TODO: modify pipeline so that slop is done here
    # peaks = pybedtools.BedTool(os.path.join(peakFilePath, signal + ".motifStrand.bed")).slop(genome=genome, b=args.window_width/2)
    peaks = bedToolsInterval2GenomicInterval(pybedtools.BedTool(args.peak_file))
    # Filter peaks near chrm borders
    for name, interval in peaks.iteritems():
        if interval.length < args.window_width:
            peaks.pop(name)

    # Load bam
    bamfile = HTSeq.BAM_Reader(args.bam_file)

    # Get dataframe of signal coverage in bed regions, append to dict
    cov = coverage(bamfile, peaks, args.fragment_size, strand_specific=args.strand_specific)

    # Make multiindex dataframe
    levels = [cov.keys(), ["+", "-"]]
    labels = [[y for x in range(len(cov)) for y in [x, x]], [y for x in range(len(cov.keys())) for y in (0, 1)]]
    index = pd.MultiIndex(labels=labels, levels=levels, names=["peak", "strand"])
    df = pd.DataFrame(np.vstack(cov.values()), index=index)
    df.columns = range(window_range[0], window_range[1])

    # Save
    pickle.dump(
        df,
        open(
            os.path.join(
                args.plots_dir,
                "pickles",
                sample_name + "_tssCoverage_%ibp.pickle" % args.window_width
            ),
            'wb'
        ),
        protocol=pickle.HIGHEST_PROTOCOL
    )

    # Compute averages
    aveSignal = pd.DataFrame({"x": list(df.columns),                                             # x axis
                              "average": df.apply(np.mean, axis=0),                              # both strands
                              "positive": df.ix[range(0, len(df), 2)].apply(np.mean, axis=0),    # positive strand
                              "negative": df.ix[range(1, len(df), 2)].apply(np.mean, axis=0)     # negative strand
                              })

    # Plot average profiles by strand
    aveSignal.plot("x", ["average", "positive", "negative"], subplots=True, sharex=True, colormap="Accent")
    plt.savefig("{0}_averageProfile_{1}bp.pdf".format(exportName, args.window_width))

    # join strand signal (plus - minus)
    df = df.xs('+', level="strand") + df.xs('-', level="strand")

    # Export as cdt
    exportToJavaTreeView(
        df.copy(),
        os.path.join(
            args.plots_dir,
            "cdt",
            sample_name + "_tssCoverage_%ibp_averageProfile.cdt" % args.window_width
        )
    )
    # scale row signal to 0:1 (normalization)
    dfNorm = df.apply(lambda x: (x - min(x)) / (max(x) - min(x)), axis=1)

    # replace inf with 0s
    dfNorm.replace([np.inf, -np.inf], 0, inplace=True)

    # sort by absolute read amounts
    order = dfNorm.sum(axis=1)
    order.sort(inplace=True, ascending=False)

    dfNorm = dfNorm.reindex([order.index])

    # Export as cdt
    exportToJavaTreeView(
        dfNorm.copy(),
        os.path.join(
            args.plots_dir,
            "cdt",
            sample_name + "_tssCoverage_%ibp_averageProfile.normalized.cdt" % args.window_width
        )
    )


def bedToolsInterval2GenomicInterval(bedtool):
    """
    Given a pybedtools.BedTool object, returns dictionary of HTSeq.GenomicInterval objects.
    """
    intervals = OrderedDict()
    for iv in bedtool:
        if iv.strand == "+" or iv.strand == 0 or iv.strand == str(0):
            intervals[iv.name] = HTSeq.GenomicInterval(iv.chrom, iv.start, iv.end, "+")
        elif iv.strand == "-" or iv.strand == 0 or iv.strand == str(1):
            intervals[iv.name] = HTSeq.GenomicInterval(iv.chrom, iv.start, iv.end, "-")
        else:
            intervals[iv.name] = HTSeq.GenomicInterval(iv.chrom, iv.start, iv.end)
    return intervals


def coverage(bam, intervals, fragmentsize, orientation=True, duplicates=True, strand_specific=False):
    """
    Gets read coverage in bed regions.
    Returns dict of regionName:numpy.array if strand_specific=False, A dict of "+" and "-" keys with regionName:numpy.array
    bam - HTSeq.BAM_Reader object. Must be sorted and indexed with .bai file!
    intervals - dict with HTSeq.GenomicInterval objects as values
    fragmentsize - integer
    stranded - boolean
    duplicates - boolean.
    """
    chroms = ['chr1', 'chr2', 'chr3', 'chr4', 'chr5', 'chr6', 'chr7', 'chr8', 'chr9', 'chr10', 'chr11', 'chr12', 'chr13', 'chr14', 'chr15', 'chr16', 'chr17', 'chr18', 'chr19', 'chr20', 'chr21', 'chr22', 'chrX']
    # Loop through TSSs, get coverage, append to dict
    cov = OrderedDict()
    i = 0
    for name, feature in intervals.iteritems():
        if feature.chrom not in chroms:
            continue
        # if i % 1000 == 0:
        #    print(len(intervals) - i)
        # Initialize empty array for this feature
        if not strand_specific:
            profile = np.zeros(feature.length, dtype=np.int8)
        else:
            profile = np.zeros((2, feature.length), dtype=np.int8)

        # Fetch alignments in feature window
        for aln in bam[feature]:
            # check if duplicate
            if not duplicates and aln.pcr_or_optical_duplicate:
                continue

            aln.iv.length = fragmentsize  # adjust to size

            # get position in relative to window
            if orientation:
                if feature.strand == "+" or feature.strand == ".":
                    start_in_window = aln.iv.start - feature.start - 1
                    end_in_window = aln.iv.end - feature.start - 1
                else:
                    start_in_window = feature.length - abs(feature.start - aln.iv.end) - 1
                    end_in_window = feature.length - abs(feature.start - aln.iv.start) - 1
            else:
                start_in_window = aln.iv.start - feature.start - 1
                end_in_window = aln.iv.end - feature.start - 1

            # check fragment is within window; this is because of fragmentsize adjustment
            if start_in_window < 0 or end_in_window > feature.length:
                continue

            # add +1 to all positions overlapped by read within window
            if not strand_specific:
                profile[start_in_window: end_in_window] += 1
            else:
                if aln.iv.strand == "+":
                    profile[0][start_in_window: end_in_window] += 1
                elif aln.iv.strand == "-":
                    profile[1][start_in_window: end_in_window] += 1

        # append feature profile to dict
        cov[name] = profile
        i += 1
    return cov


def exportToJavaTreeView(df, filename):
    """
    Export cdt file of cluster to view in JavaTreeView.
    df - pandas.DataFrame object with numeric data.
    filename - string.
    """
    cols = ["X" + str(x) for x in df.columns]
    df.columns = cols
    df["X"] = df.index
    df["NAME"] = df.index
    df["GWEIGHT"] = 1
    df = df[["X", "NAME", "GWEIGHT"] + cols]
    df.to_csv(filename, sep="\t", index=False)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Program canceled by user!")
        sys.exit(0)
