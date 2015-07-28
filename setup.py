#! /usr/bin/env python

import sys
import re
import os

extra = {}

try:
    from setuptools import setup
    if sys.version_info < (2, 7):
        extra['install_requires'] = ['argparse']
    if sys.version_info >= (3,):
        extra['use_2to3'] = True
except ImportError:
    from distutils.core import setup
    if sys.version_info < (2, 7):
        extra['dependencies'] = ['argparse']


setup(
    name="pipelines",
    packages=["pipelines"],
    version="0.1",
    description="Pipelines in Python.",
    long_description=open('README.md').read(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Programming Language :: Python :: 2.7",
        "Topic :: Scientific/Engineering :: Bio-Informatics"
    ],
    keywords="bioinformatics, sequencing, ngs, ChIP-seq, DNase-seq, ATAC-Seq",
    url="https://github.com/afrendeiro/pipelines",
    author=u"Andre Rendeiro",
    author_email="arendeiro@cemm.oeaw.ac.at",
    license="GPL2",
    install_requires=["pyyaml", "numpy", "pandas"],
    entry_points={
        "console_scripts": [
            'pipelines = pipelines.pipelines:main',
            'chipseq-pipeline = pipelines.chipseq:main',
            'atacseq-pipeline = pipelines.atacseq:main',
            'quantseq-pipeline = pipelines.quantseq:main'
        ],
    },
     scripts=[
        "lib/shift_reads.py",
        "lib/fix_bedfile_genome_boundaries.py",
        "lib/get5primePosition.py",
        "lib/spp_peak_calling.R"
    ],
    data_files=[(os.path.expanduser("~"), ['.pipelines_config.yaml'])],
    include_package_data=True
)
