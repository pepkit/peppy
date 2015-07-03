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
    if row[0][0] == "@":
        wr.writerow(row)
    else:
        flag = int(row[1])
        chrm = row[2]

        if flag & 16 == 0:
            if int(row[3]) + 4 + 51 < chrms[chrm]:
                row[3] = int(row[3]) + 4
            else:
                continue
        elif flag & 16 == 16:
            if int(row[3]) - 5 - 51 >= 1:
                row[3] = int(row[3]) - 5
            else:
                continue
        wr.writerow(row)
