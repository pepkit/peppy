#!/usr/bin/env python
import csv, sys

wr = csv.writer(sys.stdout, delimiter = '\t', lineterminator='\n')

for row in csv.reader(iter(sys.stdin.readline, ''), delimiter = '\t'):
    strand = str(row[5])
    if strand == '+':
        row[2] = int(row[1]) + 1
    elif strand == '-':
        row[1] = int(row[2]) - 1
    wr.writerow(row)