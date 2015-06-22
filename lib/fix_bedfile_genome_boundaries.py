#!/usr/bin/env python
import csv
import sys


def getChrSizes(chrmFile):
    """
    Reads tab-delimiter file with two rows describing the chromossomes and its lengths.
    Returns dictionary of chr:sizes.
    """
    with open(chrmFile, 'r') as f:
        chrmSizes = {}
        for line in enumerate(f):
            row = line[1].strip().split('\t')
            chrmSizes[str(row[0])] = int(row[1])
    return chrmSizes

chrSizes = {
    "hg19": "/fhgfs/groups/lab_bock/arendeiro/share/hg19.chrom.sizes",
    "mm10": "/fhgfs/groups/lab_bock/arendeiro/share/mm10.chrom.sizes",
    "dr7": "/fhgfs/groups/lab_bock/arendeiro/share/danRer7.chrom.sizes"
}

genome = sys.argv[1]
chrms = getChrSizes(chrSizes[genome])  # get size of chromosomes

wr = csv.writer(sys.stdout, delimiter='\t', lineterminator='\n')

for row in csv.reader(iter(sys.stdin.readline, ''), delimiter='\t'):
    chrm = row[0]
    start = int(row[1])
    end = int(row[2])

    if chrm in chrms.keys():  # skip weird chromosomes
        if start >= 1 and end <= chrms[chrm] and start < end:
            wr.writerow(row)
